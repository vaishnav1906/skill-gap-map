"""Skill Gap Map: which skills would get you the most interviews, measured on real Indian job postings.

    streamlit run app.py
"""
import json
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import gap_engine as ge
import ui
from skills import CATEGORY, CATEGORY_ORDER, NAMES, WEEKS, skills_from_text, with_implied

st.set_page_config(page_title="Skill Gap Map", page_icon="🪜", layout="wide")
ui.inject_css()
T = ui.tokens()
CAT_COLOUR = dict(zip(CATEGORY_ORDER, T["series"]))
ROOT = Path(__file__).resolve().parent

ROLES = ["Data Analyst", "Business Analyst", "Data Scientist", "ML / AI Engineer", "Data Engineer", "BI / Reporting",
         "Product / Marketing", "Software Engineer"]
CITIES = ["Bengaluru", "Delhi NCR", "Hyderabad", "Pune", "Mumbai", "Chennai", "Kolkata", "Ahmedabad"]
THRESHOLDS = {"Lenient · 50%": 0.5, "Typical · 60%": 0.6, "Strict · 70%": 0.7}
PRESETS = {
    "BTech (AI) + MBA marketing": ["Python", "Machine learning", "Deep learning", "NumPy", "Pandas", "Excel", "Data analysis",
                                   "Market research", "Digital marketing", "MS Office"],
    "Fresh BTech (CS / IT)": ["Python", "Java", "SQL", "Data structures & algorithms", "Git", "HTML & CSS", "MySQL"],
    "MBA (marketing)": ["Excel", "MS Office", "Market research", "Digital marketing", "SEO / SEM", "Stakeholder management",
                        "Data analysis"],
    "Commerce / finance graduate": ["Excel", "MS Office", "Financial analysis", "Data analysis"],
    "Start from scratch": [],
}
SAMPLE_RESUME = ("B.Tech in Artificial Intelligence. Projects in Python (Pandas, NumPy) and deep learning with PyTorch. "
                 "MBA Marketing (ongoing): market research, digital marketing campaigns, advanced Excel and PowerPoint. "
                 "Built a demand forecasting app and an A/B testing tool.")


# ---------------------------------------------------------------- data
@st.cache_resource(show_spinner=False)
def postings() -> pd.DataFrame:
    return ge.load_postings()


@st.cache_resource(show_spinner=False)
def market_for(role: str, cities: tuple, years, remote: bool) -> ge.Market:
    return ge.build_market(ge.filter_postings(postings(), [role], list(cities) or None, years, remote))


@st.cache_data(show_spinner=False)
def coverage_stats() -> dict:
    p = ROOT / "data" / "coverage.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def colour(skill: str) -> str:
    return CAT_COLOUR.get(CATEGORY.get(skill, ""), T["neutral"])


def pct(x: float) -> str:
    return "–" if x != x else f"{x:.0%}"


def exp_label(lo, hi) -> str:
    return "–" if lo != lo else f"{int(lo)}–{int(hi)} yrs"


SMALL = 100       # below this many postings, plans are read as a direction
MIN_PAY_N = 20    # fewest pay-disclosing postings before a median is shown


def wk_txt(w: float) -> str:
    """Weeks for display: 0.5 -> '0.5', 2.5 -> '2.5', 7.0 -> '7' (no banker's rounding to 0 or 2)."""
    return f"{round(float(w), 1):g}"


def ci_txt(k: int, n: int) -> str:
    """95% Wilson range for a share, as text: '8–18%'."""
    lo = ge.wilson_low(k, n)
    hi = 1 - ge.wilson_low(n - k, n)
    return f"{lo:.0%}–{hi:.0%} range"


def clean_weeks(edited: pd.DataFrame) -> dict:
    """Edited learning times merged over the defaults: an emptied or zero cell falls back to the default."""
    out = dict(WEEKS)
    for r in edited.itertuples():
        try:
            w = float(r.weeks)
        except (TypeError, ValueError):
            continue
        if w == w and w > 0:
            out[r.skill] = min(w, 52.0)
    return out


# ---------------------------------------------------------------- sidebar: who you are
ss = st.session_state
if "skills" not in ss:
    ss.skills = list(PRESETS["BTech (AI) + MBA marketing"])
if "weeks" not in ss:
    ss.weeks = dict(WEEKS)


def _apply_preset():
    ss.skills = list(PRESETS[ss.preset])


