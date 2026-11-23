#!/usr/bin/env python3
"""Instrument real Escargot disk cache; do not mislabel it source-free bytecode."""
from pathlib import Path

shell = Path(".escargot-src/src/shell/Shell.cpp")
source = shell.read_text()
anchor = "PersistentRefHolder<VMInstanceRef> instance = VMInstanceRef::create();"
assert source.count(anchor) >= 1
replacement = '''const char* benchCacheDir = getenv("ESCARGOT_BENCH_CACHE_DIR");
    PersistentRefHolder<VMInstanceRef> instance =
        VMInstanceRef::create(nullptr, nullptr, benchCacheDir);
#if defined(ENABLE_CODE_CACHE)
    if (benchCacheDir && *benchCacheDir) {
        instance->setCodeCacheMinSourceLength(0);
    }
#endif'''
pos = source.rfind(anchor)
source = source[:pos] + source[pos:].replace(anchor, replacement, 1)
shell.write_text(source)

cache = Path(".escargot-src/src/codecache/CodeCache.cpp")
source = cache.read_text()
hit = 'ESCARGOT_LOG_INFO("[CodeCache] Load CodeCache Done (%s)\\n", script->srcName()->toUTF8StringData().data());'
assert source.count(hit) == 1, "Escargot cache load API changed"
source = source.replace(hit, hit + '\n        if (getenv("ESCARGOT_BENCH_CACHE_DIR")) fprintf(stderr, "ESCARGOT_BENCH_CACHE_HIT\\n");')
store = "bool result = postCacheWriting(cacheIndex);"
assert source.count(store) >= 2
pos = source.index(store, source.index("bool CodeCache::storeGlobalCache"))
source = source[:pos] + source[pos:].replace(store,
    store + '\n    if (result && getenv("ESCARGOT_BENCH_CACHE_DIR")) fprintf(stderr, "ESCARGOT_BENCH_CACHE_STORE\\n");', 1)
cache.write_text(source)
print("patched Escargot: persistent cache directory and true load/store proof")
