use std::{
    ffi::{c_char, c_void, CStr},
    marker::PhantomData,
    ptr,
    rc::Rc,
};

pub type MutationCallback = unsafe extern "C" fn(*mut c_void, *const u8, usize) -> i32;

unsafe extern "C" {
    fn gpui_hermes_create() -> *mut c_void;
    fn gpui_hermes_destroy(handle: *mut c_void);
    fn gpui_hermes_install_mutation_sink(
        handle: *mut c_void,
        callback: MutationCallback,
        user_data: *mut c_void,
        out_error: *mut *mut c_char,
    ) -> i32;
    fn gpui_hermes_eval_hbc(
        handle: *mut c_void,
        data: *const u8,
        length: usize,
        out_value: *mut *mut c_char,
        out_error: *mut *mut c_char,
    ) -> i32;
    fn gpui_hermes_free_string(value: *mut c_char);
}

/// A thread-affine Hermes runtime with a real JSI `gpuiEmit` host function.
/// The callback's user data must outlive this runtime; it is invoked
/// synchronously on the thread that calls `eval_hbc`.
pub struct HermesBridge {
    handle: *mut c_void,
    _not_send_or_sync: PhantomData<Rc<()>>,
}

impl HermesBridge {
    pub fn new() -> Result<Self, String> {
        // Force Cargo to retain the exact pinned native VM archive and its link line.
        hermes_lean_sys::ensure_linked();
        let handle = unsafe { gpui_hermes_create() };
        if handle.is_null() {
            return Err("could not create the pinned Hermes runtime".into());
        }
        Ok(Self { handle, _not_send_or_sync: PhantomData })
    }

    pub fn install_mutation_sink(
        &mut self,
        callback: MutationCallback,
        user_data: *mut c_void,
    ) -> Result<(), String> {
        let mut error = ptr::null_mut();
        let status = unsafe {
            gpui_hermes_install_mutation_sink(self.handle, callback, user_data, &mut error)
        };
        if status == 0 { Ok(()) } else { Err(unsafe { take_string(error) }) }
    }

    pub fn eval_hbc(&mut self, bytecode: &[u8]) -> Result<String, String> {
        let mut value = ptr::null_mut();
        let mut error = ptr::null_mut();
        let status = unsafe {
            gpui_hermes_eval_hbc(self.handle, bytecode.as_ptr(), bytecode.len(), &mut value, &mut error)
        };
        if status == 0 { Ok(unsafe { take_string(value) }) } else { Err(unsafe { take_string(error) }) }
    }
}

impl Drop for HermesBridge {
    fn drop(&mut self) {
        // The JSI closure retaining the callback is destroyed before its Rust
        // user_data owner is dropped by the caller's reverse declaration order.
        unsafe { gpui_hermes_destroy(self.handle) };
    }
}

unsafe fn take_string(value: *mut c_char) -> String {
    if value.is_null() { return String::new(); }
    let result = CStr::from_ptr(value).to_string_lossy().into_owned();
    gpui_hermes_free_string(value);
    result
}

use gpui_ui_mutation::Scene;
use serde_json::Value;
use std::{panic::{catch_unwind, AssertUnwindSafe}, time::Instant};

#[derive(Default)]
struct MutationState {
    scene: Scene,
    batches: usize,
    error: Option<String>,
    pending_at: Option<Instant>,
}

unsafe extern "C" fn apply_mutation_batch(
    user_data: *mut c_void,
    payload: *const u8,
    length: usize,
) -> i32 {
    if user_data.is_null() || payload.is_null() { return 1; }
    let outcome = catch_unwind(AssertUnwindSafe(|| {
        let state = &mut *(user_data as *mut MutationState);
        let bytes = std::slice::from_raw_parts(payload, length);
        let parsed: Value = serde_json::from_slice(bytes).map_err(|error| error.to_string())?;
        let batch = parsed.as_array().ok_or_else(|| "mutation payload must be an array".to_string())?;
        state.scene.apply_batch(batch)?;
        state.batches += 1;
        state.pending_at = Some(Instant::now());
        Ok::<(), String>(())
    }));
    match outcome {
        Ok(Ok(())) => 0,
        Ok(Err(error)) => {
            (*(user_data as *mut MutationState)).error = Some(error);
            1
        }
        Err(_) => {
            (*(user_data as *mut MutationState)).error = Some("Rust mutation callback panicked".into());
            2
        }
    }
}

/// One thread-affine Hermes VM and the Rust scene receiving its live JSI batches.
/// The runtime is destroyed before the boxed callback state so JSI never retains
/// a dangling user-data pointer.
pub struct SceneRuntime {
    runtime: Option<HermesBridge>,
    state: Box<MutationState>,
}

impl SceneRuntime {
    pub fn new() -> Result<Self, String> {
        let mut state = Box::<MutationState>::default();
        let mut runtime = HermesBridge::new()?;
        runtime.install_mutation_sink(
            apply_mutation_batch,
            (&mut *state as *mut MutationState).cast::<c_void>(),
        )?;
        Ok(Self { runtime: Some(runtime), state })
    }

    pub fn eval_hbc(&mut self, bytecode: &[u8]) -> Result<String, String> {
        let result = self.runtime.as_mut().expect("live Hermes runtime").eval_hbc(bytecode)?;
        if let Some(error) = &self.state.error { return Err(error.clone()); }
        Ok(result)
    }

    pub fn snapshot(&self) -> Result<Value, String> {
        if let Some(error) = &self.state.error { return Err(error.clone()); }
        self.state.scene.snapshot()
    }

    pub fn take_pending_at(&mut self) -> Option<Instant> { self.state.pending_at.take() }
    pub fn batches(&self) -> usize { self.state.batches }
    pub fn operations(&self) -> usize { self.state.scene.operations() }
    pub fn node_count(&self) -> usize { self.state.scene.node_count() }
}

impl Drop for SceneRuntime {
    fn drop(&mut self) {
        drop(self.runtime.take());
    }
}