def _read_resume():
    found = skills_from_text(ss.resume)
    ss.found = sorted(found)
    ss.skills = sorted(set(ss.skills) | found, key=NAMES.index)


with st.sidebar:
    ui.brand()
    st.selectbox("Start from a profile", list(PRESETS), key="preset", on_change=_apply_preset,
                 help="Fills in typical skills for that background. Edit them below.")
    with st.expander("…or paste your resume", expanded=False):
        st.text_area("Resume text", key="resume", height=150, placeholder=SAMPLE_RESUME, label_visibility="collapsed")
        st.button("Find skills in my resume", on_click=_read_resume, width="stretch",
                  disabled=not ss.get("resume", "").strip())
        if ss.get("found") is not None:
            st.caption(("Found: " + ", ".join(ss.found)) if ss.found else "No known skills found. Add them below.")
        st.caption("In the online version this runs inside your browser, so your resume is not uploaded anywhere. "
                   "Matching is by keyword (a degree name counts too), so check the list below.")
    st.multiselect("Your skills", sorted(NAMES, key=str.lower), key="skills", placeholder="Add skills you can show evidence for")
    implied = sorted(with_implied(ss.skills) - set(ss.skills))
    if implied:
        st.caption("Also counted, because your skills cover them: " + ", ".join(implied) + ".")

    st.divider()
    role = st.selectbox("Target role", ROLES, index=0, key="role_pick")
    use_exp = st.toggle("Match my experience", value=True)
    years_val = st.slider("Years of experience", 0, 15, 1, disabled=not use_exp, key="years_pick",
                          help="Keeps postings whose experience range includes this number.")
    years = years_val if use_exp else None
    cities = st.multiselect("Cities", CITIES, placeholder="All of India", key="city_pick")
    remote = st.toggle("Include remote jobs", value=True, disabled=not cities,
                       help="Only matters when you pick cities; with no city filter every posting is included.")
    st.divider()
    th_label = st.segmented_control("A posting is within reach when you have", list(THRESHOLDS), default="Typical · 60%")
    theta = THRESHOLDS[th_label or "Typical · 60%"]
    st.caption("In whole skills: " + ", ".join(f"{int(ge.need([n], theta)[0])} of {n}" for n in (3, 4, 5, 6, 8)) + ".")
    by_label = st.segmented_control("Rank the next skill by", ["Jobs per skill", "Jobs per week"], default="Jobs per skill",
                                    help="Jobs per week divides by a rough learning time for each skill (editable in the plan tab).")
    by = "effort" if by_label == "Jobs per week" else "jobs"
    n_steps = st.slider("Steps in the plan", 3, 8, 6)

have = list(ss.skills)
mk = market_for(role, tuple(cities), years, remote)
city_label = ", ".join(cities) if cities else "All India"
exp_txt = f"{years} yr{'s' if years != 1 else ''} experience" if years is not None else "any experience"

# ---------------------------------------------------------------- header + guards
if mk.n == 0:
    ui.hero("Skill Gap Map", "No postings match these filters", "Widen the cities or experience, or pick another role.",
            [("Role", role), ("Where", city_label), ("Experience", exp_txt)], [], 0)
    st.stop()

p = ge.plan(mk, have, theta, n_steps, by=by, weeks=ss.weeks)
flat = ge.plan_skills(p)
start, end = p["start"], (p["steps"][-1]["reachable"] if p["steps"] else p["start"])
weeks_total = sum(s["weeks"] for s in p["steps"])
climb = [start] + [s["reachable"] for s in p["steps"]]

if start == 0:
    title = f"None of the <em>{mk.n:,}</em> postings are within reach yet"
else:
    title = f"You can reach <em>{start:,}</em> of {mk.n:,} postings today"
if p["steps"]:
    first = p["steps"][0]
    sub = (f"Learn {' + '.join(first['skills'])} first (about {wk_txt(first['weeks'])} weeks) and {first['reachable']:,} postings "
           f"come within reach. The full plan below gets you to {end:,}.")
elif start == mk.n:
    sub = "Every posting in this market is already within reach. Try a stricter bar, more experience, or another role."
else:
    sub = "No skill, pair or trio brings at least two more postings within reach here. Try the lenient bar or another role."
ui.hero(f"{role} · {city_label} · {exp_txt}", title, sub,
        [("Postings", f"{mk.n:,}"), ("Bar", f"{theta:.0%} of a posting's skills"), ("Your skills", str(len(have)))],
        climb, mk.n)

