"""Single source of truth for the mlc-z3-static release.

Bumping Z3 means editing only this file (see "Bumping the version" in
README.md). Build scripts, package metadata, and the generated runtime module
``mlc_z3_static/_version.py`` all derive from these values.
"""

__version__ = "4.16.0"
Z3_VERSION = "4.16.0"
Z3_COMMIT = "ddb49568d3520e99799e364fb22f35fc67d887b1"
Z3_ARCHIVE_SHA256 = "34deac6d0d46002b1040c56a51c4385ebb4ea56baa95fa8dd66e315a25b0cfa6"

Z3_TAG = f"z3-{Z3_VERSION}"
