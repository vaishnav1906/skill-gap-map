"""Build data/postings.csv.gz from the public Naukri job-postings dataset.

    python scripts/prepare_data.py                    # downloads the raw file (~28 MB)
    python scripts/prepare_data.py path/to/raw.jsonl  # or use a local copy

Source: "Job postings for Software Engineers and Data Scientists in Naukri" by muhammetakkurt on Hugging Face
(https://huggingface.co/datasets/muhammetakkurt/naukri-jobs-dataset), file naukri_data_scientist.jsonl,
licensed CC BY-NC 4.0. The processed file keeps only what the app needs and inherits that licence.
"""
import json
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from skills import TAG_TO_SKILL, normalise_tag, skills_from_tags, skills_in_order  # noqa: E402

RAW_URL = "https://huggingface.co/datasets/muhammetakkurt/naukri-jobs-dataset/resolve/main/naukri_data_scientist.jsonl"
OUT = ROOT / "data" / "postings.csv.gz"
STATS = ROOT / "data" / "coverage.json"
MIN_TAG_SKILLS = 3  # below this, the description tops up the requirements
MAX_REQUIREMENTS = 8  # same cap the portal puts on tags
TEMPLATE_COMPANIES = 3  # a description used word for word by this many companies is boilerplate, not a requirement list

# First matching rule wins, so the specific families come before the broad ones.
FAMILIES = [
    # "scientist" alone also matches lab jobs (forensic, food, dairy scientist), so it needs a data/AI qualifier
    ("Data Scientist", r"data scien|\b(?:applied|research|ml|ai|machine learning|decision|nlp|quantitative) scientist\b"),
    # a title that names the role outright wins over tool keywords ("Data Analyst - SQL, Tableau" is an analyst)
    ("Data Engineer", r"data engineer|data quality engineer"),
    ("Data Analyst", r"data analy"),
    ("ML / AI Engineer", r"machine learning|\bml\b|mlops|\bai\b|artificial intelligence|deep learning|\bnlp\b|computer vision"
                         r"|gen ?ai|\bllm|\bai/ml|\baiml\b"),
    ("Business Analyst", r"business analy|\bba\b|business systems analy|functional analyst|business consultant"),
    ("BI / Reporting", r"\bbi\b|power ?bi|tableau|business intelligence|reporting|\bmis\b|qlik|visuali[sz]ation"),
    ("Data Analyst", r"analytics|\bsql analyst|insights analyst|quantitative analyst|research analyst"),
    ("Product / Marketing", r"product (?:analy|manag|owner)|marketing|growth|\bseo\b|digital|brand|campaign"),
    ("Data Engineer", r"big data|\betl\b|data platform|pyspark|\bspark\b|snowflake|databricks|data architect"
                      r"|data model|data warehouse|\bdwh\b|informatica|hadoop|data integration|data pipeline"),
    # engineering titles that are not software jobs
    ("Other", r"sales engineer|\bgis\b|civil|mechanical|electrical|field engineer|service engineer|site engineer"
              r"|network engineer|support engineer|quality engineer|process engineer|design engineer|test engineer"
              r"|\bqa engineer|\bscientist\b"),
    ("Software Engineer", r"software|developer|engineer|programmer|full ?stack|backend|front ?end|devops|\bsde\b|architect"),
]
FAMILY_NAMES = list(dict.fromkeys([f for f, _ in FAMILIES] + ["Other"]))

CITY_ALIASES = {
    "bengaluru": "Bengaluru", "bangalore": "Bengaluru", "bangalore rural": "Bengaluru", "bengaluru rural": "Bengaluru",
    "hyderabad": "Hyderabad", "secunderabad": "Hyderabad", "pune": "Pune", "chennai": "Chennai",
    "mumbai": "Mumbai", "navi mumbai": "Mumbai", "thane": "Mumbai", "mumbai suburbs": "Mumbai", "mumbai suburban": "Mumbai",
    "delhi": "Delhi NCR", "new delhi": "Delhi NCR", "delhi ncr": "Delhi NCR", "gurgaon": "Delhi NCR",
    "gurugram": "Delhi NCR", "noida": "Delhi NCR", "greater noida": "Delhi NCR", "ghaziabad": "Delhi NCR",
    "faridabad": "Delhi NCR", "kolkata": "Kolkata", "ahmedabad": "Ahmedabad", "gandhinagar": "Ahmedabad",
    "remote": "Remote", "work from home": "Remote", "wfh": "Remote", "temp. wfh": "Remote",
    # hiring anywhere: shown for every city filter
    "india": "Pan-India", "pan india": "Pan-India", "anywhere in india": "Pan-India", "across india": "Pan-India",
}


def family_of(title: str) -> str:
    t = title.lower()
    for name, pat in FAMILIES:
        if re.search(pat, t):
            return name
    return "Other"


