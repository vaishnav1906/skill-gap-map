"""Skill Gap Map engine: which postings are within reach, and which skills to learn next.

A posting is *within reach* when you hold at least `theta` of the skills it asks for (default 60%). That is a
screening assumption, not a hiring prediction: it says your profile would plausibly pass a skills filter.

Your skills count with the broad skills they imply (Machine learning covers an "Artificial intelligence" tag).

The learning plan is greedy: at each step it adds the skill (or the pair or trio) that brings the most
postings within reach per skill (or per week of learning). Because a posting only counts once you cross the
threshold, gains are not additive, so greedy is not guaranteed optimal; `best_k_skills` checks it against an
exhaustive search.
"""
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

from skills import CATEGORY, WEEKS, with_implied

DATA = Path(__file__).resolve().parent / "data" / "postings.csv.gz"
MIN_SKILLS = 3  # postings that name fewer recognised skills are too thin to judge fit
MIN_ROLE_POSTINGS = 30  # roles with fewer postings are listed last in role fit, not ranked
MIN_STEP_GAIN = 2  # a step must bring at least this many postings (and one per skill), or the plan stops there


def load_postings(path=DATA) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"job_id": str, "company": str, "posted": str})
    df["skills"] = df["skills"].fillna("").map(lambda s: tuple(x for x in s.split("|") if x))
    df["cities"] = df["cities"].fillna("Other").map(lambda s: tuple(s.split("|")))
    df["company"] = df["company"].fillna("")
    return df


def filter_postings(df: pd.DataFrame, families=None, cities=None, years=None, include_remote=True) -> pd.DataFrame:
    """Keep postings in the chosen role families and cities whose experience range includes `years`."""
    m = pd.Series(True, index=df.index)
    if families:
        m &= df["family"].isin(list(families))
    if cities:
        # "Pan-India" postings hire anywhere, so they count for every city
        want = set(cities) | {"Pan-India"} | ({"Remote"} if include_remote else set())
        m &= df["cities"].map(lambda cs: bool(want.intersection(cs)))
    if years is not None:
        m &= (df["exp_min"] <= years) & (df["exp_max"] >= years)
    return df[m]


@dataclass
class Market:
    X: np.ndarray            # postings x skills, 0/1 (int32 so sums do not overflow)
    vocab: list              # skill name per column
    postings: pd.DataFrame   # the postings behind the rows, same order
    thin: int                # postings left out because they name fewer than MIN_SKILLS recognised skills

    @property
    def n(self) -> int:
        return len(self.postings)

    @property
    def sizes(self) -> np.ndarray:
        return self.X.sum(1)

    def col(self, skills) -> np.ndarray:
        """Columns for these skills and everything they imply."""
        return self.raw_col(with_implied(skills))

    def raw_col(self, skills) -> np.ndarray:
        idx = {s: i for i, s in enumerate(self.vocab)}
        mask = np.zeros(len(self.vocab), bool)
        for s in skills:
            if s in idx:
                mask[idx[s]] = True
        return mask

    def contributions(self, have: set, cand) -> np.ndarray:
        """postings x candidates: how many of each posting's skills learning that candidate adds (itself plus what it
        implies that you don't already hold)."""
        return np.stack([self.X[:, self.raw_col(with_implied({self.vocab[j]}) - have)].sum(1) for j in cand], 1)             if len(cand) else np.zeros((self.n, 0), np.int32)


def build_market(df: pd.DataFrame, min_skills: int = MIN_SKILLS) -> Market:
    sizes = df["skills"].map(len)
    keep = df[sizes >= min_skills].reset_index(drop=True)
    vocab = sorted({s for sk in keep["skills"] for s in sk})
    idx = {s: i for i, s in enumerate(vocab)}
    X = np.zeros((len(keep), len(vocab)), np.int32)
    for r, sk in enumerate(keep["skills"]):
        X[r, [idx[s] for s in sk]] = 1
    return Market(X, vocab, keep, int((sizes < min_skills).sum()))


def need(sizes, theta: float) -> np.ndarray:
    """Skills you must hold to reach a posting: ceil(theta x size). The epsilon keeps 0.6 x 5 = 3, not 4."""
    return np.ceil(theta * np.asarray(sizes, float) - 1e-9).astype(np.int32)


def matched(market: Market, have) -> np.ndarray:
    """How many of each posting's skills you hold."""
    return market.X[:, market.col(have)].sum(1)


def reachable(market: Market, have, theta: float) -> np.ndarray:
    return matched(market, have) >= need(market.sizes, theta)


def coverage(market: Market, have) -> np.ndarray:
    s = market.sizes
    return matched(market, have) / np.maximum(s, 1)


