"""Look & feel for Skill Gap Map: tokens (light + dark), CSS, HTML pieces and a shared Plotly style."""
from html import escape

import plotly.graph_objects as go
import streamlit as st

FONT = "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"
MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace"
DISPLAY = "'Space Grotesk', Inter, system-ui, sans-serif"

# Categorical slots validated for colour-blind separation (adjacent pairs, both modes): one per skill category.
TOKENS = {
    "light": dict(
        card="#ffffff", border="rgba(20,16,60,0.10)", border_solid="#e2e0ef", text1="#110e2b", text2="#46435f",
        muted="#7c7994", grid="#ecebf5", axis="#c9c6dc", brand="#5b45e0", brand_text="#4a35c9",
        brand_soft="rgba(91,69,224,0.10)", gold="#b7791f", gold_soft="rgba(245,176,51,0.18)", have="#5b45e0",
        series=["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
        neutral="#cfcde0", shadow="0 1px 2px rgba(17,14,43,0.04), 0 8px 24px rgba(17,14,43,0.06)",
    ),
    "dark": dict(
        card="#14122a", border="rgba(255,255,255,0.09)", border_solid="#2a2748", text1="#efedff", text2="#bdb9d8",
        muted="#8a86a8", grid="#221f3d", axis="#38345a", brand="#a497ff", brand_text="#b9afff",
        brand_soft="rgba(164,151,255,0.13)", gold="#f5b033", gold_soft="rgba(245,176,51,0.12)", have="#a497ff",
        series=["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767"],
        neutral="#34304f", shadow="0 1px 2px rgba(0,0,0,0.35)",
    ),
}


def mode() -> str:
    try:
        return "dark" if st.context.theme.type == "dark" else "light"
    except Exception:
        return "light"


def tokens() -> dict:
    return TOKENS[mode()]


def _md_html(html: str) -> None:
    """Markdown ends an HTML block at a blank line, so drop blank lines before injecting raw HTML/CSS."""
    st.markdown("\n".join(line for line in html.splitlines() if line.strip()), unsafe_allow_html=True)


def inject_css() -> None:
    t = tokens()
    _md_html(f"""
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600;700&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
    <style>
    .block-container {{ padding-top: 2rem; max-width: 1260px; }}
    h1, h2, h3 {{ letter-spacing: -0.02em; }}
    .hero {{ position: relative; overflow: hidden; border-radius: 24px; border: 1px solid {t['border']};
             padding: 26px 30px 22px; margin-bottom: 16px; background: {t['card']}; box-shadow: {t['shadow']};
             display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 24px; align-items: center; }}
    .hero::before {{ content: ""; position: absolute; inset: 0; pointer-events: none;
             background: radial-gradient(55% 120% at 100% 0%, {t['brand_soft']}, transparent 62%),
                         radial-gradient(35% 80% at 80% 100%, {t['gold_soft']}, transparent 70%); }}
    .hero > * {{ position: relative; }}
    .hero .eyebrow {{ color: {t['brand_text']}; font-weight: 700; font-size: .76rem; letter-spacing: .1em; text-transform: uppercase; }}
    .hero h1 {{ font-family: {DISPLAY}; font-weight: 700; font-size: 2.2rem; line-height: 1.08; margin: 4px 0 8px; padding: 0;
               color: {t['text1']}; letter-spacing: -0.02em; }}
    .hero h1 em {{ font-style: normal; color: {t['brand_text']}; }}
    .hero p {{ color: {t['text2']}; margin: 0 0 14px; }}
    .hero svg.climb {{ width: 100%; height: 170px; }}
    @media (max-width: 1180px) {{ .hero {{ grid-template-columns: 1fr; gap: 8px; }} .hero svg.climb {{ height: 110px; }} }}
    @media (max-width: 640px) {{ .hero {{ padding: 20px 18px 16px; }} .hero h1 {{ font-size: 1.6rem; }} }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .chip {{ display: inline-flex; gap: 6px; align-items: center; padding: 5px 11px; border-radius: 999px; font-size: .8rem;
            background: {t['card']}; border: 1px solid {t['border']}; color: {t['text2']}; }}
    .chip b {{ color: {t['text1']}; font-weight: 600; }}
    .kpis {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 4px 0 16px; }}
    @media (max-width: 900px) {{ .kpis {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
    .kpi {{ background: {t['card']}; border: 1px solid {t['border']}; border-radius: 16px; padding: 14px 16px; box-shadow: {t['shadow']}; min-width: 0; }}
    .kpi.accent {{ border-color: {t['brand']}; box-shadow: 0 0 0 1px {t['brand']} inset, {t['shadow']}; }}
    .kpi .label {{ color: {t['muted']}; font-size: .72rem; font-weight: 600; letter-spacing: .07em; text-transform: uppercase; }}
    .kpi .value {{ font-family: {MONO}; color: {t['text1']}; font-size: 1.65rem; font-weight: 600; margin-top: 4px; line-height: 1.15;
                  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .kpi .sub {{ color: {t['text2']}; font-size: .82rem; margin-top: 3px; }}
    .section {{ display: flex; align-items: baseline; gap: 8px; margin: 2px 0 6px; flex-wrap: wrap; }}
    .section .t {{ font-weight: 700; font-size: 1.02rem; color: {t['text1']}; }}
    .section .d {{ color: {t['muted']}; font-size: .85rem; }}
    .note {{ border-radius: 14px; padding: 12px 16px; margin: 6px 0 14px; border: 1px solid {t['border']}; color: {t['text2']};
            background: {t['card']}; font-size: .9rem; }}
    .note.warn {{ border-color: {t['gold']}; background: {t['gold_soft']}; color: {t['text1']}; }}
    .note b {{ color: {t['text1']}; }}
    .steps {{ display: grid; gap: 10px; margin: 6px 0 14px; }}
    .step {{ display: grid; grid-template-columns: 46px minmax(0, 1fr) auto; gap: 14px; align-items: start; border-radius: 18px;
            padding: 14px 18px; border: 1px solid {t['border']}; background: {t['card']}; box-shadow: {t['shadow']}; }}
    .step .num {{ width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center; font-family: {DISPLAY};
                 font-weight: 700; font-size: 1.15rem; color: {t['brand_text']}; background: {t['brand_soft']}; }}
    .step .sk {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 6px; }}
    .step .tag {{ padding: 4px 10px; border-radius: 999px; font-weight: 700; font-size: .86rem; color: {t['text1']};
                 border: 1px solid var(--c); background: color-mix(in srgb, var(--c) 14%, transparent); }}
    .step .together {{ font-size: .74rem; color: {t['muted']}; align-self: center; }}
    .step .why {{ color: {t['text2']}; font-size: .86rem; }}
    .step .gain {{ text-align: right; }}
    .step .gain .v {{ font-family: {MONO}; font-weight: 600; font-size: 1.35rem; color: {t['brand_text']}; line-height: 1.1; }}
    .step .gain .l {{ font-size: .74rem; color: {t['muted']}; }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: .8rem; color: {t['text2']}; margin: 0 0 6px; }}
    .legend i {{ display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }}
    .brand {{ display: flex; align-items: center; gap: 10px; margin: -6px 0 8px; }}
    .brand .n {{ font-family: {DISPLAY}; font-weight: 700; font-size: 1.15rem; color: {t['text1']}; line-height: 1.05; }}
    .brand .s {{ font-size: .74rem; color: {t['muted']}; }}
    div[data-testid="stTabs"] button[role="tab"] p {{ font-size: .93rem; font-weight: 600; }}
    </style>""")


def brand() -> None:
    t = tokens()
    _md_html(f'<div class="brand"><svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true">'
             f'<rect width="34" height="34" rx="10" fill="{t["brand_soft"]}"/>'
             f'<path d="M7 26 H13 V20 H19 V14 H25 V8" fill="none" stroke="{t["brand"]}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>'
             f'<circle cx="25" cy="8" r="3" fill="{t["gold"]}"/></svg>'
             '<div><div class="n">Skill Gap Map</div><div class="s">What to learn next</div></div></div>')


def climb_svg(values: list[int], total: int) -> str:
    """A staircase of postings within reach after each step (the hero's picture of the plan)."""
    t = tokens()
    w, h, pad = 320, 170, 10
    top = max(max(values), 1)
    n = len(values)
    xs = [pad + i * (w - 2 * pad) / max(n, 1) for i in range(n + 1)]
    ys = [h - pad - (v / top) * (h - 2 * pad - 14) for v in values]
    d = f"M{xs[0]:.1f},{h - pad:.1f} L{xs[0]:.1f},{ys[0]:.1f}"
    for i in range(n):
        d += f" L{xs[i + 1]:.1f},{ys[i]:.1f}"
        if i + 1 < n:
            d += f" L{xs[i + 1]:.1f},{ys[i + 1]:.1f}"
    area = d + f" L{xs[-1]:.1f},{h - pad:.1f} Z"
    dots = "".join(f'<circle cx="{xs[i]:.1f}" cy="{ys[i]:.1f}" r="3.5" fill="{t["brand"]}"/>' for i in range(1, n))
    return (f'<svg class="climb" viewBox="0 0 {w} {h}" preserveAspectRatio="none" role="img" '
            f'aria-label="Postings within reach grow from {values[0]} to {values[-1]} of {total}">'
            f'<line x1="{pad}" x2="{w - pad}" y1="{h - pad}" y2="{h - pad}" stroke="{t["axis"]}"/>'
            f'<path d="{area}" fill="{t["brand_soft"]}"/>'
            f'<path d="{d}" fill="none" stroke="{t["brand"]}" stroke-width="3" stroke-linejoin="round"/>{dots}'
            f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="6" fill="{t["gold"]}"/>'
            f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="11" fill="none" stroke="{t["gold"]}" stroke-opacity=".45"/></svg>')


def hero(eyebrow: str, title_html: str, text: str, chips: list[tuple[str, str]], climb: list[int], total: int) -> None:
    """`title_html` may contain <em> for the highlighted number; everything else is escaped by the caller."""
    chip_html = "".join(f'<span class="chip">{escape(k)} <b>{escape(v)}</b></span>' for k, v in chips)
    pic = climb_svg(climb, total) if len(climb) >= 2 else ""
    _md_html(f'<div class="hero"><div><div class="eyebrow">{escape(eyebrow)}</div><h1>{title_html}</h1>'
             f'<p>{escape(text)}</p><div class="chips">{chip_html}</div></div><div>{pic}</div></div>')


def kpi(label: str, value: str, sub: str = "", accent: bool = False) -> str:
    return (f'<div class="kpi{" accent" if accent else ""}"><div class="label">{escape(label)}</div>'
            f'<div class="value">{escape(value)}</div><div class="sub">{escape(sub)}</div></div>')


def kpi_row(cards: list[str]) -> None:
    _md_html(f'<div class="kpis">{"".join(cards)}</div>')


def section(title: str, desc: str = "") -> None:
    d = f'<span class="d">{escape(desc)}</span>' if desc else ""
    _md_html(f'<div class="section"><span class="t">{escape(title)}</span>{d}</div>')


def note(text_html: str, warn: bool = False) -> None:
    _md_html(f'<div class="note{" warn" if warn else ""}">{text_html}</div>')


def steps(cards: list[dict]) -> None:
    """cards: dict(num, skills=[(name, colour)], why, gain, reach)."""
    out = []
    for c in cards:
        tags = "".join(f'<span class="tag" style="--c:{col}">{escape(s)}</span>' for s, col in c["skills"])
        if len(c["skills"]) > 1:
            tags += '<span class="together">learn together</span>'
        out.append(f'<div class="step"><div class="num">{c["num"]}</div><div><div class="sk">{tags}</div>'
                   f'<div class="why">{c["why"]}</div></div><div class="gain"><div class="v">+{c["gain"]:,}</div>'
                   f'<div class="l">postings<br>{escape(c["reach"])}</div></div></div>')
    _md_html(f'<div class="steps">{"".join(out)}</div>')


def legend(items: list[tuple[str, str]]) -> None:
    _md_html('<div class="legend">' + "".join(f'<span><i style="background:{c}"></i>{escape(n)}</span>' for n, c in items) + "</div>")


def html(block: str) -> None:
    _md_html(block)


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def style(fig: go.Figure, height: int = 320, legend: bool = False) -> go.Figure:
    t = tokens()
    fig.update_layout(
        height=height, margin=dict(l=4, r=14, t=34 if legend else 8, b=4),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color=t["text2"], size=13), title=None,
        hoverlabel=dict(bgcolor=t["card"], bordercolor=t["border_solid"], font=dict(family=FONT, color=t["text1"])),
        showlegend=legend, legend=dict(orientation="h", x=0, y=1.0, yanchor="bottom", font=dict(color=t["text2"]), title=None),
        barcornerradius=4, bargap=0.3, bargroupgap=0.12,
    )
    axis = dict(automargin=True, gridcolor=t["grid"], linecolor=t["axis"], zeroline=False,
                tickfont=dict(color=t["muted"]), title=dict(font=dict(color=t["muted"])))
    fig.update_xaxes(**axis)
    fig.update_yaxes(**axis)
    return fig


def show(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False})
