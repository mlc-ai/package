"""Single source of truth for the mlc-doxygen-bin release.

Bumping Doxygen means editing only this file (see "Bumping the version" in
README.md). Build scripts, package metadata, and the generated runtime module
``mlc_doxygen_bin/_version.py`` all derive from these values.
"""

__version__ = "1.17.0"
DOXYGEN_VERSION = "1.17.0"
DOXYGEN_ARCHIVE_SHA256 = "fa4c3dd78785abc11ccc992bc9c01e7a8c3120fe14b8a8dfd7cefa7014530814"

DOXYGEN_TAG = "Release_" + DOXYGEN_VERSION.replace(".", "_")
