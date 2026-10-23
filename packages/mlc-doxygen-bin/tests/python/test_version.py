"""Version metadata of the installed mlc-doxygen-bin wheel."""
from __future__ import annotations

import mlc_doxygen_bin


def test_package_version_is_based_on_doxygen_version() -> None:
    # __version__ may add a PEP 440 suffix such as .post1 to the upstream release.
    assert mlc_doxygen_bin.__version__.startswith(mlc_doxygen_bin.DOXYGEN_VERSION)


def test_doxygen_tag_matches_version() -> None:
    expected = "Release_" + mlc_doxygen_bin.DOXYGEN_VERSION.replace(".", "_")
    assert mlc_doxygen_bin.DOXYGEN_TAG == expected


def test_metadata_records_pinned_source() -> None:
    metadata = mlc_doxygen_bin.metadata()
    assert metadata["doxygen_version"] == mlc_doxygen_bin.DOXYGEN_VERSION
    assert metadata["doxygen_tag"] == mlc_doxygen_bin.DOXYGEN_TAG
    assert metadata["package_version"] == mlc_doxygen_bin.__version__
