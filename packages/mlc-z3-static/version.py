"""Single source of truth for the mlc-z3-static release.

Bumping Z3 means editing only this file (see "Bumping the version" in
README.md). Build scripts, package metadata, and the generated runtime module
``mlc_z3_static/_version.py`` all derive from these values.
"""

__version__ = "5.3.1"
Z3_VERSION = "5.3.1"
Z3_COMMIT = "ac9156f97cb44e56472e1c841f7a2beb1e976b24"
Z3_ARCHIVE_SHA256 = "33558971c286653d47b03f97f9f973d0350629c827cacda2583608ba14d74ea6"

Z3_TAG = f"z3-{Z3_VERSION}"
