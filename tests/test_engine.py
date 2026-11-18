"""The plan engine, checked on small markets worked by hand and against brute force."""
import random
from itertools import combinations

import numpy as np
import pandas as pd
import pytest

import gap_engine as ge


def frame(rows, family="Data Analyst", cities=("Pune",), exp=(0, 3), salary=(np.nan, np.nan)):
    return pd.DataFrame({
        "job_id": [str(i) for i in range(len(rows))], "title": [f"Job {i}" for i in range(len(rows))],
        "family": family, "company": "Acme", "cities": [tuple(cities)] * len(rows),
        "exp_min": exp[0], "exp_max": exp[1], "salary_min_lpa": salary[0], "salary_max_lpa": salary[1],
        "posted": "2024-12-01", "skills": [tuple(sorted(r)) for r in rows],
    })


def brute_best(market, have, theta, k):
    cand = [s for s in market.vocab if s not in have]
    return max(int(ge.reachable(market, list(have) + list(c), theta).sum()) for c in combinations(cand, k))


# ---------------------------------------------------------------- basics
def test_need_rounds_up_without_float_noise():
    assert ge.need([5], 0.6).tolist() == [3]          # 0.6 * 5 = 3.0000000000000004 in floats
    assert ge.need([3, 4, 7, 10], 0.6).tolist() == [2, 3, 5, 6]
    assert ge.need([4], 0.5).tolist() == [2]
    assert ge.need([3], 0.7).tolist() == [3]          # 2.1 -> 3


def test_thin_postings_are_left_out_and_counted():
    m = ge.build_market(frame([("A", "B", "C"), ("A", "B"), ("A",), ("A", "B", "C", "D")]))
    assert m.n == 2 and m.thin == 2


def test_reachable_worked_by_hand():
    m = ge.build_market(frame([("A", "B", "C"), ("A", "B", "C", "D", "E"), ("C", "D", "E")]))
    # theta 0.6: needs 2, 3, 2.  Holding A, B: 2/3 ok, 2/5 no, 0/3 no
    assert ge.reachable(m, ["A", "B"], 0.6).tolist() == [True, False, False]
    assert ge.matched(m, ["A", "B", "Z"]).tolist() == [2, 2, 0]      # unknown skills are ignored
    assert np.allclose(ge.coverage(m, ["C"]), [1 / 3, 1 / 5, 1 / 3])


def test_filter_by_family_city_remote_and_experience():
    a = frame([("A", "B", "C")], cities=("Pune",), exp=(0, 2))
    b = frame([("A", "B", "C")], cities=("Remote",), exp=(3, 6))
    c = frame([("A", "B", "C")], family="Data Scientist", cities=("Mumbai", "Pune"), exp=(1, 4))
    df = pd.concat([a, b, c], ignore_index=True)
    assert len(ge.filter_postings(df, ["Data Analyst"])) == 2
    assert len(ge.filter_postings(df, None, ["Pune"])) == 3                       # remote included by default
    assert len(ge.filter_postings(df, None, ["Pune"], include_remote=False)) == 2
    assert len(ge.filter_postings(df, None, None, years=2)) == 2                  # 0-2 and 1-4
    assert len(ge.filter_postings(df, None, None, years=5)) == 1
    assert len(ge.filter_postings(df, ["Data Scientist"], ["Mumbai"], 1)) == 1
    pan = frame([("A", "B", "C")], cities=("Pan-India",))
    assert len(ge.filter_postings(pd.concat([df, pan], ignore_index=True), None, ["Kolkata"], include_remote=False)) == 1


# ---------------------------------------------------------------- the plan
def test_plan_finds_the_obvious_next_skill():
    rows = [("SQL", "Excel", "Power BI")] * 10 + [("Python", "Spark", "AWS")] * 3
    m = ge.build_market(frame(rows))
    p = ge.plan(m, ["Excel"], 0.6, steps=2)
    assert p["start"] == 0
    assert p["steps"][0]["skills"] in (("SQL",), ("Power BI",))
    assert p["steps"][0]["gain"] == 10 and p["steps"][0]["reachable"] == 10


