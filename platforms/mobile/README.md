# GPUI Mobile compatibility adapter — BUILD-only until device proof

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

**Not yet proven:** HBC compiled/loaded *inside* Android/iOS, UI interaction,
mobile screenshots, full frame times, or live JSI-to-Rust Mutation delivery.
A correct APK library and identical scene JSON do not establish those gates.