# ---------------------------------------------------------------- the plan
def plan(market: Market, have, theta: float = 0.6, steps: int = 6, by: str = "jobs", weeks: dict | None = None,
         pair_pool: int = 25, max_group: int = 3) -> dict:
    """Greedy learning plan.

    by="jobs": most postings unlocked per skill.  by="effort": most postings unlocked per week of learning.
    A step may be a group of up to `max_group` skills when the group beats every single skill per unit of cost:
    many postings need two or three missing skills at once, so no single skill unlocks them.
    """
    weeks = {**WEEKS, **(weeks or {})}
    have = with_implied(have)
    X, nd = market.X, need(market.sizes, theta)
    cnt = matched(market, have)
    start = int((cnt >= nd).sum())
    demand = X.sum(0)
    out = []
    for _ in range(steps):
        reach = cnt >= nd
        cand = np.array([j for j, s in enumerate(market.vocab) if s not in have], int)
        if cand.size == 0:
            break
        C = market.contributions(have, cand)
        open_ = ~reach
        gain = (open_[:, None] & (cnt[:, None] + C >= nd[:, None])).sum(0)
        cost = np.array([max(weeks.get(market.vocab[j], 4), 0.5) if by == "effort" else 1.0 for j in cand])
        score = gain / cost
        # deterministic order: score, then gain, then overall demand, then name
        order = sorted(range(len(cand)), key=lambda i: (-score[i], -gain[i], -demand[cand[i]], market.vocab[cand[i]]))
        bi = order[0]
        best = dict(skills=(market.vocab[cand[bi]],), gain=int(gain[bi]), cost=float(cost[bi]), score=float(score[bi]))

        gap = nd - cnt
        for size in range(2, max_group + 1):
            rows = open_ & (gap <= size)
            if not rows.any():
                continue
            rel = C[rows].sum(0)
            pool = np.array([i for i in np.argsort(-rel, kind="stable")[:pair_pool] if rel[i] > 0], int)
            if pool.size < size:
                continue
            combos = np.array(list(combinations(range(pool.size), size)), int)
            P = C[:, pool]
            for s0 in range(0, len(combos), 500):
                ch = combos[s0:s0 + 500]
                g = (open_[:, None] & ((cnt[:, None] + P[:, ch].sum(2)) >= nd[:, None])).sum(0)
                c = cost[pool][ch].sum(1)
                sc = g / c
                i = int(np.argmax(sc))
                if sc[i] > best["score"] + 1e-12:
                    group = tuple(sorted(market.vocab[cand[pool[j]]] for j in ch[i]))
                    best = dict(skills=group, gain=int(g[i]), cost=float(c[i]), score=float(sc[i]))
        # Exact effect (group estimates can double-count a skill implied by two members), then stop when a step
        # brings fewer than one posting per skill: in small markets that is noise, not advice.
        new_have = with_implied(have | set(best["skills"]))
        new_cnt = matched(market, new_have)
        newly = open_ & (new_cnt >= nd)
        gain_exact = int(newly.sum())
        if gain_exact < max(MIN_STEP_GAIN, len(best["skills"])):
            break
        also = tuple(sorted(new_have - have - set(best["skills"])))
        cnt, have = new_cnt, new_have
        out.append(dict(skills=best["skills"], also=also, gain=gain_exact, reachable=int((cnt >= nd).sum()),
                        weeks=float(sum(weeks.get(s, 4) for s in best["skills"])), unlocked=np.flatnonzero(newly)))
    return dict(start=start, steps=out, total=market.n)


def plan_skills(p: dict) -> list:
    return [s for st in p["steps"] for s in st["skills"]]


def best_k_skills(market: Market, have, theta: float, k: int, pool_size: int = 30) -> tuple[int, tuple]:
    """Exhaustive search for the k new skills that bring the most postings within reach.

    To stay fast, candidates are the `pool_size` skills that appear most often in postings you could reach with
    k more skills. Returns (postings within reach afterwards, skills).
    """
    have = with_implied(have)
    X, nd = market.X, need(market.sizes, theta)
    cnt = matched(market, have)
    gap = nd - cnt
    near = (gap > 0) & (gap <= k)
    cand = np.array([j for j, s in enumerate(market.vocab) if s not in have], int)
    if cand.size == 0 or not near.any():
        return int((cnt >= nd).sum()), ()
    D = market.contributions(have, cand)
    rel = D[near].sum(0)
    order = np.argsort(-rel, kind="stable")[:pool_size]
    pool, P = cand[order], D[:, order]
    k = min(k, len(pool))
    combos = np.array(list(combinations(range(len(pool)), k)), int)
    best, best_set = -1, ()
    for s in range(0, len(combos), 400):
        chunk = combos[s:s + 400]
        add = P[:, chunk].sum(2)                              # n x chunk
        got = ((cnt[:, None] + add) >= nd[:, None]).sum(0)
        i = int(np.argmax(got))
        if got[i] > best:
            best, best_set = int(got[i]), tuple(sorted(market.vocab[pool[j]] for j in chunk[i]))
    if best_set:  # report the exact count for the chosen set
        best = int(reachable(market, have | set(best_set), theta).sum())
    return best, best_set


