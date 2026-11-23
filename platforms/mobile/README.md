# GPUI Mobile compatibility adapter — G1 real-render evidence available

The canonical Svelte/Solid components are compiled and executed in the pinned
native Ibex 2/Hermes CI. Both resulting verified scene JSON files are consumed
by this *mobile API compatibility* view in gpui-mobile's existing Android/iOS
example's Home screen. The two targets therefore display identical data and UI
structure rather than separate hardcoded demonstration content.

- `home.rs`: an adapter for community `gpui-pre = 0.3.6`, **not** a copy of
  Zed GPUI v1.29.3. It validates source, count, theme, and all 48 tracks.
- `prepare-upstream.sh`: copies the adapter and the actual archived Hermes
  scene JSONs into a fresh gpui-mobile checkout; enables `solid-demo` feature.
- `verify-scenes.py`: blocks incorrect scene data before building.

For Android, build both features separately, copying each built .so into the
Gradle app before packaging two differently labeled APK artifacts. Since they
share an Android application ID, they are installed and run sequentially.
For iOS the same `home.rs` works with the separate community GPUI Mobile iOS
platform (subject to an actual simulator toolchain/runner and signing).

**G1 scene-render evidence:** Android Svelte/Solid screenshots were verified
on an API-34 x86_64 emulator using SwiftShader GLES and the opt-in backport;
The clean from-source Android CI
[#45283713120](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45283713120)
reports 2/2 `RENDER_PASS`: two independently built APKs (both Gradle attempt 1),
actual AVD pixel screenshots (Svelte 92.87%; Solid 92.90% coverage), scene
markers and live app PIDs. A previous successful replay
[#45282165716](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45282165716)
used the *same binary APKs* built in CI
[#45280068480](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45280068480)
to isolate the screenshot verifier fix before the final clean build. iOS Svelte/Solid simulator G1 had
previously passed in CI
[#45278354140](https://github.com/tims-SP/rust-gpui-demo/actions/runs/45278354140).

**Not yet proven:** HBC compiled/loaded *inside* Android/iOS, UI event
roundtrips, full frame timings or live JSI-to-Rust Mutation delivery.
G1 renders *precomputed* Hermes scenes; it is not a live HBC benchmark.

## G1 automatic boot acceptance (implemented on this branch)

See [six-platform auto-benchmark implementation contract](../../docs/MOBILE_AUTO_BENCHMARK.md).
Build with the `bench-auto` Cargo feature: the Rust GPUI Home view logs
`BENCH_G1_SCENE_BUILT` when its validated *element tree* is constructed.
Actions then invoke `g1_probe.py` to poll a genuine ADB or simctl screenshot
until its **scene-specific** pixels pass, or fail after a timeout. Results are
`{svelte,solid}-g1.json` with `actual_hermes_vm_on_device: false`.
The two stages are intentionally distinct; neither marker proves live HBC.

Local regression: `python3 -m unittest discover -s platforms/mobile/tests -p 'test_*.py' -v`.

## Android GLES renderer backport (experimental)

`vendor/gpui-pre-wgpu-0.3.6/` retains the Apache-2.0-licensed, pinned
published crate and backports Zed PR #67323's adapter-capability fallback.
`prepare-upstream.sh` overlays it through Cargo `[patch.crates-io]` without
modifying the canonical Svelte/Solid precomputed Hermes scene payloads.
The Android emulator CI disables guest Vulkan while testing this GLES path.
The GLES backport cleared both the original `65535 > 0` device Limits error
and the `EGL_BAD_ALLOC` surface failure. Its GL-only Instance feature is enabled
only for the emulator APK build, not for ARM64 physical-device builds or iOS.
The real screenshot replay gate has passed for both Svelte and Solid, with the
following independent checks:

| G1 Android | Result | Screenshot evidence |
|---|---|---|
| Svelte | PASS (attempt 3; process alive) | 1080×2340, background 92.87%, 59 text bands |
| Solid | PASS (attempt 3; process alive) | 1080×2340, background 92.90%, 59 text bands |

The baseline 0.3.6 source hash, license and patch scope are recorded in
`vendor/gpui-pre-wgpu-0.3.6/ANDROID_BACKPORT.md`.
Vulkan, physical ARM64 device runtime, native HBC/JSI and frame timing are
**not** claimed as verified by these G1 screenshot results.
