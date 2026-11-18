"""Turning raw postings into the app's data file, and the shipped file itself."""
import json
import math
from pathlib import Path

import pytest

import gap_engine as ge
from prepare_data import FAMILY_NAMES, cities_of, experience_of, family_of, salary_of
from skills import NAMES

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("title, family", [
    ("Data Scientist - Phd only", "Data Scientist"),
    ("Senior Data Scientist (GenAI)", "Data Scientist"),
    ("Machine Learning Engineer", "ML / AI Engineer"),
    ("GenAI Engineer", "ML / AI Engineer"),
    ("Business Analyst - Payments", "Business Analyst"),
    ("Power BI Developer", "BI / Reporting"),
    ("MIS Executive", "BI / Reporting"),
    ("Data Analyst", "Data Analyst"),
    ("Analytics Consultant", "Data Analyst"),
    ("Product Analyst", "Product / Marketing"),
    ("Digital Marketing Executive", "Product / Marketing"),
    ("Azure Data Engineer", "Data Engineer"),
    ("Big Data Developer", "Data Engineer"),
    ("Full Stack Developer", "Software Engineer"),
    ("Analyst", "Other"),
    ("Senior Manager", "Other"),
    ("Email Marketing Specialist", "Product / Marketing"),
    # review findings: a title that names the role wins over tool keywords; non-software engineers are not SWE
    ("Data Analyst - SQL, Tableau", "Data Analyst"),
    ("Senior Data Engineer - Analytics", "Data Engineer"),
    ("Data Engineer - GenAI", "Data Engineer"),
    ("Sales Engineer", "Other"),
    ("Gis Engineer", "Other"),
    ("Forensic Scientist", "Other"),
    ("Food Scientist", "Other"),
    ("Research Scientist - NLP", "Data Scientist"),
    ("Data Quality Engineer", "Data Engineer"),
    ("QA Engineer", "Other"),
])
def test_family_of(title, family):
    assert family_of(title) == family
    assert family in FAMILY_NAMES


@pytest.mark.parametrize("loc, cities", [
    ("Bengaluru", ["Bengaluru"]),
    ("Bangalore/Bengaluru", ["Bengaluru"]),
    ("Hybrid - Delhi NCR, Hyderabad, Gurgaon", ["Delhi NCR", "Hyderabad"]),
    ("Mumbai (All Areas)", ["Mumbai"]),
    ("Remote", ["Remote"]),
    ("Kochi", ["Other"]),
    ("Bangalore Rural", ["Bengaluru"]),
    ("Mumbai Suburbs", ["Mumbai"]),
    ("India", ["Pan-India"]),
    ("", ["Other"]),
    (None, ["Other"]),
])
def test_cities_of(loc, cities):
    assert cities_of(loc) == sorted(cities)


def test_experience_and_salary_parsing():
    assert experience_of("3-8 Yrs") == (3, 8)
    assert experience_of("8-3 Yrs") == (3, 8)
    assert experience_of("0 Yrs") == (0, 0)          # freshers-only postings must not be dropped
    assert experience_of("8 Yrs") == (8, 8)
    assert all(math.isnan(x) for x in experience_of("Not Mentioned"))
    assert salary_of("12-15 Lacs PA") == (12.0, 15.0)
    assert salary_of("1,00-1,50 Lacs PA") == (100.0, 150.0)
    assert salary_of("80 Lacs-1.5 Cr PA") == (80.0, 150.0)
    assert salary_of("50,000-3 Lacs PA") == (0.5, 3.0)
    assert salary_of("6 Lacs PA") == (6.0, 6.0)
    assert salary_of("1-1.5 Cr PA") == (100.0, 150.0)
    assert salary_of("50,000-60,000 PA") == (0.5, 0.6)              # plain rupees a year
    assert salary_of("45-55 Lacs PA (Including Variable: 8.0%)") == (45.0, 55.0)
    assert salary_of("15,000/month") == (1.8, 1.8)
    for bad in ["Not disclosed", "Unpaid", "15-12 Lacs PA", None]:
        assert all(math.isnan(x) for x in salary_of(bad)), bad


def test_requirements_come_from_tags_unless_too_few():
    from prepare_data import requirements
    assert requirements({"SQL", "Excel", "Power BI"}, ["Python", "Tableau"]) == {"SQL", "Excel", "Power BI"}
    assert requirements({"SQL"}, ["Python", "Tableau"]) == {"SQL", "Python", "Tableau"}
    # review finding: a long description used to add up to 30 skills; now it tops up in order and stops at 8
    many = [f"S{i}" for i in range(20)]
    assert requirements({"SQL"}, many) == {"SQL", *many[:7]}
    # review finding: boilerplate shared by many companies is not a requirement list
    assert requirements({"SQL"}, ["Python", "Tableau"], template=True) == {"SQL"}


def test_no_repeat_ads_in_shipped_data():
    df = ge.load_postings()
    assert not df.duplicated(["company", "title", "skills", "exp_min", "exp_max"]).any()
    assert df["skills"].map(len).max() <= 8


def test_shipped_data_is_consistent():
    df = ge.load_postings()
    stats = json.loads((ROOT / "data" / "coverage.json").read_text(encoding="utf-8"))
    assert len(df) == stats["postings"] > 10_000
    assert df["job_id"].is_unique
    assert set(df["family"]) <= set(FAMILY_NAMES)
    assert {s for sk in df["skills"] for s in sk} <= set(NAMES)
    ok = df["exp_min"].notna()
    assert (df.loc[ok, "exp_min"] <= df.loc[ok, "exp_max"]).all()
    pay = df["salary_min_lpa"].notna()
    assert (df.loc[pay, "salary_min_lpa"] <= df.loc[pay, "salary_max_lpa"]).all()
    assert pay.sum() == stats["salary_disclosed"]
    assert (df["skills"].map(len) >= ge.MIN_SKILLS).sum() == stats["postings_with_3plus_skills"]


def test_data_file_is_small_enough_for_the_browser():
    assert (ROOT / "data" / "postings.csv.gz").stat().st_size < 1_500_000