if mk.n < SMALL:
    ui.note(f"<b>Only {mk.n} postings</b> match these filters, so read the plan as a direction rather than exact counts: "
            "a few postings more or less can reorder the steps. Widen the cities or the experience range for a sturdier answer.",
            warn=True)

tab_plan, tab_market, tab_roles, tab_posts, tab_about = st.tabs(
    ["Your plan", "The market", "Which role fits", "Postings", "About the data"])

# ---------------------------------------------------------------- tab: plan
with tab_plan:
    ui.kpi_row([
        ui.kpi("Postings in this market", f"{mk.n:,}", f"{mk.thin} more name too few skills to judge"),
        ui.kpi("Within reach now", f"{start:,}", f"{start / mk.n:.0%} of the market ({ci_txt(start, mk.n)})"),
        ui.kpi("After the plan", f"{end:,}", f"{end / mk.n:.0%} of the market ({ci_txt(end, mk.n)})", accent=True),
        ui.kpi("Learning time", f"~{wk_txt(weeks_total)} wks", "rough guess, edit below"),
    ])
    if p["steps"]:
        ui.section("Your learning plan", "each step brings the most new postings within reach")
        cards = []
        for i, s in enumerate(p["steps"], 1):
            ex = mk.postings.iloc[s["unlocked"][:3]]
            eg = "; ".join(f"{escape(r.title)}{' at ' + escape(r.company) if r.company else ''}" for r in ex.itertuples())
            also = f" Also covers {', '.join(s['also'])}, which postings ask for by name." if s.get("also") else ""
            why = f"About {wk_txt(s['weeks'])} weeks.{escape(also)}" + (f" Unlocks postings such as {eg}." if eg else "")
            cards.append(dict(num=i, skills=[(k, colour(k)) for k in s["skills"]], why=why, gain=s["gain"],
                              reach=f"{s['reachable']:,} in reach"))
        ui.steps(cards)

        # Honesty check: compare the plan's first step(s) against an exhaustive search.
        chk = ge.check_plan(mk, have, theta, p) if by == "jobs" else None
        if by == "effort":
            ui.note("<b>Ranked by learning time:</b> each step is the best value per week, so quick skills come first. "
                    "That is a different goal from reaching the most postings with the fewest skills, so the exhaustive "
                    "check is shown only when ranking by jobs per skill.")
        elif chk and chk["ok"]:
            ui.note(f"<b>Checked:</b> the plan's first {chk['k']} skills reach <b>{chk['got']:,}</b> postings, and no other set "
                    f"of {chk['k']} new skills does better (every combination of the {chk['pool']} most relevant skills was "
                    "tried). Later steps are chosen one at a time and are not guaranteed to be the best possible set.")
        elif chk:
            ui.note(f"<b>Checked:</b> {escape(' + '.join(chk['best_set']))} would reach <b>{chk['best']:,}</b> postings "
                    f"with {chk['k']} skills, versus <b>{chk['got']:,}</b> for the plan's first {chk['k']} "
                    f"({chk['best'] - chk['got']:,} more). The plan picks one step at a time, so here a fixed set does better: "
                    "consider learning that set first.", warn=True)

        ui.section("Reach vs learning time", "postings within reach after each step")
        xs = np.cumsum([0] + [s["weeks"] for s in p["steps"]])
        labels = ["Today"] + [" + ".join(s["skills"]) for s in p["steps"]]
        fig = go.Figure(go.Scatter(x=xs, y=climb, mode="lines+markers", line=dict(shape="hv", color=T["brand"], width=3),
                                   marker=dict(size=9, color=[T["muted"]] + [T["brand"]] * (len(climb) - 2) + [T["gold"]]),
                                   fill="tozeroy", fillcolor=ui.rgba(T["brand"], 0.10), customdata=labels,
                                   hovertemplate="%{customdata}<br>%{y:,} postings within reach<br>after ~%{x:.0f} weeks<extra></extra>"))
        fig.update_xaxes(title="Weeks of learning (rough)", rangemode="tozero")
        fig.update_yaxes(title="Postings within reach", rangemode="tozero")
        ui.show(ui.style(fig, 300))

        plan_df = pd.DataFrame([{"step": i, "learn": " + ".join(s["skills"]), "weeks (rough)": s["weeks"],
                                 "new postings within reach": s["gain"], "postings within reach": s["reachable"]}
                                for i, s in enumerate(p["steps"], 1)])
        st.download_button("Download the plan (CSV)", plan_df.to_csv(index=False), "skill_plan.csv", "text/csv",
                           icon=":material/download:")
    elif start == mk.n:
        ui.note("You already reach every posting in this market at this bar.")
    else:
        ui.note("No single skill, pair or trio brings at least two more postings within reach in this market. "
                "Try the lenient bar, another role, or wider filters.", warn=True)

    with st.expander("Adjust the learning-time guesses"):
        st.caption("Rough weeks to job-ready basics with a technical degree. They only change the plan when ranking by "
                   "jobs per week, and the time shown on each step.")
        wk = pd.DataFrame({"skill": NAMES, "category": [CATEGORY[n] for n in NAMES],
                           "weeks": [ss.weeks.get(n, WEEKS[n]) for n in NAMES]})
        edited = st.data_editor(wk, hide_index=True, width="stretch", disabled=["skill", "category"], key="weeks_editor",
                                column_config={"weeks": st.column_config.NumberColumn(min_value=0.5, max_value=52, step=0.5)})
        new_weeks = clean_weeks(edited)
        if new_weeks != ss.weeks:
            ss.weeks = new_weeks
            st.rerun()

