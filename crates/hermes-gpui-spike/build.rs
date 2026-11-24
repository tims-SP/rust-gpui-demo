use std::{env, path::PathBuf};

fn main() {
    let include_dir = env::var("DEP_HERMES_LEAN_INCLUDE_DIR")
        .expect("hermes-lean-sys must export the pinned Hermes include directory");
    let hermesc = env::var("DEP_HERMES_LEAN_HERMESC_PATH")
        .expect("hermes-lean-sys must export the matching hermesc path");
    let engine_digest = env::var("DEP_HERMES_LEAN_LINKED_ENGINE_DIGEST")
        .expect("hermes-lean-sys must export the exact linked engine digest");
    let bytecode_version = env::var("DEP_HERMES_LEAN_BYTECODE_VERSION")
        .expect("hermes-lean-sys must export the HBC bytecode version");
    println!("cargo:rustc-env=HERMESC_PATH={hermesc}");
    println!("cargo:rustc-env=HERMES_ENGINE_DIGEST={engine_digest}");
    println!("cargo:rustc-env=HERMES_BYTECODE_VERSION={bytecode_version}");
    println!("cargo:rerun-if-changed=src/hermes_shim.cc");
    let mut build = cc::Build::new();
    build.cpp(true).file("src/hermes_shim.cc").include(PathBuf::from(include_dir));
    // cc-rs maps this to /std:c++17 on MSVC and -std=c++17 on clang/gcc.
    // The pinned Hermes public headers use C++17 types (string_view, variant).
    build.std("c++17");
    // The JSI shim intentionally translates C++ exceptions into Rust errors.
    build.flag_if_supported("/EHsc").warnings(true).compile("gpui_hermes_shim");
}
