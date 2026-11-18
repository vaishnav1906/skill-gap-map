"""Write docs/showcase-data.js: every number on the overview page, computed by the real engine.

    python scripts/showcase_data.py

A test fails if the page's numbers drift from what the engine produces.
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import gap_engine as ge  # noqa: E402

OUT = ROOT / "docs" / "showcase-data.js"
PROFILE = ["Python", "Machine learning", "Deep learning", "NumPy", "Pandas", "Excel", "Data analysis", "Market research",
           "Digital marketing", "MS Office"]  # the app's default "BTech (AI) + MBA marketing" profile
ROLE, YEARS, THETA = "Data Analyst", 1, 0.6
ROLES = ["Data Analyst", "Business Analyst", "Data Scientist", "ML / AI Engineer", "Data Engineer", "BI / Reporting",
         "Product / Marketing", "Software Engineer"]


def build() -> dict:
    df = ge.load_postings()
    stats = json.loads((ROOT / "data" / "coverage.json").read_text(encoding="utf-8"))
    m = ge.build_market(ge.filter_postings(df, [ROLE], None, YEARS))
    p = ge.plan(m, PROFILE, THETA, 6)
    gap = ge.need(m.sizes, THETA) - ge.matched(m, PROFILE)
    rf = ge.role_fit(df, PROFILE, THETA, ROLES, None, YEARS)
    everything = ge.build_market(df)
    dem = ge.skill_demand(everything)
    chk = ge.check_plan(m, PROFILE, THETA, p)
    return {
        "postings": int(stats["postings"]), "skills": int(len(dem)),
        "companies": int(df["company"].replace("", np.nan).nunique()),
        "salary_disclosed": int(stats["salary_disclosed"]),
        "profile": PROFILE, "role": ROLE, "years": YEARS, "theta": THETA,
        "market": int(m.n), "start": int(p["start"]),
        "steps": [{"skills": list(s["skills"]), "also": list(s.get("also", ())), "gain": int(s["gain"]),
                   "reachable": int(s["reachable"]),
                   "weeks": float(s["weeks"])} for s in p["steps"]],
        "check": {"k": chk["k"], "ok": bool(chk["ok"]), "pool": chk["pool"]} if chk else None,
        "short_by": {"1": int((gap == 1).sum()), "2": int((gap == 2).sum()), "3plus": int((gap >= 3).sum())},
        "roles": [{"role": r.family, "postings": int(r.postings), "reachable": int(r.reachable), "ranked": bool(r.rankable)}
                  for r in rf.itertuples()],
        "top_skills": [{"skill": r.skill, "share": round(float(r.share), 4)} for r in dem.head(10).itertuples()],
    }


def main():
    data = build()
    OUT.write_text("window.SGM = " + json.dumps(data, indent=1) + ";\n", encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
