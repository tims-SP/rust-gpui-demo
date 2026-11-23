use gpui_ui_mutation::Scene;
use serde_json::Value;
use std::{env, fs, process};
fn run() -> Result<(), String> {
    let path = env::args().nth(1).ok_or("missing trace JSON path")?;
    let input = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let v: Value = serde_json::from_str(&input).map_err(|e| e.to_string())?;
    let framework = v["framework"].as_str().ok_or("missing framework")?;
    let batches = v["batches"].as_array().ok_or("missing batches")?;
    let mut scene = Scene::default();
    for (i, batch) in batches.iter().enumerate() {
        scene.apply_batch(batch.as_array().ok_or("invalid batch")?)
            .map_err(|e| format!("batch {i}: {e}"))?;
    }
    let expected = &v["scene"];
    let actual = scene.snapshot()?;
    if actual != *expected {
        return Err(format!("scene snapshot mismatch for {framework}: root={:?}", actual.get("type")));
    }
    let operations = v["operations"].as_u64().ok_or("missing operation count")? as usize;
    if operations != scene.operations() {
        return Err(format!("operation count mismatch: expected {operations}, got {}", scene.operations()));
    }
    println!("RUST_MUTATION_TRACE_PARITY_PASS:{framework}:{}:{}", scene.operations(), scene.node_count());
    Ok(())
}
fn main() {
    if let Err(err) = run() {
        eprintln!("RUST_MUTATION_TRACE_FAIL: {err}");
        process::exit(1);
    }
}
