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