def test_plan_learns_a_pair_when_no_single_skill_helps():
    # every posting needs two things you lack, so any single skill unlocks nothing
    rows = [("Spark", "Databricks", "SQL", "Python", "Airflow")] * 8 + [("Tableau", "Excel", "SQL")] * 2
    m = ge.build_market(frame(rows))
    p = ge.plan(m, ["SQL"], 0.6, steps=3)
    # a single skill unlocks at most 2 (the Tableau/Excel postings); a pair from the big group unlocks 8, 4 per skill
    first = p["steps"][0]
    assert len(first["skills"]) == 2 and first["gain"] == 8
    assert set(first["skills"]) <= {"Spark", "Databricks", "Python", "Airflow"}
    assert p["steps"][-1]["reachable"] == 10


def test_plan_is_deterministic_and_never_relearns():
    rng = random.Random(1)
    vocab = [f"S{i}" for i in range(12)]
    rows = [tuple(rng.sample(vocab, rng.randint(3, 6))) for _ in range(150)]
    m = ge.build_market(frame(rows))
    p1, p2 = ge.plan(m, ["S0"], 0.6, 6), ge.plan(m, ["S0"], 0.6, 6)
    assert [s["skills"] for s in p1["steps"]] == [s["skills"] for s in p2["steps"]]
    flat = ge.plan_skills(p1)
    assert len(flat) == len(set(flat)) and "S0" not in flat
    reach = [p1["start"]] + [s["reachable"] for s in p1["steps"]]
    assert all(b > a for a, b in zip(reach, reach[1:]))                          # every step adds postings
    assert all(s["gain"] == b - a for s, a, b in zip(p1["steps"], reach, reach[1:]))


def test_unlocked_rows_match_the_gain():
    rng = random.Random(2)
    vocab = [f"S{i}" for i in range(10)]
    m = ge.build_market(frame([tuple(rng.sample(vocab, rng.randint(3, 5))) for _ in range(120)]))
    p = ge.plan(m, [], 0.6, 4)
    have = []
    for s in p["steps"]:
        before = ge.reachable(m, have, 0.6)
        have += list(s["skills"])
        after = ge.reachable(m, have, 0.6)
        assert sorted(np.flatnonzero(after & ~before)) == sorted(s["unlocked"])


@pytest.mark.parametrize("seed", range(25))
def test_plan_matches_brute_force_at_step_boundaries(seed):
    """On random small markets, after the plan's first step(s) (up to 3 skills), no other set of the same size does better."""
    rng = random.Random(seed)
    vocab = [f"S{i}" for i in range(rng.randint(8, 13))]
    rows = [tuple(rng.sample(vocab, rng.randint(3, 6))) for _ in range(rng.randint(40, 160))]
    m = ge.build_market(frame(rows))
    have = rng.sample(vocab, rng.randint(0, 3))
    theta = rng.choice([0.5, 0.6, 0.7])
    p = ge.plan(m, have, theta, 4, pair_pool=len(vocab))
    k = 0
    for s in p["steps"]:
        k += len(s["skills"])
        if k > 3:
            break
        assert s["reachable"] == brute_best(m, have, theta, k), (seed, k)


@pytest.mark.parametrize("seed", range(10))
def test_best_k_skills_equals_brute_force_with_a_full_pool(seed):
    rng = random.Random(100 + seed)
    vocab = [f"S{i}" for i in range(10)]
    m = ge.build_market(frame([tuple(rng.sample(vocab, rng.randint(3, 6))) for _ in range(rng.randint(30, 120))]))
    have = rng.sample(vocab, 2)
    for k in (1, 2, 3):
        got, skills = ge.best_k_skills(m, have, 0.6, k, pool_size=len(vocab))
        assert got == brute_best(m, have, 0.6, k)
        if skills:
            assert int(ge.reachable(m, have + list(skills), 0.6).sum()) == got


