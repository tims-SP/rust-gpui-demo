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
