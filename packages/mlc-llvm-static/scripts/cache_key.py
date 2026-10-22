"""Fingerprint compiled SDK inputs independently of wheel/frontend changes."""
import hashlib
import inspect
import json

import prepare_llvm
import split_sdk

recipe = [{name: {key: spec[key] for key in ("version", "sha256")}
           for name, spec in prepare_llvm.SOURCES.items()}, prepare_llvm.DEFAULT_TARGETS]
for module, names in (
    (prepare_llvm, ("configure", "install", "build_dependencies", "build_llvm")),
    (split_sdk, ("read_components", "closure", "partitions", "cmake_value", "distribution_options", "record_build")),
):
    recipe.extend(inspect.getsource(getattr(module, name)) for name in names)
key = hashlib.sha256(json.dumps(recipe, sort_keys=True).encode()).hexdigest()
print("key=" + key)
# One-time migration from the dev1 key that also hashed source-fetch code and
# URLs. This exact old recipe has identical pinned source digests, compilation
# flags, and export generation. Any future compiled-input change disables it.
compatible = ("e9202c0a3c655a793eb8673a07aabccc199a7344b4bc6230ca8ca69ff6bb6d0f"
              if key == "8e583d8c1ecb82af3a8f75932c94835442781184fab13b5b64ceab5b3cefe0c2" else "")
print("compatible_key=" + compatible)