def test_effort_ranking_prefers_cheap_skills_with_similar_payoff():
    rows = [("SQL", "Excel", "Power BI")] * 6 + [("SQL", "Excel", "Machine learning")] * 7
    m = ge.build_market(frame(rows))
    by_jobs = ge.plan(m, ["SQL"], 0.6, 1, by="jobs")
    by_effort = ge.plan(m, ["SQL"], 0.6, 1, by="effort", weeks={"Machine learning": 12, "Power BI": 3, "Excel": 2})
    assert by_jobs["steps"][0]["skills"] == ("Excel",)                    # Excel completes all 13
    assert by_effort["steps"][0]["skills"] == ("Excel",)
    by_effort2 = ge.plan(m, ["SQL", "Excel"], 0.7, 1, by="effort", weeks={"Machine learning": 12, "Power BI": 3})
    assert by_effort2["steps"][0]["skills"] == ("Power BI",)              # 6 jobs in 3 weeks beats 7 in 12


def test_plan_stops_when_nothing_helps_and_handles_edges():
    m = ge.build_market(frame([("A", "B", "C")] * 3))
    full = ge.plan(m, ["A", "B", "C"], 0.6, 5)
    assert full["start"] == 3 and full["steps"] == []
    empty = ge.build_market(frame([("A",)]))
    assert empty.n == 0
    p = ge.plan(empty, [], 0.6, 3)
    assert p["steps"] == [] and p["start"] == 0
    assert ge.best_k_skills(empty, [], 0.6, 2) == (0, ())


# ---------------------------------------------------------------- views
def test_demand_companions_and_near_misses():
    rows = [("SQL", "Excel", "Power BI")] * 6 + [("SQL", "Python", "Spark")] * 4
    m = ge.build_market(frame(rows))
    d = ge.skill_demand(m, ["SQL"])
    assert d.iloc[0]["skill"] == "SQL" and d.iloc[0]["share"] == 1.0 and bool(d.iloc[0]["have"])
    c = ge.companions(m, "Excel")
    row = c.set_index("skill").loc["Power BI"]
    assert row["together"] == 1.0 and row["lift"] == pytest.approx(1 / 0.6)
    nm = ge.near_misses(m, ["SQL"], 0.6, 1)
    assert len(nm) == 10 and set(nm["missing"].iloc[0]) <= {"Excel", "Power BI", "Python", "Spark"}
    oa = ge.one_away_skills(m, ["SQL"], 0.6)
    assert dict(zip(oa["skill"], oa["postings"]))["Excel"] == 6
    assert ge.companions(m, "Nope").empty


def test_wilson_lower_bound_known_values_and_ranking():
    assert ge.wilson_low(5, 10) == pytest.approx(0.2366, abs=1e-4)      # textbook 95% interval 0.237-0.763
    assert ge.wilson_low(0, 10) == 0.0                                    # clamped: float noise showed as "-0%"
    assert all(ge.wilson_low(0, n) >= 0 for n in range(1, 4000))
    assert ge.wilson_low(10, 10) == pytest.approx(0.7225, abs=1e-4)
    assert ge.wilson_low(25, 202) > ge.wilson_low(2, 9)                    # bigger evidence wins over a lucky small share
    assert np.isnan(ge.wilson_low(0, 0))


def test_role_fit_and_salary_view():
    da = frame([("SQL", "Excel", "Power BI")] * 4, salary=(6.0, 8.0))
    ds = frame([("Python", "Machine learning", "Statistics")] * 4, family="Data Scientist")
    df = pd.concat([da, ds], ignore_index=True)
    rf = ge.role_fit(df, ["SQL", "Excel"], 0.6, ["Data Analyst", "Data Scientist", "Data Engineer"])
    assert rf.iloc[0]["family"] == "Data Analyst" and rf.iloc[0]["share"] == 1.0
    assert rf.set_index("family").loc["Data Engineer", "postings"] == 0
    m = ge.build_market(da)
    sv = ge.salary_view(m, np.ones(m.n, bool))
    assert sv == {"n": 4, "median": 7.0}
    assert ge.salary_view(m, np.zeros(m.n, bool))["n"] == 0