# ---------------------------------------------------------------- tab: market
with tab_market:
    dem = ge.skill_demand(mk, have)
    ui.section("What this market asks for", f"share of the {mk.n:,} postings that name each skill")
    ui.legend([("You have it", T["brand"]), ("You don't (yet)", T["neutral"])])
    top = dem.head(25).iloc[::-1]
    fig = go.Figure(go.Bar(x=top["share"], y=top["skill"], orientation="h",
                           marker_color=[T["brand"] if h else T["neutral"] for h in top["have"]],
                           customdata=np.stack([top["postings"], top["category"]], 1),
                           hovertemplate="%{y}: %{x:.0%} of postings (%{customdata[0]:,})<br>%{customdata[1]}<extra></extra>"))
    fig.update_xaxes(tickformat=".0%")
    ui.show(ui.style(fig, 640))

    c1, c2 = st.columns(2, gap="large")
    with c1:
        oa = ge.one_away_skills(mk, have, theta)
        n1 = len(ge.near_misses(mk, have, theta, 1))
        ui.section("One skill away", f"{n1:,} postings need just one more of their skills")
        if oa.empty:
            st.caption("No postings are exactly one skill away.")
        else:
            o = oa.head(12).iloc[::-1]
            fig = go.Figure(go.Bar(x=o["postings"], y=o["skill"], orientation="h", marker_color=[colour(s) for s in o["skill"]],
                                   hovertemplate="%{y} would complete %{x:,} of them<extra></extra>"))
            ui.show(ui.style(fig, 380))
            st.caption("Any one missing skill completes a posting, so counts overlap.")
    with c2:
        opts = [s for s in dem["skill"].head(40)]
        default = next((s for s in flat if s in opts), opts[0] if opts else None)
        pick = st.selectbox("Skills that travel with", opts, index=opts.index(default) if default in opts else 0)
        comp = ge.companions(mk, pick, 10)
        ui.section(f"Asked for alongside {pick}", "share of its postings that also name each skill")
        if not comp.empty:
            c = comp.iloc[::-1]
            fig = go.Figure(go.Bar(x=c["together"], y=c["skill"], orientation="h",
                                   marker_color=[T["brand"] if s in have else T["neutral"] for s in c["skill"]],
                                   customdata=c["lift"],
                                   hovertemplate="%{y}: %{x:.0%} of these postings (%{customdata:.1f}× its usual rate)<extra></extra>"))
            fig.update_xaxes(tickformat=".0%")
            ui.show(ui.style(fig, 380))

