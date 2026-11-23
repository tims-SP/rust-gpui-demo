# Evidence ledger (2026-11-23)

| Test | Evidence | Status |
|---|---|---|
| Git history preserved | Archive tag `archive/pre-hermes-six-platform-20261123` -> `7e398212c1d9450c95e3b86b4a60604eb13f6df9` | Verified |
| Svelte custom renderer compiles | Local Node build `BUILD_OK=svelte` | Verified |
| Solid universal renderer compiles | Local Node build `BUILD_OK=solid` | Verified |
| JS semantic parity | `CUSTOM_RENDERER_PARITY_PASS` local Node smoke | Verified |
| Hermes HBC JS semantic parity | CI after pushing `p0-hermes.yml` | Pending |
| Rust mutation test | CI after pushing | Pending |
| Real Linux GPUI rendering | Screenshot + input + frame timings | Not implemented |
| Web GPUI | Canvas pixels in Chromium | Not implemented |
| Windows, macOS, iOS, Android | Build, Run, Render distinct evidence | Not implemented |

## Known real fixes

1. Solid universal `removeNode(parent,node)` required explicit second argument;
   using the first detached the entire list during the first window move.
2. A keyed reconciliation can request `insert(node, node)`. That must be a no-op
   rather than detaching the anchor before computing its insertion index.
3. Initial package pins conflicted (`babel-preset-solid@1.9.19` required
   `solid-js >=1.9.16`); corrected to `1.9.20`.
4. Babel universal output imports `insertNode`, not only `insert`;
   the public renderer now exports both.

Node baseline timings are intentionally not published as full UI frame results.
