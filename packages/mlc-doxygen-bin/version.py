"""Single source of truth for the mlc-doxygen-bin release.

Bumping Doxygen means editing only this file (see "Bumping the version" in
README.md). Build scripts, package metadata, and the generated runtime module
``mlc_doxygen_bin/_version.py`` all derive from these values.
"""

__version__ = "1.18.0"
DOXYGEN_VERSION = "1.18.0"
DOXYGEN_ARCHIVE_SHA256 = "a1deed70a6785bbec95a2b2a9e419dc7f7b223a9d74a8644ae611c8e2dcdd354"

DOXYGEN_TAG = "Release_" + DOXYGEN_VERSION.replace(".", "_")