def cities_of(location) -> list[str]:
    if not isinstance(location, str) or not location.strip():
        return ["Other"]
    loc = re.sub(r"^\s*hybrid\s*-\s*", "", location, flags=re.I)
    out = []
    for part in re.split(r"[,/]", loc):
        p = re.sub(r"\(.*?\)", "", part).strip().lower()
        p = re.sub(r"^hybrid\s*-\s*", "", p)
        if p:
            out.append(CITY_ALIASES.get(p, "Other"))
    return sorted(set(out)) or ["Other"]


def experience_of(text) -> tuple[float, float]:
    m = re.match(r"\s*(\d+)\s*-\s*(\d+)\s*Yrs", str(text))
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        return (lo, hi) if lo <= hi else (hi, lo)
    m = re.match(r"\s*(\d+)\s*Yrs", str(text))  # "0 Yrs" (freshers only), "8 Yrs"
    if m:
        return (int(m.group(1)), int(m.group(1)))
    return (float("nan"), float("nan"))


def _lakh(num: str, unit: str) -> float:
    v = float(num.replace(",", ""))
    unit = unit.lower()
    if unit.startswith("cr"):
        return v * 100
    if unit.startswith("lac"):
        return v
    return v / 1e5  # plain rupees, e.g. "50,000"


def salary_of(text) -> tuple[float, float]:
    """Annual pay in lakh rupees.

    '12-15 Lacs PA' -> (12, 15); '80 Lacs-1.5 Cr PA' -> (80, 150); '50,000-3 Lacs PA' -> (0.5, 3); '6 Lacs PA' -> (6, 6).
    Undisclosed, unpaid or anything else -> NaN.
    """
    nan = (float("nan"), float("nan"))
    t = re.sub(r"\s*\(.*?\)\s*$", "", str(text).strip())  # "45-55 Lacs PA (Including Variable: 8.0%)"
    m = re.fullmatch(r"([\d.,]+)\s*(?:-\s*([\d.,]+))?\s*(?:/\s*month|PM)", t, flags=re.I)  # monthly rupees
    if m:
        lo = float(m.group(1).replace(",", "")) * 12 / 1e5
        hi = float((m.group(2) or m.group(1)).replace(",", "")) * 12 / 1e5
        return (round(lo, 2), round(hi, 2)) if 0 < lo <= hi <= 500 else nan
    m = re.fullmatch(r"([\d,]{4,})\s*-\s*([\d,]{4,})\s*PA", t, flags=re.I)  # plain rupees, "80,000-1,00,000 PA"
    if m:
        lo, hi = (float(x.replace(",", "")) / 1e5 for x in m.groups())
        return (round(lo, 2), round(hi, 2)) if 0 < lo <= hi <= 500 else nan
    m = re.fullmatch(r"([\d.,]+)\s*(Cr|Lacs?)?\s*-\s*([\d.,]+)\s*(Cr|Lacs?)\s*PA", t, flags=re.I)
    if m:
        lo_num, lo_unit, hi_num, hi_unit = m.groups()
        if lo_unit is None:
            # "50,000-3 Lacs": a number in the thousands is plain rupees; otherwise it shares the upper unit
            lo_unit = "rs" if float(lo_num.replace(",", "")) >= 1000 else hi_unit
        lo, hi = _lakh(lo_num, lo_unit), _lakh(hi_num, hi_unit)
    else:
        m = re.fullmatch(r"([\d.,]+)\s*(Cr|Lacs?)\s*PA", t, flags=re.I)
        if not m:
            return nan
        lo = hi = _lakh(m.group(1), m.group(2))
    if not (0 < lo <= hi <= 500):
        return nan
    return (round(lo, 2), round(hi, 2))


def _norm(x) -> str:
    return re.sub(r"\W+", " ", str(x).lower()).strip()


def load_raw(path: str | None) -> pd.DataFrame:
    if path:
        return pd.read_json(path, lines=True)
    print("downloading", RAW_URL)
    with urllib.request.urlopen(RAW_URL, timeout=300) as r:
        lines = r.read().decode("utf-8").splitlines()
    return pd.DataFrame([json.loads(x) for x in lines if x.strip()])


def requirements(tag_skills: set, text_skills_in_order: list, template: bool = False) -> set:
    """The portal's key-skill tags (what recruiters filter on; at most 8) are the requirements.

    Long descriptions list many nice-to-haves, and counting them made short postings look easy and long ones
    impossible. The description only tops up postings whose tags name fewer than MIN_TAG_SKILLS skills: it adds
    skills in the order they are first mentioned, stops at MAX_REQUIREMENTS, and is ignored when it is boilerplate
    shared word for word by several companies.
    """
    req = set(tag_skills)
    if len(req) >= MIN_TAG_SKILLS or template:
        return req
    for s in text_skills_in_order:
        if len(req) >= MAX_REQUIREMENTS:
            break
        req.add(s)
    return req


