// Minimal, persistent JSI host for browser-embedded Hermes VM.
// This is not the Hermes command-line tool and does not enter its main().
// The bytecode is compiled by the *matching* upstream hermesc host compiler.
#include <hermes/hermes.h>
#include <jsi/jsi.h>

#include <cstdio>
#include <cstdlib>
#include <memory>
#include <string>
#include <vector>

using facebook::jsi::Function;
using facebook::jsi::PropNameID;
using facebook::jsi::Runtime;
using facebook::jsi::Value;

namespace {
// The browser retains this VM until the page is closed.
std::unique_ptr<facebook::hermes::HermesRuntime> engine;
int observed_checksum = -1;

int registerHostConsole(Runtime &rt) {
  auto log = Function::createFromHostFunction(
      rt, PropNameID::forAscii(rt, "log"), 1,
      [](Runtime &runtime, const Value &, const Value *args,
         size_t count) -> Value {
        for (size_t i = 0; i < count; ++i) {
          const std::string value = args[i].toString(runtime).utf8(runtime);
          std::puts(value.c_str());
          constexpr char prefix[] = "HERMES_SHARED_OK=";
          if (value.compare(0, sizeof(prefix) - 1, prefix) == 0) {
            observed_checksum = std::atoi(value.c_str() + sizeof(prefix) - 1);
          }
        }
        return Value::undefined();
      });
  facebook::jsi::Object console(rt);
  console.setProperty(rt, "log", std::move(log));
  rt.global().setProperty(rt, "console", std::move(console));
  return 0;
}
} // namespace

// Receives a file path in Emscripten MEMFS. Returns exact computed checksum;
// returns a negative code on OS/bytecode/JS failures. JS itself is not run by V8.
extern "C" int hermes_run_hbc_file(const char *path) {
  if (!path || !*path)
    return -1;
  FILE *file = std::fopen(path, "rb");
  if (!file)
    return -2;
  if (std::fseek(file, 0, SEEK_END) || std::ftell(file) <= 0) {
    std::fclose(file);
    return -3;
  }
  long count = std::ftell(file);
  std::rewind(file);
  std::string data(static_cast<size_t>(count), '\0');
  const size_t read = std::fread(data.data(), 1, data.size(), file);
  std::fclose(file);
  if (read != data.size())
    return -4;
  if (!engine) {
    engine = facebook::hermes::makeHermesRuntimeNoThrow();
    if (!engine)
      return -5;
    registerHostConsole(*engine);
  }
  observed_checksum = -1;
  auto bytecode = std::make_shared<facebook::jsi::StringBuffer>(std::move(data));
  // Hermes JSI detects and executes matching HBC; it is NOT recompiled by JS.
  try {
    engine->evaluateJavaScript(bytecode, "shared.hbc");
  } catch (const std::exception &error) {
    std::fprintf(stderr, "HERMES_JSI_EVAL_ERROR: %s\n", error.what());
    return -6;
  }
  return observed_checksum;
}