# ---------------------------------------------------------------- tab: roles
with tab_roles:
    rf = ge.role_fit(postings(), have, theta, ROLES, list(cities) or None, years, remote)
    ranked = rf[rf["rankable"]]
    best_role = ranked.iloc[0] if len(ranked) else None
    if best_role is not None and best_role["reachable"] > 0:
        ui.note(f"With your current skills you are closest to <b>{escape(best_role['family'])}</b>: "
                f"{best_role['reachable']:,} of {best_role['postings']:,} postings ({best_role['share']:.0%}) are within reach.")
    ui.section("Share of each role's postings within reach", f"{city_label} · {exp_txt} · bar {theta:.0%}")
    r = rf.iloc[::-1]
    fig = go.Figure(go.Bar(x=r["share"].fillna(0), y=r["family"], orientation="h",
                           marker_color=[T["neutral"] if not rk else T["brand"] if f == role else ui.rgba(T["brand"], 0.35)
                                         for f, rk in zip(r["family"], r["rankable"])],
                           text=[f"{a:,} of {b:,}" for a, b in zip(r["reachable"], r["postings"])], textposition="outside",
                           textfont=dict(color=T["text2"]), cliponaxis=False,
                           hovertemplate="%{y}: %{x:.0%} within reach<extra></extra>"))
    fig.update_xaxes(tickformat=".0%", range=[0, max(0.05, float(rf["share"].fillna(0).max()) * 1.25)])
    ui.show(ui.style(fig, 360))
    small = rf[~rf["rankable"]]["family"].tolist()
    if small:
        st.caption(f"Fewer than {ge.MIN_ROLE_POSTINGS} postings, so listed last rather than ranked: " + ", ".join(small) + ". "
                   "Roles are ranked by a cautious estimate (the 95% Wilson lower bound) so a small lucky share does not win.")
    st.caption("Software Engineer and Product / Marketing postings here come from a data-science search on the portal, "
               "so they are the data-flavoured end of those roles.")

# ---------------------------------------------------------------- tab: postings
with tab_posts:
    nd = ge.need(mk.sizes, theta)
    got = ge.matched(mk, have)
    after = ge.matched(mk, have + flat)
    view = st.segmented_control("Show", ["Within reach now", "One skill away", "Unlocked by the plan", "All"],
                                default="Unlocked by the plan")
    view = view or "Unlocked by the plan"
    mask = {"Within reach now": got >= nd, "One skill away": nd - got == 1,
            "Unlocked by the plan": (got < nd) & (after >= nd), "All": np.ones(mk.n, bool)}[view]
    pay_all = ge.salary_view(mk, np.ones(mk.n, bool))
    if years is None:
        # Without an experience filter, "after the plan" mostly adds more senior postings, so a pay comparison would
        # show seniority rather than skills. Show the market's pay only.
        pay_cards = [ui.kpi("Pay in this market", "–" if pay_all["n"] < MIN_PAY_N else f"₹{pay_all['median']:.1f} L",
                            f"median, {pay_all['n']} disclose pay"),
                     ui.kpi("Pay comparison", "–", "turn on Match my experience to compare like with like")]
    else:
        sal_now, sal_new = ge.salary_view(mk, got >= nd), ge.salary_view(mk, (got < nd) & (after >= nd))
        pay_cards = [ui.kpi("Pay within reach now", "–" if sal_now["n"] < MIN_PAY_N else f"₹{sal_now['median']:.1f} L",
                            f"median, {sal_now['n']} disclose pay"),
                     ui.kpi("Pay of postings the plan adds", "–" if sal_new["n"] < MIN_PAY_N else f"₹{sal_new['median']:.1f} L",
                            f"median, {sal_new['n']} disclose pay", accent=True)]
    ui.kpi_row([ui.kpi("Postings shown", f"{int(mask.sum()):,}", view.lower()), *pay_cards,
                ui.kpi("Disclose pay", f"{pay_all['n']:,}", f"of the {mk.n:,} postings here")])
    rows = mk.postings[mask].copy()
    rows["you have"] = [f"{a} of {b}" for a, b in zip(got[mask], mk.sizes[mask])]
    have_all = with_implied(have)
    rows["missing"] = rows["skills"].map(lambda sk: ", ".join(s for s in sk if s not in have_all))
    rows["where"] = rows["cities"].map(lambda c: ", ".join(c))
    rows["experience"] = [exp_label(a, b) for a, b in zip(rows["exp_min"], rows["exp_max"])]
    rows["pay (₹ L/yr)"] = [("" if a != a else f"{a:g}–{b:g}") for a, b in zip(rows["salary_min_lpa"], rows["salary_max_lpa"])]
    st.dataframe(rows[["title", "company", "where", "experience", "you have", "missing", "pay (₹ L/yr)", "posted"]],
                 hide_index=True, width="stretch", height=460)
    st.caption(f"Pay is shown only where the employer published it (about 1 posting in 11), and a median needs at least "
               f"{MIN_PAY_N} of them, so it leans towards employers who disclose. Most postings are from late 2024 (some "
               "older) and are likely closed; use them to see what is asked for.")