def test_check_plan_covers_whole_steps_up_to_four_skills():
    rng = random.Random(9)
    vocab = [f"S{i}" for i in range(12)]
    m = ge.build_market(frame([tuple(rng.sample(vocab, rng.randint(3, 6))) for _ in range(150)]))
    p = ge.plan(m, [], 0.6, 5)
    chk = ge.check_plan(m, [], 0.6, p)
    sizes = [len(s["skills"]) for s in p["steps"]]
    k = 0
    for n in sizes:
        if k + n > 4:
            break
        k += n
    if k < 2:
        assert chk is None
    else:
        assert chk["k"] == k and chk["got"] == p["steps"][[sum(sizes[:i + 1]) for i in range(len(sizes))].index(k)]["reachable"]
        assert chk["ok"] == (chk["got"] >= chk["best"])
    single = {"start": 0, "steps": [{"skills": ("S1",)}], "total": m.n}
    assert ge.check_plan(m, [], 0.6, single) is None          # a lone single skill is best by construction


def test_tiny_roles_are_listed_last_not_ranked():
    big = frame([("SQL", "Excel", "Power BI")] * 20 + [("Python", "Spark", "AWS")] * 20)
    tiny = frame([("SQL", "Excel", "Tableau")] * 3, family="Product / Marketing")
    rf = ge.role_fit(pd.concat([big, tiny], ignore_index=True), ["SQL", "Excel"], 0.6, ["Data Analyst", "Product / Marketing"])
    assert list(rf["family"]) == ["Data Analyst", "Product / Marketing"]   # 100% of 3 does not outrank 50% of 40
    assert list(rf["rankable"]) == [True, False]


def test_specific_skills_cover_broad_tags():
    """Review finding: a BTech-AI profile with Machine learning was told to learn "Artificial intelligence"."""
    m = ge.build_market(frame([("Artificial intelligence", "NLP", "Python")] * 5 + [("SQL", "Data visualization", "Excel")] * 5))
    assert ge.matched(m, ["Machine learning"]).tolist()[:1] == [1]       # ML counts for the AI tag
    p = ge.plan(m, ["Machine learning", "Python"], 0.6, 3)
    assert "Artificial intelligence" not in ge.plan_skills(p)
    assert int(ge.reachable(m, ["Machine learning", "Python"], 0.6).sum()) == 5
    nm = ge.near_misses(m, ["Machine learning"], 0.6, 1)
    assert all("Artificial intelligence" not in miss for miss in nm["missing"])


def test_a_step_reports_what_it_also_covers_and_gains_are_exact():
    m = ge.build_market(frame([("SQL", "MySQL", "Excel")] * 6 + [("SQL", "Excel", "Tableau")] * 2))
    p = ge.plan(m, ["Excel"], 0.7, 2)          # needs all 3: only MySQL (which brings SQL with it) completes 6 at once
    first = p["steps"][0]
    assert first["skills"] == ("MySQL",) and first["also"] == ("SQL",) and first["gain"] == 6
    assert first["reachable"] - p["start"] == first["gain"]


def test_plan_stops_instead_of_padding_with_one_posting_steps():
    m = ge.build_market(frame([("A", "B", "C")] * 6 + [("D", "E", "F")]))
    p = ge.plan(m, ["A"], 0.6, 5)
    assert all(s["gain"] >= max(ge.MIN_STEP_GAIN, len(s["skills"])) for s in p["steps"])
    assert p["steps"][-1]["reachable"] == 6                                # the lone D/E/F posting is not chased
