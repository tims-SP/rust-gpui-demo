use gpui_hermes_live_spike::HermesBridge;
use gpui_ui_mutation::Scene;
use serde_json::Value;
use std::{
    ffi::c_void,
    fs,
    panic::{catch_unwind, AssertUnwindSafe},
    path::{Path, PathBuf},
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

fn compile_hbc(source: &Path, output: &Path) -> Vec<u8> {
    fs::create_dir_all(output.parent().expect("HBC output parent")).expect("create HBC output directory");
    let compiler = Command::new(env!("HERMESC_PATH"))
        .args(["-O", "-emit-binary", "-out"])
        .arg(output)
        .arg(source)
        .output()
        .expect("launch hermesc paired with the linked Hermes VM");
    assert!(compiler.status.success(), "hermesc failed for {}: {}",
        source.display(), String::from_utf8_lossy(&compiler.stderr));
    let hbc = fs::read(output).expect("read compiled HBC");
    assert!(hbc.starts_with(b"\xc6\x1f\xbc\x03"), "{} is not Hermes bytecode", output.display());
    hbc
}

fn find_by_id<'a>(node: &'a Value, id: &str) -> Option<&'a Value> {
    if node.get("attrs").and_then(|attrs| attrs.get("id")).and_then(Value::as_str) == Some(id) {
        return Some(node);
    }
    node.get("children")?.as_array()?.iter().find_map(|child| find_by_id(child, id))
}

fn text_content(node: &Value) -> String {
    if node.get("type").and_then(Value::as_str) == Some("text") {
        return node.get("text").and_then(Value::as_str).unwrap_or_default().to_owned();
    }
    node.get("children").and_then(Value::as_array).into_iter().flatten()
        .map(text_content).collect()
}

fn assert_framework_scene(framework: &str, state: &MutationState, click_count: usize) {
    assert!(state.error.is_none(), "{framework} Rust mutation callback error: {:?}", state.error);
    let snapshot = state.scene.snapshot().expect("Rust scene snapshot");
    let panel = find_by_id(&snapshot, "app").expect("app panel missing");
    assert_eq!(panel["attrs"]["theme"], "light", "{framework} theme");
    let counter = find_by_id(&snapshot, "counter").expect("counter missing");
    assert_eq!(text_content(counter), "Count: 256", "{framework} counter");
    let button = find_by_id(&snapshot, "event-button").expect("event button missing");
    assert_eq!(text_content(button), format!("Clicks: {click_count}"), "{framework} event count");
    let tracks = find_by_id(&snapshot, "tracks").expect("track list missing");
    let rows: Vec<_> = tracks.get("children").and_then(Value::as_array).expect("track children")
        .iter().filter(|node| node.get("name").and_then(Value::as_str) == Some("row")).collect();
    assert_eq!(rows.len(), 48, "{framework} rendered row count");
    assert_eq!(rows.first().and_then(|row| row["attrs"]["id"].as_str()), Some("track-40"));
    assert_eq!(rows.last().and_then(|row| row["attrs"]["id"].as_str()), Some("track-87"));
}

fn run_framework(root: &Path, framework: &str, bootstrap_hbc: &[u8], click_hbc: &[u8]) {
    let source = root.join(format!("dist/{framework}.js"));
    let output = root.join(format!("crates/hermes-gpui-spike/target/{framework}.hbc"));
    let app_hbc = compile_hbc(&source, &output);

    let mut state = MutationState::default();
    let mut runtime = HermesBridge::new().expect("create in-process Hermes VM");
    runtime.install_mutation_sink(
        apply_mutation_batch,
        (&mut state as *mut MutationState).cast::<c_void>(),
    ).expect("install live JSI-to-Rust mutation callback");
    runtime.eval_hbc(bootstrap_hbc).expect("install deterministic host globals");
    runtime.eval_hbc(&app_hbc).unwrap_or_else(|error| panic!("{framework} framework HBC failed: {error}"));
    assert!(state.batches >= 6, "{framework} expected framework flushes through JSI, got {}", state.batches);
    assert_framework_scene(framework, &state, 1000);
    let before_click_ops = state.scene.operations();

    runtime.eval_hbc(click_hbc).expect("invoke framework's persistent interactive event");
    assert_framework_scene(framework, &state, 1001);
    assert!(state.scene.operations() > before_click_ops, "{framework} interactive click emitted no Rust mutations");
    println!("LIVE_HERMES_FRAMEWORK_HBC_JSI_RUST_PASS:{framework}:batches={}:ops={}:nodes={}",
        state.batches, state.scene.operations(), state.scene.node_count());
}

fn main() {
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let root = manifest.parent().and_then(Path::parent).expect("repository root");
    let target = manifest.join("target");
    let bootstrap_hbc = compile_hbc(&manifest.join("bootstrap.js"), &target.join("bootstrap.hbc"));
    let click_hbc = compile_hbc(&manifest.join("click.js"), &target.join("click.hbc"));
    run_framework(root, "svelte", &bootstrap_hbc, &click_hbc);
    run_framework(root, "solid", &bootstrap_hbc, &click_hbc);
    println!("HERMES_ENGINE_DIGEST:{}", env!("HERMES_ENGINE_DIGEST"));
    println!("HERMES_BYTECODE_VERSION:{}", env!("HERMES_BYTECODE_VERSION"));
}
