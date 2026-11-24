use gpui_hermes_live_spike::HermesBridge;
use gpui_ui_mutation::Scene;
use serde_json::Value;
use std::{
    ffi::c_void,
    fs,
    panic::{catch_unwind, AssertUnwindSafe},
    path::PathBuf,
    process::Command,
    slice,
};

#[derive(Default)]
struct MutationState {
    scene: Scene,
    batches: usize,
    error: Option<String>,
}

unsafe extern "C" fn apply_mutation_batch(
    user_data: *mut c_void,
    payload: *const u8,
    length: usize,
) -> i32 {
    if user_data.is_null() || payload.is_null() { return 1; }
    let outcome = catch_unwind(AssertUnwindSafe(|| {
        let state = &mut *(user_data as *mut MutationState);
        let bytes = slice::from_raw_parts(payload, length);
        let parsed: Value = serde_json::from_slice(bytes).map_err(|error| error.to_string())?;
        let batch = parsed.as_array().ok_or_else(|| "mutation payload must be an array".to_string())?;
        state.scene.apply_batch(batch)?;
        state.batches += 1;
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

fn main() {
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let source = manifest.join("probe.js");
    let bytecode = manifest.join("target/gpui-live-probe.hbc");
    fs::create_dir_all(bytecode.parent().expect("bytecode parent")).expect("create output dir");

    let compiler = Command::new(env!("HERMESC_PATH"))
        .args(["-O", "-emit-binary", "-out"])
        .arg(&bytecode)
        .arg(&source)
        .output()
        .expect("launch hermesc paired with the linked Hermes VM");
    assert!(compiler.status.success(), "hermesc failed: {}", String::from_utf8_lossy(&compiler.stderr));
    let hbc = fs::read(&bytecode).expect("read compiled HBC");
    assert!(hbc.starts_with(b"\xc6\x1f\xbc\x03"), "compiler output is not Hermes bytecode");

    let mut state = MutationState::default();
    let mut runtime = HermesBridge::new().expect("create in-process Hermes VM");
    runtime.install_mutation_sink(
        apply_mutation_batch,
        (&mut state as *mut MutationState).cast::<c_void>(),
    ).expect("install live JSI-to-Rust mutation callback");
    let result = runtime.eval_hbc(&hbc).expect("execute HBC and synchronously deliver its mutation batch");
    assert_eq!(result, "mutation-sent");
    assert_eq!(state.batches, 1, "one actual JSI host call must reach Rust");
    assert!(state.error.is_none(), "Rust callback error: {:?}", state.error);

    let snapshot = state.scene.snapshot().expect("Rust scene snapshot");
    assert_eq!(snapshot["children"][0]["attrs"]["id"], "app");
    assert_eq!(snapshot["children"][0]["children"][0]["text"], "Live JSI mutation");
    println!("LIVE_HERMES_HBC_JSI_TO_RUST_MUTATION_PASS:batches={}:ops={}:nodes={}",
        state.batches, state.scene.operations(), state.scene.node_count());
    println!("HERMES_ENGINE_DIGEST:{}", env!("HERMES_ENGINE_DIGEST"));
    println!("HERMES_BYTECODE_VERSION:{}", env!("HERMES_BYTECODE_VERSION"));
}