def main(path: str | None = None):
    raw = load_raw(path)
    n_raw = len(raw)
    df = raw.drop_duplicates("jobId")
    n_unique_id = len(df)
    # The same ad is often posted many times (once per city, or re-posted). Keep one per company + title +
    # description, and merge the cities it was posted in.
    key = df["companyName"].map(_norm) + "|" + df["title"].map(_norm) + "|" + df["jobDescription"].map(_norm)
    df = df.assign(_key=key.values, _cities=df["location"].map(cities_of).values)
    merged = df.groupby("_key")["_cities"].agg(lambda cs: sorted({c for cl in cs for c in cl}))
    df = df.drop_duplicates("_key").copy()
    df["_cities"] = df["_key"].map(merged).map(lambda cs: [c for c in cs if c != "Other"] or ["Other"])

    tag_lists = df["tagsAndSkills"].fillna("").map(lambda s: [t for t in s.split(",") if t.strip()])
    tag_sk = list(tag_lists.map(skills_from_tags))
    text_sk = list(df["jobDescription"].fillna("").map(skills_in_order))
    desc = df["jobDescription"].map(_norm)
    companies_per_desc = df.groupby(desc.values)["companyName"].nunique()
    template = (desc.map(companies_per_desc) >= TEMPLATE_COMPANIES) & (desc.str.len() > 0) & (desc != "nan")
    df["_req"] = ["|".join(sorted(requirements(a, b, t))) for a, b, t in zip(tag_sk, text_sk, template)]
    # Large employers post many near-identical requisitions (same title, skills and experience, reworded text).
    # Count each once so one employer cannot dominate a market; merge their cities.
    key2 = (df["companyName"].map(_norm) + "|" + df["title"].map(_norm) + "|" + df["_req"] + "|"
            + df["experience"].astype(str))
    df["_key2"] = key2.values
    merged2: dict[str, set] = {}
    for k2, cl in zip(df["_key2"], df["_cities"]):
        merged2.setdefault(k2, set()).update(cl)
    keep = ~df["_key2"].duplicated()
    df = df[keep].copy()
    tag_lists = tag_lists[keep.values]
    tag_sk = [t for t, k in zip(tag_sk, keep.values) if k]
    df["_cities"] = [sorted(c for c in merged2[k2] if c != "Other") or ["Other"] for k2 in df["_key2"]]
    req = [set(r.split("|")) - {""} for r in df["_req"]]
    n_unique = len(df)

    exp = df["experience"].map(experience_of)
    sal = df["salary"].map(salary_of)
    posted = pd.to_datetime(df["createdDate"], errors="coerce")
    posted = posted.where(posted.dt.year >= 2020)

    out = pd.DataFrame({
        "job_id": df["jobId"].astype(str).values,
        "title": df["title"].str.strip().values,
        "family": df["title"].map(family_of).values,
        "company": df["companyName"].fillna("").str.strip().values,
        "cities": ["|".join(c) for c in df["_cities"]],
        "exp_min": [e[0] for e in exp], "exp_max": [e[1] for e in exp],
        "salary_min_lpa": [s[0] for s in sal], "salary_max_lpa": [s[1] for s in sal],
        "posted": posted.dt.strftime("%Y-%m-%d").values,
        "skills": ["|".join(sorted(s)) for s in req],
    })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False, compression={"method": "gzip", "mtime": 0})

    # How much of the portal's tagging the dictionary understands.
    counts = Counter(normalise_tag(t) for tags in tag_lists for t in tags)
    total = sum(counts.values())
    mapped = sum(v for k, v in counts.items() if k in TAG_TO_SKILL)
    n_sk = pd.Series([len(s) for s in req])
    stats = {
        "raw_rows": n_raw, "unique_job_ids": n_unique_id, "postings": n_unique, "duplicates_removed": n_raw - n_unique,
        "tag_mentions": total, "tag_mentions_mapped": mapped, "tag_share_mapped": round(mapped / total, 4),
        "skills_per_posting_median": float(n_sk.median()), "skills_per_posting_max": int(n_sk.max()),
        "postings_with_3plus_skills": int((n_sk >= 3).sum()),
        "postings_topped_up_from_text": int(sum(len(a) < MIN_TAG_SKILLS for a in tag_sk)),
        "template_descriptions_ignored": int(template.sum()),
        "posted_before_2024": int((out["posted"] < "2024-01-01").sum()),
        "salary_disclosed": int(out["salary_min_lpa"].notna().sum()),
        "posted_min": out["posted"].dropna().min(), "posted_max": out["posted"].dropna().max(),
        "posted_sep_dec_2024_share": round(float(out["posted"].between("2024-09-01", "2024-12-31").mean()), 4),
        "families": out["family"].value_counts().to_dict(),
        "top_unmapped_tags": [k for k, _ in sorted(((k, v) for k, v in counts.items() if k not in TAG_TO_SKILL),
                                                   key=lambda kv: -kv[1])[:40]],
    }
    STATS.write_text(json.dumps(stats, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in stats.items() if k != "top_unmapped_tags"}, indent=1))
    print("wrote", OUT, f"{OUT.stat().st_size/1e6:.2f} MB")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