# ---------------------------------------------------------------- tab: about
with tab_about:
    cs = coverage_stats()
    c1, c2 = st.columns(2, gap="large")
    with c1:
        ui.section("Where the postings come from")
        st.markdown(
            f"- **{cs.get('postings', len(postings())):,} job postings** from Naukri, an Indian job portal, collected from "
            "searches for data-science jobs and published as the *Naukri jobs dataset* by muhammetakkurt on "
            "[Hugging Face](https://huggingface.co/datasets/muhammetakkurt/naukri-jobs-dataset) (CC BY-NC 4.0).\n"
            f"- **{cs.get('posted_sep_dec_2024_share', 0):.0%}** were posted between September and December 2024; "
            f"{cs.get('posted_before_2024', 0):,} are older (2020–2023). It is a snapshot, not the whole Indian job market.\n"
            f"- **{cs.get('duplicates_removed', 0):,} repeat ads were removed**: repeated job IDs, the same ad posted once per "
            "city (same company, title and description), and near-identical requisitions (same company, title, skills and "
            "experience). Their cities were merged.\n"
            f"- A posting's requirements are the portal's *key skills* tags, mapped onto {len(NAMES)} skills. When the tags "
            f"name fewer than 3 skills ({cs.get('postings_topped_up_from_text', 0):,} postings), skills from the description "
            "are added in the order they appear, up to 8, unless the description is boilerplate shared by several companies "
            f"({cs.get('template_descriptions_ignored', 0):,} postings). **{cs.get('tag_share_mapped', 0):.0%}** of tag "
            "mentions map to a skill; the rest are mostly generic "
            "words such as *analytical*, *data* or *coding*, role names, and industries.\n"
            f"- Only **{cs.get('salary_disclosed', 0):,}** postings publish pay.")
    with c2:
        ui.section("How the plan works")
        st.markdown(
            "- A posting is **within reach** when you hold at least the chosen share of the skills it names. "
            "That is a screening assumption, not a promise of an interview.\n"
            f"- Postings naming fewer than {ge.MIN_SKILLS} recognised skills are left out: one or two tags cannot describe a job.\n"
            "- Each step adds the skill, or the pair or trio of skills, that brings the most new postings within reach per "
            "skill (or per week). Groups matter because many postings need two or three things you lack at once.\n"
            "- When ranking by jobs per skill, the plan's first whole steps (up to four skills) are checked against an "
            "exhaustive search of the most relevant skills (30 for up to three skills, 22 for four), and the plan tab "
            "says what it found. Later steps are chosen one at a time: fast and usually close, but not guaranteed to be "
            "the best possible set.\n"
            "- Specific skills count for the broad tags they cover: *Machine learning* meets an *Artificial intelligence* "
            "tag, *Power BI* meets *Data visualization*, *MySQL* meets *SQL*.\n"
            "- A step must bring at least two postings and one per skill; otherwise the plan stops rather than pad.\n"
            "- Learning times are rough guesses and editable.")
    ui.section("Limits worth knowing")
    st.markdown(
        "- Tags are capped at eight per posting, so some requirements may be missing.\n"
        "- Postings that name fewer skills are easier to reach; the table below shows how much.\n"
        "- Keyword matching cannot judge depth: *Python* on a resume counts the same whether it is a course or five years.\n"
        "- Roles are assigned from job titles with simple rules; *Analyst* alone is too vague and is left out.\n"
        "- The data is from 2024. Demand moves, especially for generative AI.")
    bands = pd.cut(pd.Series(mk.sizes), [2, 4, 6, 8, 100], labels=["3–4 skills", "5–6 skills", "7–8 skills", "9 or more"])
    within = pd.Series(ge.reachable(mk, have, theta))
    by_size = (pd.DataFrame({"posting names": bands, "within": within}).groupby("posting names", observed=True)["within"]
               .agg(postings="size", within_reach="sum").reset_index())
    by_size["share within reach"] = (by_size["within_reach"] / by_size["postings"]).map(lambda x: f"{x:.0%}")
    ui.section("Within reach, by how many skills a posting names", "your current profile and filters")
    st.dataframe(by_size.rename(columns={"within_reach": "within reach"}), hide_index=True)
