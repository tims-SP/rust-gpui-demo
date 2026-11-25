# Android GLES low-capability renderer backport

Base: published `gpui-pre-wgpu` 0.3.6, the exact GPUI Mobile dependency.
Source SHA256: `05515b32799b1767d69300921c1b562cd53104965211a0e8905acdc7aa18e693` (`gpui-pre-wgpu-0.3.6.crate`).
License: Apache-2.0 (upstream LICENSE-APACHE retained).

Minimal capability-based backport from Zed PR https://github.com/zed-industries/zed/pull/67323:
- GL adapters missing VERTEX_STORAGE or FRAGMENT_STORAGE request WebGL2-downlevel Limits.
- On such adapters, reuse GPUI 0.3.6's existing WebGL texture-backed
  instance transport and shader path, instead of using shader storage buffers.
- Vulkan and GL with both storage capabilities keep their existing path.
- No renderer feature is disabled just to make CI green; on-device scene pixels
  and process survival remain the acceptance criteria.

The old function name `uses_webgl_instance_data` is kept for 0.3.6 compatibility.
This is intentionally not a full GPUI dependency upgrade, nor the unrelated
subpixel shader refactor in Zed #67323 (unsupported dual-source is disabled).

### Android Emulator EGL surface follow-up

2026-11-24 Android G1 CI #45278222779 confirmed the backport selected GL,
requested compute_workgroups=0 and got past request_device, but failed during
`Surface::configure`: `eglCreateWindowSurface: EGL_BAD_ALLOC` / `Invalid surface`.
The emulator-only build script enables the opt-in `android-gles-only` feature
which restricts wgpu Instance creation to GL instead of requesting both GL
and Vulkan for one AndroidNativeWindow. It is only a hypothesis until an on-device
retest verifies a valid configured Surface and drawn GPUI scene.
