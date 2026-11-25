#include <hermes/hermes.h>
#include <hermes/Public/JSOutOfMemoryError.h>
#include <jsi/jsi.h>

#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <string>
#include <utility>
#include <vector>

using namespace facebook;

namespace {
using MutationCallback = int (*)(void *, const uint8_t *, size_t);

struct RuntimeHandle {
  std::unique_ptr<facebook::hermes::HermesRuntime> runtime;
};

class OwnedBytes final : public jsi::Buffer {
public:
  explicit OwnedBytes(std::vector<uint8_t> bytes) : bytes_(std::move(bytes)) {}
  size_t size() const override { return bytes_.size(); }
  const uint8_t *data() const override { return bytes_.data(); }
private:
  std::vector<uint8_t> bytes_;
};

char *copy_string(const std::string &value) {
  auto *result = static_cast<char *>(std::malloc(value.size() + 1));
  if (result == nullptr) return nullptr;
  std::memcpy(result, value.data(), value.size());
  result[value.size()] = '\0';
  return result;
}

void set_error(char **out, const std::string &message) {
  if (out != nullptr) *out = copy_string(message);
}
} // namespace

extern "C" {

void *gpui_hermes_create() {
  auto config = ::hermes::vm::RuntimeConfig::Builder()
                    .withEnableEval(false)
                    .withMicrotaskQueue(true)
                    .withAsyncBreakCheckInEval(true)
                    .withES6BlockScoping(true)
                    .build();
  auto runtime = facebook::hermes::makeHermesRuntimeNoThrow(config);
  if (!runtime) return nullptr;
  auto *handle = new RuntimeHandle();
  handle->runtime = std::move(runtime);
  return handle;
}

void gpui_hermes_destroy(void *raw) {
  delete static_cast<RuntimeHandle *>(raw);
}

int gpui_hermes_install_mutation_sink(void *raw, MutationCallback callback,
                                      void *user_data, char **out_error) {
  auto *handle = static_cast<RuntimeHandle *>(raw);
  if (handle == nullptr || handle->runtime == nullptr || callback == nullptr) {
    set_error(out_error, "invalid Hermes mutation sink arguments");
    return 1;
  }
  try {
    jsi::Runtime &runtime = *handle->runtime;
    auto name = jsi::PropNameID::forUtf8(runtime, std::string("gpuiEmit"));
    auto function = jsi::Function::createFromHostFunction(
        runtime, name, 1,
        [callback, user_data](jsi::Runtime &rt, const jsi::Value &,
                              const jsi::Value *args, size_t count) -> jsi::Value {
          if (count != 1 || !args[0].isString()) {
            throw jsi::JSError(rt, "gpuiEmit expects one JSON string");
          }
          const std::string payload = args[0].asString(rt).utf8(rt);
          const int status = callback(
              user_data, reinterpret_cast<const uint8_t *>(payload.data()),
              payload.size());
          if (status != 0) {
            throw jsi::JSError(rt, "Rust GPUI mutation sink rejected the batch");
          }
          return jsi::Value::undefined();
        });
    runtime.global().setProperty(runtime, name, std::move(function));
    return 0;
  } catch (const ::hermes::vm::JSOutOfMemoryError &) {
    set_error(out_error, "Hermes out of memory while installing gpuiEmit");
    return 2;
  } catch (const std::exception &error) {
    set_error(out_error, error.what());
    return 1;
  }
}

int gpui_hermes_eval_hbc(void *raw, const uint8_t *data, size_t length,
                         char **out_value, char **out_error) {
  auto *handle = static_cast<RuntimeHandle *>(raw);
  if (handle == nullptr || handle->runtime == nullptr || data == nullptr || length == 0) {
    set_error(out_error, "invalid Hermes HBC evaluation arguments");
    return 1;
  }
  try {
    auto buffer = std::make_shared<OwnedBytes>(std::vector<uint8_t>(data, data + length));
    jsi::Value value = handle->runtime->evaluateJavaScript(buffer, "<gpui-hbc>");
    handle->runtime->drainMicrotasks();
    const std::string result = value.isUndefined()
        ? std::string("undefined")
        : value.toString(*handle->runtime).utf8(*handle->runtime);
    if (out_value != nullptr) *out_value = copy_string(result);
    return 0;
  } catch (const jsi::JSError &error) {
    set_error(out_error, error.getMessage());
    return 1;
  } catch (const ::hermes::vm::JSOutOfMemoryError &) {
    set_error(out_error, "Hermes out of memory while evaluating HBC");
    return 2;
  } catch (const std::exception &error) {
    set_error(out_error, error.what());
    return 1;
  }
}

void gpui_hermes_free_string(char *value) { std::free(value); }

} // extern "C"
