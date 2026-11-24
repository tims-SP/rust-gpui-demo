use ibex2_runtime::engine::hermes::{DynamicCode, Hermes};
use std::{fs, path::PathBuf, process::Command};

fn main() {
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let source = manifest.join("probe.js");
    let bytecode = manifest.join("target/gpui-live-probe.hbc");
    fs::create_dir_all(bytecode.parent().expect("bytecode parent")).expect("create output dir");

    let compiler = Command::new(ibex2_runtime::HERMESC_PATH)
        .args(["-O", "-emit-binary", "-out"])
        .arg(&bytecode)
        .arg(&source)
        .output()
        .expect("launch the Hermes compiler pinned to the linked runtime");
    assert!(compiler.status.success(), "hermesc failed: {}", String::from_utf8_lossy(&compiler.stderr));
    let hbc = fs::read(&bytecode).expect("read compiled HBC");
    assert!(hbc.starts_with(b"\xc6\x1f\xbc\x03"), "output is not Hermes bytecode");

    let mut runtime = Hermes::new(DynamicCode::Closed).expect("create in-process Hermes VM");
    assert!(runtime.install_probe("__gpui_probe", "host-callback-ok"), "install stock JSI host function");
    let result = runtime.eval_bytes(&hbc).expect("execute HBC in the same process as the Rust host");
    assert_eq!(result, "host-callback-ok:42");
    println!("IN_PROCESS_HERMES_HBC_JSI_PROBE_PASS:{result}");
    println!("HERMES_ENGINE_DIGEST:{}", ibex2_runtime::LINKED_ENGINE_DIGEST);
    println!("HERMES_BYTECODE_VERSION:{}", ibex2_runtime::LINKED_BYTECODE_VERSION);
}