def check_plan(market: Market, have, theta: float, p: dict, max_k: int = 4) -> dict | None:
    """Compare the plan's first steps (as many whole steps as fit in `max_k` skills, at least 2 skills) with an
    exhaustive search. Returns None when there is nothing meaningful to check (a lone single-skill step is the best
    single skill by construction)."""
    k = 0
    for s in p["steps"]:
        if k + len(s["skills"]) > max_k:
            break
        k += len(s["skills"])
    if k < 2:
        return None
    pool = 30 if k <= 3 else 22
    flat = plan_skills(p)
    got = int(reachable(market, list(have) + flat[:k], theta).sum())
    best, best_set = best_k_skills(market, have, theta, k, pool_size=pool)
    return dict(k=k, got=got, best=best, best_set=best_set, pool=pool, ok=got >= best)


# ---------------------------------------------------------------- views for the app
def skill_demand(market: Market, have=()) -> pd.DataFrame:
    have = with_implied(have)
    cnt = market.X.sum(0)
    d = pd.DataFrame({"skill": market.vocab, "postings": cnt, "share": cnt / max(market.n, 1)})
    d["category"] = d["skill"].map(CATEGORY)
    d["have"] = d["skill"].isin(have)
    return d.sort_values(["postings", "skill"], ascending=[False, True]).reset_index(drop=True)


def wilson_low(k: int, n: int, z: float = 1.96) -> float:
    """Lower end of the 95% Wilson interval for a share k/n: a cautious estimate that shrinks small samples."""
    if n == 0:
        return float("nan")
    p = k / n
    centre = p + z * z / (2 * n)
    spread = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, float((centre - spread) / (1 + z * z / n)))  # clamp float noise (-2e-17 showed as "-0%")


def role_fit(df: pd.DataFrame, have, theta: float, families, cities=None, years=None, include_remote=True) -> pd.DataFrame:
    """Share of each role's postings within reach. Ranked by the Wilson lower bound, so 2 of 9 does not outrank 25 of 202."""
    rows = []
    for fam in families:
        m = build_market(filter_postings(df, [fam], cities, years, include_remote))
        r = int(reachable(m, have, theta).sum()) if m.n else 0
        rows.append(dict(family=fam, postings=m.n, reachable=r, share=r / m.n if m.n else np.nan,
                         share_low=wilson_low(r, m.n),
                         median_coverage=float(np.median(coverage(m, have))) if m.n else np.nan))
    out = pd.DataFrame(rows)
    out["rankable"] = out["postings"] >= MIN_ROLE_POSTINGS
    return (out.sort_values(["rankable", "share_low", "postings"], ascending=[False, False, False], na_position="last")
            .reset_index(drop=True))


def near_misses(market: Market, have, theta: float, short_by: int = 1) -> pd.DataFrame:
    """Postings you are exactly `short_by` skills away from, with which of their skills you lack."""
    have = with_implied(have)
    gap = need(market.sizes, theta) - matched(market, have)
    rows = np.flatnonzero(gap == short_by)
    out = market.postings.iloc[rows][["title", "company", "cities", "exp_min", "exp_max", "skills"]].copy()
    out["missing"] = out["skills"].map(lambda sk: tuple(s for s in sk if s not in have))
    return out.reset_index(drop=True)


def one_away_skills(market: Market, have, theta: float) -> pd.DataFrame:
    """For postings one skill short: which missing skills appear most (any one of them would do for that posting)."""
    nm = near_misses(market, have, theta, 1)
    if nm.empty:
        return pd.DataFrame(columns=["skill", "postings"])
    s = pd.Series([x for t in nm["missing"] for x in t]).value_counts()
    return s.rename_axis("skill").reset_index(name="postings")


def companions(market: Market, skill: str, top: int = 8) -> pd.DataFrame:
    """Skills that most often appear alongside `skill`, with lift over their overall rate."""
    if skill not in market.vocab or market.n == 0:
        return pd.DataFrame(columns=["skill", "together", "lift"])
    j = market.vocab.index(skill)
    rows = market.X[:, j] == 1
    if rows.sum() == 0:
        return pd.DataFrame(columns=["skill", "together", "lift"])
    together = market.X[rows].mean(0)
    base = market.X.mean(0)
    d = pd.DataFrame({"skill": market.vocab, "together": together, "lift": together / np.where(base > 0, base, np.nan)})
    d = d[d["skill"] != skill]
    return d.sort_values(["together", "skill"], ascending=[False, True]).head(top).reset_index(drop=True)


def salary_view(market: Market, mask: np.ndarray) -> dict:
    """Median of the posted salary mid-point (lakh/yr) for postings in `mask` that disclose pay."""
    p = market.postings
    mid = (p["salary_min_lpa"] + p["salary_max_lpa"]) / 2
    sel = mid[mask & mid.notna().to_numpy()]
    return dict(n=int(sel.size), median=float(sel.median()) if sel.size else float("nan"))
