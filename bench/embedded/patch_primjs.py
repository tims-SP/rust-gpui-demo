#!/usr/bin/env python3
"""Give the upstream PrimJS test shell a strict cross-process bytecode mode."""
from pathlib import Path

file = Path(".primjs-src/testing/quickjs/compiler/qjs.cc")
source = file.read_text()
anchor = "int main(int argc, char **argv) {"
assert source.count(anchor) == 1
addition = r'''
static int bench_bytecode_io(LEPUSContext *ctx, const char *mode,
                             const char *input, const char *output) {
  size_t size = 0;
  uint8_t *bytes = lepus_load_file(ctx, &size, input);
  if (!bytes) { perror(input); return -1; }
  LEPUSValue value = LEPUS_UNDEFINED;
  if (!strcmp(mode, "--emit-bytecode")) {
    value = LEPUS_Eval(ctx, reinterpret_cast<const char *>(bytes), size, input,
                       LEPUS_EVAL_TYPE_GLOBAL | LEPUS_EVAL_FLAG_COMPILE_ONLY);
    if (!LEPUS_IsGCMode(ctx)) lepus_free(ctx, bytes);
    if (LEPUS_IsException(value)) {
      lepus_std_dump_error(ctx);
      return -1;
    }
    HandleScope root(ctx, &value, HANDLE_TYPE_LEPUS_VALUE);
    size_t bytecode_size = 0;
    uint8_t *compiled = LEPUS_WriteObject(
        ctx, &bytecode_size, value, LEPUS_WRITE_OBJ_BYTECODE);
    if (!compiled || !bytecode_size) {
      fprintf(stderr, "PrimJS bytecode compilation produced no bytes\n");
      return -1;
    }
    root.PushHandle(&compiled, HANDLE_TYPE_HEAP_OBJ);
    FILE *out = fopen(output, "wb");
    if (!out) { perror(output); return -1; }
    size_t n = fwrite(compiled, 1, bytecode_size, out);
    int close_ret = fclose(out);
    fprintf(stderr, "PRIMJS_BYTECODE_COMPILED=%zu\n", bytecode_size);
    if (!LEPUS_IsGCMode(ctx)) {
      lepus_free(ctx, compiled);
      LEPUS_FreeValue(ctx, value);
    }
    return n == bytecode_size && close_ret == 0 ? 0 : -1;
  }
  value = LEPUS_ReadObject(ctx, bytes, size, LEPUS_READ_OBJ_BYTECODE);
  if (!LEPUS_IsGCMode(ctx)) lepus_free(ctx, bytes);
  if (LEPUS_IsException(value)) {
    lepus_std_dump_error(ctx);
    return -1;
  }
  HandleScope root(ctx, &value, HANDLE_TYPE_LEPUS_VALUE);
  LEPUSValue global = LEPUS_GetGlobalObject(ctx);
  root.PushHandle(&global, HANDLE_TYPE_LEPUS_VALUE);
  fprintf(stderr, "PRIMJS_BYTECODE_LOADED=%zu\n", size);
  LEPUSValue result = LEPUS_EvalFunction(ctx, value, global);
  if (LEPUS_IsException(result)) {
    lepus_std_dump_error(ctx);
    return -1;
  }
  if (!LEPUS_IsGCMode(ctx)) {
    LEPUS_FreeValue(ctx, result);
    LEPUS_FreeValue(ctx, global);
  }
  return 0;
}

'''
source = source.replace(anchor, addition + anchor)
mode_anchor = "  LEPUSRuntime *rt;"
assert source.count(mode_anchor) == 1
source = source.replace(mode_anchor, '''  bool emit_bytecode = argc == 4 && !strcmp(argv[1], "--emit-bytecode");
  bool run_bytecode = argc == 3 && !strcmp(argv[1], "--run-bytecode");
  bool bytecode_mode = emit_bytecode || run_bytecode;
''' + mode_anchor, 1)
loop = "for (int i = 1; i < argc - 1; ++i)"
assert source.count(loop) == 1
source = source.replace(loop, "for (int i = 1; i < argc - 1 && !bytecode_mode; ++i)")
execute = "    if (eval_file(ctx, filename, time_top_level)) goto fail;"
assert source.count(execute) == 1
source = source.replace(execute, '''    if (bytecode_mode) {
      if (bench_bytecode_io(ctx, argv[1], argv[2],
                            emit_bytecode ? argv[3] : nullptr)) goto fail;
    } else if (eval_file(ctx, filename, time_top_level)) goto fail;''')
file.write_text(source)
print("patched PrimJS: cross-process bytecode compilation and loading")
