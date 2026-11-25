use gpui_ui_mutation::Scene;
use serde_json::{json, Value};
use std::{env, fs, path::PathBuf, process, time::Instant};

fn quantile(sorted: &[u64], fraction: f64) -> u64 {
    sorted[(((sorted.len() - 1) as f64) * fraction).ceil() as usize]
}

fn run() -> Result<(), String> {
    let path = env::args().nth(1).ok_or("missing trace JSON path")?;
    let input = fs::read_to_string(&path).map_err(|e| e.to_string())?;
    let v: Value = serde_json::from_str(&input).map_err(|e| e.to_string())?;
    let framework = v["framework"].as_str().ok_or("missing framework")?;
    let batches = v["batches"].as_array().ok_or("missing batches")?;
    let expected = &v["scene"];
    let operations = v["operations"].as_u64().ok_or("missing operation count")? as usize;

    // Warm-up and semantic gate using the actual Hermes-exported JSON batches.
    let mut scene = Scene::default();
    for (i, batch) in batches.iter().enumerate() {
        scene.apply_batch(batch.as_array().ok_or("invalid batch")?)
            .map_err(|e| format!("batch {i}: {e}"))?;
    }
    if scene.snapshot()? != *expected {
        return Err(format!("scene snapshot mismatch for {framework}"));
    }
    if scene.operations() != operations {
        return Err(format!("operation count mismatch for {framework}"));
    }
    println!("RUST_MUTATION_TRACE_PARITY_PASS:{framework}:{}:{}",
        scene.operations(), scene.node_count());

    // Seven independent Rust scene applications. This measures apply_batch
    // including transactional cloning and excludes Hermes execution, JSON
    // serialization/parsing, JSI dispatch and GPU presentation.
    let mut samples = Vec::with_capacity(7);
    for trial in 0..7 {
        let mut current = Scene::default();
        let started = Instant::now();
        for (i, batch) in batches.iter().enumerate() {
            current.apply_batch(batch.as_array().ok_or("invalid batch")?)
                .map_err(|e| format!("trial {trial} batch {i}: {e}"))?;
        }
        let elapsed_us = started.elapsed().as_micros() as u64;
        if current.operations() != operations || current.snapshot()? != *expected {
            return Err(format!("Rust mutation replay drift in trial {trial}"));
        }
        samples.push(elapsed_us);
    }
    let mut sorted = samples.clone();
    sorted.sort_unstable();
    let result = json!({
        "schema":"rust-hermes-mutation-apply/v1",
        "framework":framework,
        "source":"actual-Ibex2-Hermes-HBC-exported-batches",
        "scope":"Rust-apply-batch-CPU-including-transactional-cloning",
        "includes_jsi":false,"includes_gpu":false,
        "operations":operations,"batches":batches.len(),
        "independent_trials":7,"elapsed_us":samples,
        "p50_us":quantile(&sorted,0.50),
        "p95_us":quantile(&sorted,0.95),
        "p99_us":quantile(&sorted,0.99),
    });
    let output = PathBuf::from(path).with_file_name(format!("{framework}-rust-apply.json"));
    fs::write(&output, serde_json::to_vec_pretty(&result).map_err(|e|e.to_string())?)
        .map_err(|e|e.to_string())?;
    println!("RUST_MUTATION_APPLY_BENCH_PASS:{framework}:p50={}us:p95={}us",
        result["p50_us"],result["p95_us"]);
    Ok(())
}

fn main() {
    if let Err(err) = run() {
        eprintln!("RUST_MUTATION_TRACE_FAIL: {err}");
        process::exit(1);
    }
}
