#!/usr/bin/env python3
"""Patch the pinned GPUI Mobile example for the isolated live-Hermes CI run."""
from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--example", type=Path, required=True, help="Pinned gpui-mobile/example directory")
    parser.add_argument("--repo", type=Path, required=True, help="rust-gpui-demo checkout")
    args = parser.parse_args()

    example = args.example.resolve()
    repo = args.repo.resolve()
    src = example / "src"
    cargo_toml = example / "Cargo.toml"
    lib_rs = src / "lib.rs"
    for path in (cargo_toml, lib_rs, repo / "platforms/mobile/live_hermes.rs"):
        if not path.is_file():
            raise SystemExit(f"missing required input: {path}")

    cargo = cargo_toml.read_text()
    bridge_path = Path(os.path.relpath(repo / "crates/hermes-gpui-spike", example)).as_posix()
    bridge_dependency = f'gpui-hermes-live-spike = {{ path = "{bridge_path}", optional = true }}'
    dependency_pattern = r'gpui-hermes-live-spike = \{ path = "[^"]+", optional = true \}'
    if re.search(dependency_pattern, cargo):
        cargo = re.sub(dependency_pattern, bridge_dependency, cargo, count=1)
    if "[features]\nlive-hermes" not in cargo:
        cargo = replace_once(
            cargo,
            "[dependencies]\n",
            '[features]\nlive-hermes = ["dep:gpui-hermes-live-spike"]\n\n[dependencies]\n',
            "Cargo feature insertion",
        )
    if bridge_dependency not in cargo:
        cargo = replace_once(
            cargo,
            'gpui-mobile = { path = ".." }\n',
            'gpui-mobile = { path = ".." }\n' + bridge_dependency + "\n",
            "Cargo live Hermes dependency",
        )
    if 'serde_json = "1"' not in cargo:
        cargo = replace_once(cargo, 'gpui-mobile = { path = ".." }\n',
                             'gpui-mobile = { path = ".." }\nserde_json = "1"\n',
                             "Cargo serde_json dependency")
    cargo_toml.write_text(cargo)

    lib = lib_rs.read_text()
    # In live-Hermes mode the original Router window is not compiled. Its
    # prelude traits, WindowOptions, and Router imports must follow the same
    # feature gate or `-D warnings` turns unused imports into build failures.
    old_mobile_imports = (
        '#[cfg(any(target_os = "ios", target_os = "android"))]\n'
        'use gpui::{prelude::*, App, WindowOptions};\n'
        '\n'
        '#[cfg(target_os = "android")]\n'
        'use gpui::Application;\n'
        '\n'
        '#[cfg(any(target_os = "ios", target_os = "android"))]\n'
        'use screens::Router;'
    )
    new_mobile_imports = (
        '#[cfg(any(target_os = "ios", target_os = "android"))]\n'
        'use gpui::App;\n'
        '\n'
        '#[cfg(all(any(target_os = "ios", target_os = "android"), not(feature = "live-hermes")))]\n'
        'use gpui::{prelude::*, WindowOptions};\n'
        '\n'
        '#[cfg(target_os = "android")]\n'
        'use gpui::Application;\n'
        '\n'
        '#[cfg(all(any(target_os = "ios", target_os = "android"), not(feature = "live-hermes")))]\n'
        'use screens::Router;'
    )
    if old_mobile_imports in lib:
        lib = replace_once(lib, old_mobile_imports, new_mobile_imports, "mobile imports live feature gate")
    elif new_mobile_imports not in lib:
        raise SystemExit("mobile imports: expected upstream imports were not found")

    if 'mod live_hermes;' not in lib:
        lib = replace_once(
            lib,
            "pub mod screens;\n",
            'pub mod screens;\n\n#[cfg(feature = "live-hermes")]\nmod live_hermes;\n',
            "mobile module declaration",
        )
    android_original = (
        '        log::info!("Application::run callback — opening window with Router");\n'
        '        open_main_window(cx);\n'
    )
    android_replacement = (
        '        #[cfg(feature = "live-hermes")]\n'
        '        live_hermes::open_main_window(cx);\n'
        '        #[cfg(not(feature = "live-hermes"))]\n'
        '        open_main_window(cx);\n'
    )
    if android_original in lib:
        lib = replace_once(lib, android_original, android_replacement, "Android live window entry point")
    elif android_replacement not in lib:
        raise SystemExit("Android live window entry point: existing patch is neither original nor expected form")
    old_ios = '''    gpui_mobile::ios::ffi::set_app_callback(Box::new(|cx: &mut App| {
        gpui_kit::init(cx);
        gpui_kit::component::Theme::change(gpui_kit::component::ThemeMode::Light, None, cx);
        screens::markdown::init(cx);
        cx.open_window(WindowOptions::default(), |window, cx| {
            let content = cx.new(|cx| screens::ai_chat::AiChat::new(window, cx));
            cx.new(|cx| gpui_kit::component::Root::new(content, window, cx))
        })
        .expect("open embedded Markdown view");
    }));
'''
    new_ios = '''    gpui_mobile::ios::ffi::set_app_callback(Box::new(|cx: &mut App| {
        #[cfg(feature = "live-hermes")]
        live_hermes::open_main_window(cx);
        #[cfg(not(feature = "live-hermes"))]
        {
            gpui_kit::init(cx);
            gpui_kit::component::Theme::change(gpui_kit::component::ThemeMode::Light, None, cx);
            screens::markdown::init(cx);
            cx.open_window(WindowOptions::default(), |window, cx| {
                let content = cx.new(|cx| screens::ai_chat::AiChat::new(window, cx));
                cx.new(|cx| gpui_kit::component::Root::new(content, window, cx))
            })
            .expect("open embedded Markdown view");
        }
    }));
'''
    if old_ios in lib:
        lib = replace_once(lib, old_ios, new_ios, "iOS live window entry point")
    elif not (
        'gpui_mobile::ios::ffi::set_app_callback(Box::new(|cx: &mut App| {\n'
        '        #[cfg(feature = "live-hermes")]\n'
        '        live_hermes::open_main_window(cx);'
    ) in lib:
        raise SystemExit("iOS live window entry point: existing patch is neither original nor expected form")
    # The upstream Android/iOS window helper is used only by the normal app
    # entry points. In the live-Hermes feature both entry points switch to
    # live_hermes::open_main_window, so keep the upstream helper out of that
    # build to satisfy the repository's `-D warnings` dead-code policy.
    old_window_cfg = (
        '#[cfg(any(target_os = "ios", target_os = "android"))]\n'
        'fn open_main_window(cx: &mut App) {'
    )
    new_window_cfg = (
        '#[cfg(all(any(target_os = "ios", target_os = "android"), not(feature = "live-hermes")))]\n'
        'fn open_main_window(cx: &mut App) {'
    )
    if old_window_cfg in lib:
        lib = replace_once(lib, old_window_cfg, new_window_cfg, "normal mobile window helper feature gate")
    elif new_window_cfg not in lib:
        raise SystemExit("normal mobile window helper: expected upstream cfg was not found")

    lib_rs.write_text(lib)

    destination = src / "live_hermes.rs"
    shutil.copyfile(repo / "platforms/mobile/live_hermes.rs", destination)

    print(f"GPUI_MOBILE_LIVE_HERMES_PATCH_PASS:{example}")


if __name__ == "__main__":
    main()
