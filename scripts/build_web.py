"""Copy the app's source and data into docs/app/src so the in-browser (stlite) version can load them.

    python scripts/build_web.py

Run after changing the app or the data, then redeploy. A test fails if the copies are out of date.
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "docs" / "app" / "src"
# source -> published name (static hosts often skip dot-folders, so the theme is published as a plain file)
FILES = {"app.py": "app.py", "gap_engine.py": "gap_engine.py", "skills.py": "skills.py", "ui.py": "ui.py",
         ".streamlit/config.toml": "streamlit-config.toml", "data/postings.csv.gz": "postings.csv.gz",
         "data/coverage.json": "coverage.json"}


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    for src, name in FILES.items():
        shutil.copy2(ROOT / src, DEST / name)
        print("copied", src, "->", name)


if __name__ == "__main__":
    main()
