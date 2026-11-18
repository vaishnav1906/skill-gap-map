"""The in-browser app (docs/app) runs copies of the source files. Fail if they drift.  Fix: python scripts/build_web.py"""
from pathlib import Path

import pytest

from build_web import DEST, FILES

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("src, name", FILES.items())
def test_web_copy_matches_source(src, name):
    assert (DEST / name).read_bytes() == (ROOT / src).read_bytes(), f"run python scripts/build_web.py ({name})"


def test_app_only_needs_browser_packages():
    """The browser build installs numpy, pandas and plotly only."""
    for name in FILES:
        if name.endswith(".py"):
            text = (ROOT / name).read_text(encoding="utf-8")
            for pkg in ("scipy", "sklearn", "requests", "pyarrow"):
                assert f"import {pkg}" not in text and f"from {pkg}" not in text, (name, pkg)


def test_loader_mounts_every_file():
    page = (ROOT / "docs" / "app" / "index.html").read_text(encoding="utf-8")
    for name in FILES.values():
        assert f'src("{name}")' in page, name


def test_showcase_numbers_come_from_the_engine():
    """docs/showcase-data.js must match what the engine computes now.  Fix: python scripts/showcase_data.py"""
    import json

    from showcase_data import OUT, build
    shipped = json.loads(OUT.read_text(encoding="utf-8").removeprefix("window.SGM = ").rstrip().rstrip(";"))
    assert shipped == json.loads(json.dumps(build()))
