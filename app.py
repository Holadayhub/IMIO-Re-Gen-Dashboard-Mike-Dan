"""
Imio Re-Gen Soil Health — Executive Dashboard (Streamlit)
Holaday Seed Company

Reads blocks_data.json (bundled alongside this file) and reproduces the
Imio Re-Gen executive dashboard: KPI row, risk donut, flagged-metrics chart,
ranch performance chart, grower cards, and a sortable / drillable block table.
"""

import json
import base64
import io
from pathlib import Path
from collections import Counter, defaultdict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------
# Constants — palette & metric labels (kept identical to the HTML dashboard)
# --------------------------------------------------------------------------

NAVY = "#1F3864"
BLUE = "#0070C0"
GREEN = "#00B050"
AMBER = "#FFC000"
RED = "#FF0000"
GREY = "#5A6472"
PENDING_GREY = "#C9CFDA"
BG = "#F4F6FA"
CARD_BG = "#FFFFFF"
BORDER = "#E3E7EF"

METRIC_NAMES = {
    "Fusarium": "Fusarium",
    "K": "Potassium (K)",
    "Sclerotinia": "Sclerotinia",
    "NO3-N": "Nitrate-N (NO3-N)",
    "Olsen-P": "Phosphorus (Olsen-P)",
    "VD": "Verticillium dahliae (VD)",
    "pH": "Soil pH",
    "Pythium": "Pythium",
    "OM": "Organic Matter (OM)",
    "ECe": "ECe - Salinity",
    "Rhizoctonia": "Rhizoctonia",
    "Sclerotium": "Sclerotium",
    "Phoma": "Phoma terrestris",
}

APP_DIR = Path(__file__).parent

# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------


@st.cache_data
def load_data():
    with open(APP_DIR / "blocks_data.json", "r") as f:
        return json.load(f)


def score_color(score):
    if score is None:
        return GREY
    if score >= 1.0:
        return RED
    if score >= 0.4:
        return AMBER
    return GREEN


def score_label(score):
    if score is None:
        return "Pending"
    if score >= 1.0:
        return "High"
    if score >= 0.4:
        return "Moderate"
    return "Low"


def hexc(h, fallback=GREY):
    if not h:
        return fallback
    return h if h.startswith("#") else f"#{h}"


# --------------------------------------------------------------------------
# Stats computation (Python port of the dashboard's computeStats)
# --------------------------------------------------------------------------


def compute_stats(rows):
    total = len(rows)
    scores = [r["score"] for r in rows if r.get("score") is not None]
    high = len([s for s in scores if s >= 1.0])
    moderate = len([s for s in scores if 0.4 <= s < 1.0])
    low = len([s for s in scores if s < 0.4])
    no_data = total - len(scores)
    avg = sum(scores) / len(scores) if scores else None

    flag_counter = Counter()
    for r in rows:
        flags = r.get("flags")
        if flags and flags != "None":
            for part in flags.split(";"):
                part = part.strip()
                if ":" in part:
                    key = part.split(":", 1)[0].strip()
                    flag_counter[key] += 1
    top_flags = flag_counter.most_common(8)

    ranch_scores = defaultdict(list)
    ranch_counts = defaultdict(int)
    for r in rows:
        ranch_counts[r["ranch"]] += 1
        if r.get("score") is not None:
            ranch_scores[r["ranch"]].append(r["score"])
    ranch_avg = {
        k: (sum(v) / len(v) if v else None) for k, v in
        {ranch: ranch_scores.get(ranch, []) for ranch in ranch_counts}.items()
    }

    grower_scores = defaultdict(list)
    grower_counts = defaultdict(int)
    for r in rows:
        grower_counts[r["grower"]] += 1
        if r.get("score") is not None:
            grower_scores[r["grower"]].append(r["score"])
    grower_avg = {
        k: (sum(v) / len(v) if v else None) for k, v in
        {g: grower_scores.get(g, []) for g in grower_counts}.items()
    }

    return dict(
        total=total,
        avg=avg,
        high=high,
        moderate=moderate,
        low=low,
        no_data=no_data,
        top_flags=top_flags,
        ranch_counts=dict(ranch_counts),
        ranch_avg=ranch_avg,
        grower_counts=dict(grower_counts),
        grower_avg=grower_avg,
        n_growers=len(grower_counts),
        n_ranches=len(ranch_counts),
    )


# --------------------------------------------------------------------------
# Page config & global styling
# --------------------------------------------------------------------------

st.set_page_config(
    page_title="Imio Re-Gen Executive Dashboard",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {BG}; }}
    .block-container {{ padding-top: 1.5rem; max-width: 1300px; }}
    .hsc-card {{
        background: {CARD_BG};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 14px 16px;
        height: 100%;
    }}
    .hsc-kpi-value {{
        font-size: 1.7rem;
        font-weight: 700;
        color: {NAVY};
        line-height: 1.1;
        margin-top: 4px;
    }}
    .hsc-kpi-label {{
        font-size: 0.78rem;
        color: {GREY};
        text-transform: uppercase;
        letter-spacing: 0.03em;
        font-weight: 600;
    }}
    .hsc-chip {{
        display: inline-block;
        border-radius: 7px;
        padding: 6px 10px;
        margin: 3px;
        font-size: 0.82rem;
        border: 1px solid rgba(0,0,0,0.06);
        min-width: 132px;
    }}
    .hsc-chip .lbl {{ display:block; font-size: 0.68rem; color:#333; opacity:0.75; }}
    .hsc-chip .val {{ display:block; font-weight:700; font-size: 0.92rem; }}
    .hsc-badge {{
        display: inline-block;
        border-radius: 999px;
        padding: 4px 14px;
        font-weight: 700;
        font-size: 0.85rem;
        color: white;
    }}
    .hsc-section-title {{
        font-size: 1.05rem;
        font-weight: 700;
        color: {NAVY};
        margin: 6px 0 10px 0;
    }}
    .hsc-header-title {{ color: {NAVY}; font-weight: 800; font-size: 1.6rem; margin-bottom:0; }}
    .hsc-header-sub {{ color: {GREY}; font-size: 0.92rem; margin-top:0; }}
    .hsc-nodata {{ color: {GREY}; font-style: italic; font-size: 0.85rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------

hc1, hc2 = st.columns([1, 6], vertical_alignment="center")
with hc1:
    logo_path = APP_DIR / "logo.png"
    if logo_path.exists():
        st.image(str(logo_path), width=90)
with hc2:
    st.markdown('<p class="hsc-header-title">Imio Re-Gen — Executive Dashboard</p>', unsafe_allow_html=True)
    st.markdown('<p class="hsc-header-sub">Holaday Seed Company · Soil Health & Pathogen Monitoring</p>', unsafe_allow_html=True)

st.divider()

# --------------------------------------------------------------------------
# Filter
# --------------------------------------------------------------------------

all_rows = load_data()
growers = sorted(set(r["grower"] for r in all_rows))
options = ["All Growers"] + growers

fc1, fc2 = st.columns([1, 3])
with fc1:
    selected_grower = st.selectbox("Grower", options, index=0)

rows = all_rows if selected_grower == "All Growers" else [r for r in all_rows if r["grower"] == selected_grower]
stats = compute_stats(rows)

# --------------------------------------------------------------------------
# KPI row
# --------------------------------------------------------------------------

avg_txt = f"{stats['avg']:.2f}" if stats["avg"] is not None else "—"
kpis = [
    ("Blocks Sampled", str(stats["total"]), NAVY),
    ("Growers", str(stats["n_growers"]), NAVY),
    ("Ranches", str(stats["n_ranches"]), NAVY),
    ("Avg Soil Health Score", avg_txt, score_color(stats["avg"])),
    ("High-Risk Blocks", str(stats["high"]), RED),
    ("Low-Risk Blocks", str(stats["low"]), GREEN),
    ("Pending Lab Results", str(stats["no_data"]), GREY),
]

kpi_cols = st.columns(7)
for col, (label, value, color) in zip(kpi_cols, kpis):
    with col:
        st.markdown(
            f"""
            <div class="hsc-card" style="border-top:4px solid {color};">
                <div class="hsc-kpi-label">{label}</div>
                <div class="hsc-kpi-value" style="color:{color};">{value}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.write("")

# --------------------------------------------------------------------------
# Donut + Flagged metrics
# --------------------------------------------------------------------------

cc1, cc2 = st.columns([1, 1.4])

with cc1:
    st.markdown('<div class="hsc-section-title">Risk Distribution</div>', unsafe_allow_html=True)
    donut_labels = ["High Risk", "Moderate Risk", "Low Risk", "Pending"]
    donut_values = [stats["high"], stats["moderate"], stats["low"], stats["no_data"]]
    donut_colors = [RED, AMBER, GREEN, PENDING_GREY]

    if sum(donut_values) == 0:
        st.markdown('<p class="hsc-nodata">No data to display.</p>', unsafe_allow_html=True)
    else:
        fig = go.Figure(
            data=[
                go.Pie(
                    labels=donut_labels,
                    values=donut_values,
                    hole=0.62,
                    marker=dict(colors=donut_colors, line=dict(color=CARD_BG, width=2)),
                    textinfo="value",
                    textfont=dict(size=13, color="white"),
                    hovertemplate="%{label}: %{value} blocks (%{percent})<extra></extra>",
                    sort=False,
                )
            ]
        )
        fig.update_layout(
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
            margin=dict(t=10, b=10, l=10, r=10),
            height=300,
            annotations=[
                dict(
                    text=f"<b>{avg_txt}</b><br><span style='font-size:11px;color:{GREY}'>Avg Score</span>",
                    x=0.5, y=0.5, font=dict(size=20, color=NAVY), showarrow=False,
                )
            ],
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with cc2:
    st.markdown('<div class="hsc-section-title">Most Frequently Flagged Metrics</div>', unsafe_allow_html=True)
    if not stats["top_flags"]:
        st.markdown('<p class="hsc-nodata">No flagged metrics.</p>', unsafe_allow_html=True)
    else:
        flag_labels = [METRIC_NAMES.get(k, k) for k, _ in stats["top_flags"]][::-1]
        flag_values = [v for _, v in stats["top_flags"]][::-1]
        fig2 = go.Figure(
            data=[
                go.Bar(
                    x=flag_values,
                    y=flag_labels,
                    orientation="h",
                    marker=dict(color=BLUE),
                    text=flag_values,
                    textposition="outside",
                    hovertemplate="%{y}: %{x} blocks flagged<extra></extra>",
                )
            ]
        )
        fig2.update_layout(
            margin=dict(t=10, b=10, l=10, r=20),
            height=300,
            xaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False, title=None),
            yaxis=dict(showgrid=False, title=None),
            plot_bgcolor=CARD_BG,
            paper_bgcolor=CARD_BG,
        )
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

st.write("")

# --------------------------------------------------------------------------
# Ranch performance
# --------------------------------------------------------------------------

st.markdown('<div class="hsc-section-title">Average Soil Health Score by Ranch</div>', unsafe_allow_html=True)

ranch_items = list(stats["ranch_avg"].items())
ranch_items.sort(key=lambda kv: (kv[1] is None, -(kv[1] if kv[1] is not None else 0)))

if not ranch_items:
    st.markdown('<p class="hsc-nodata">No ranches to display.</p>', unsafe_allow_html=True)
else:
    r_names = [k for k, v in ranch_items][::-1]
    r_vals = [v for k, v in ranch_items][::-1]
    r_plot_vals = [v if v is not None else 0.03 for v in r_vals]
    r_colors = [score_color(v) if v is not None else PENDING_GREY for v in r_vals]
    r_text = [f"{v:.2f}" if v is not None else "No data" for v in r_vals]

    fig3 = go.Figure(
        data=[
            go.Bar(
                x=r_plot_vals,
                y=r_names,
                orientation="h",
                marker=dict(color=r_colors),
                text=r_text,
                textposition="outside",
                hovertemplate="%{y}: %{text}<extra></extra>",
            )
        ]
    )
    fig3.update_layout(
        margin=dict(t=10, b=10, l=10, r=40),
        height=max(220, 42 * len(r_names)),
        xaxis=dict(showgrid=True, gridcolor=BORDER, zeroline=False, range=[0, max(1.4, max(r_plot_vals) * 1.25)], title=None),
        yaxis=dict(showgrid=False, title=None),
        plot_bgcolor=CARD_BG,
        paper_bgcolor=CARD_BG,
    )
    st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

st.write("")

# --------------------------------------------------------------------------
# Grower cards
# --------------------------------------------------------------------------

st.markdown('<div class="hsc-section-title">Growers</div>', unsafe_allow_html=True)
grower_items = sorted(stats["grower_avg"].items(), key=lambda kv: kv[0])

if grower_items:
    g_cols = st.columns(len(grower_items))
    for col, (gname, gavg) in zip(g_cols, grower_items):
        gcount = stats["grower_counts"][gname]
        color = score_color(gavg)
        val_txt = f"{gavg:.2f}" if gavg is not None else "no data yet"
        with col:
            st.markdown(
                f"""
                <div class="hsc-card" style="border-top:4px solid {color};">
                    <div class="hsc-kpi-label">{gname}</div>
                    <div class="hsc-kpi-value" style="color:{color}; font-size:1.25rem;">{val_txt}</div>
                    <div class="hsc-nodata" style="font-style:normal;">{gcount} block{'s' if gcount != 1 else ''}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.write("")
st.divider()

# --------------------------------------------------------------------------
# Data table
# --------------------------------------------------------------------------

st.markdown('<div class="hsc-section-title">Block Detail</div>', unsafe_allow_html=True)

table_rows = []
for r in rows:
    table_rows.append(
        {
            "Rank": r.get("rank"),
            "Grower": r["grower"],
            "Ranch": r["ranch"],
            "Block": r["block"],
            "Score": r.get("score"),
            "Risk": score_label(r.get("score")),
            "Metrics Scored": r.get("scored"),
            "Flagged Metrics": r.get("flags") or "None",
        }
    )
df = pd.DataFrame(table_rows).sort_values("Rank", na_position="last").reset_index(drop=True)


def style_risk(val):
    colors = {"High": RED, "Moderate": AMBER, "Low": GREEN, "Pending": GREY}
    c = colors.get(val, GREY)
    return f"color: {c}; font-weight: 700;"


_style_fn = df.style.map if hasattr(df.style, "map") else df.style.applymap
styled = _style_fn(style_risk, subset=["Risk"]).format({"Score": lambda v: f"{v:.2f}" if pd.notnull(v) else "—"})

st.dataframe(
    styled,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Rank": st.column_config.NumberColumn("Rank", width="small"),
        "Score": st.column_config.TextColumn("Score", width="small"),
    },
)

# --------------------------------------------------------------------------
# Row detail drill-down
# --------------------------------------------------------------------------

st.markdown('<div class="hsc-section-title">Block Drill-Down</div>', unsafe_allow_html=True)

label_map = {}
for r in rows:
    rank = r.get("rank")
    label = f"#{rank if rank is not None else '—'} · {r['grower']} / {r['ranch']} / {r['block']}"
    label_map[label] = r

if not label_map:
    st.markdown('<p class="hsc-nodata">No blocks for this filter.</p>', unsafe_allow_html=True)
else:
    sorted_labels = sorted(label_map.keys(), key=lambda l: (label_map[l].get("rank") is None, label_map[l].get("rank") or 0))
    chosen_label = st.selectbox("Select a block", sorted_labels)
    rec = label_map[chosen_label]

    overall_score = rec.get("score")
    nutrient_score = rec.get("nutrient_score")
    pathogen_score = rec.get("pathogen_score")
    overall_txt = f"{overall_score:.2f} · {score_label(overall_score)}" if overall_score is not None else "Pending"
    nutrient_txt = f"{nutrient_score:.2f}" if nutrient_score is not None else "—"
    pathogen_txt = f"{pathogen_score:.2f}" if pathogen_score is not None else "—"

    dc1, dc2, dc3 = st.columns(3)
    with dc1:
        st.markdown(f"**Overall Score:** <span class='hsc-badge' style='background:{score_color(overall_score)}'>{overall_txt}</span>", unsafe_allow_html=True)
    with dc2:
        st.markdown(f"**Nutrient Sub-Score:** <span class='hsc-badge' style='background:{score_color(nutrient_score)}'>{nutrient_txt}</span>", unsafe_allow_html=True)
    with dc3:
        st.markdown(f"**Pathogen Sub-Score:** <span class='hsc-badge' style='background:{score_color(pathogen_score)}'>{pathogen_txt}</span>", unsafe_allow_html=True)

    st.write("")
    meta_bits = []
    for key, label in [
        ("crop_cycle", "Crop Cycle"),
        ("crop_cycle_2", "Crop Cycle 2"),
        ("application_method", "Application Method"),
        ("health_sample_date", "Health Sample Date"),
        ("health_sample_2_date", "Health Sample 2 Date"),
        ("pathology_sample_date", "Pathology Sample Date"),
        ("soil_results_date", "Soil Results Date"),
        ("pathology_results_date", "Pathology Results Date"),
    ]:
        v = rec.get(key)
        if v:
            meta_bits.append(f"**{label}:** {v}")
    if meta_bits:
        st.markdown(" &nbsp;·&nbsp; ".join(meta_bits))

    def _to_num(v):
        try:
            if v in (None, "ND", ""):
                return None
            return float(v)
        except (TypeError, ValueError):
            return None

    def _pct_change(first, last):
        a = _to_num(first)
        b = _to_num(last)
        if a is None or b is None or a == 0:
            return "—"
        pct = (b - a) / abs(a) * 100
        if abs(pct) < 0.05:
            return "0.0%"
        return f"{pct:+.1f}%"

    def render_compare_table(groups, caption, first_label="first results"):
        """groups: list of {label, date, items} where items is a list of {label,unit,value} metric dicts, all same length/order.
        The first group is the baseline (value column only). Every subsequent group gets its own value
        column PLUS its own '% Δ' column measured back to the baseline — so a block with 3+ sub-areas
        or sampling rounds gets one % Δ column per non-baseline group, not just a single first-to-last column."""
        if not groups:
            return
        n_metrics = len(groups[-1]["items"])
        first_items = groups[0]["items"]

        # col_plan: ("value", header, group) for every group; ("pct", header, group) for every non-baseline group
        col_plan = [("value", groups[0]["label"] + (f" ({groups[0]['date']})" if groups[0].get("date") else ""), groups[0])]
        for g in groups[1:]:
            header = g["label"] + (f" ({g['date']})" if g.get("date") else "")
            col_plan.append(("value", header, g))
            col_plan.append(("pct", f"% Δ ({g['label']})", g))

        value_headers = [h for t, h, _ in col_plan if t == "value"]
        columns_order = ["Metric"] + [h for _, h, _ in col_plan]

        table_rows = []
        for idx in range(n_metrics):
            meta = groups[-1]["items"][idx]
            row = {"Metric": meta["label"] + (f" ({meta['unit']})" if meta.get("unit") else "")}
            first_val = first_items[idx]["value"] if idx < len(first_items) else None
            for col_type, header, g in col_plan:
                items = g["items"]
                val = items[idx]["value"] if idx < len(items) else None
                if col_type == "value":
                    row[header] = "—" if val is None else str(val)
                else:
                    row[header] = _pct_change(first_val, val) if len(groups) > 1 else "—"
            table_rows.append(row)
        cmp_df = pd.DataFrame(table_rows, columns=columns_order)

        def _highlight_change(row):
            vals = [row[h] for h in value_headers]
            present = [v for v in vals if v != "—"]
            if len(set(present)) > 1:
                return [""] + [f"background-color: {AMBER}22; font-weight:700;"] * (len(row) - 1)
            return [""] * len(row)

        st.dataframe(
            cmp_df.style.apply(_highlight_change, axis=1),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"{caption} Each \"% Δ\" column is measured from the {first_label} for this block.")
        st.write("")

    history = rec.get("nutrient_history") or []
    nutrient_areas = rec.get("nutrient_areas") or []
    pathogen_areas = rec.get("pathogen_areas") or []

    st.write("")
    if history:
        st.markdown("**Nutrients — Sampling Rounds Compared**")
        rounds = [{"label": h.get("label") or f"Round {i+1}", "date": h.get("date"), "items": h["nutrients"]} for i, h in enumerate(history)]
        rounds.append({"label": f"Round {len(rounds)+1} (latest)", "date": rec.get("soil_results_date") or rec.get("health_sample_2_date") or rec.get("health_sample_date"), "items": rec.get("nutrients", [])})
        render_compare_table(rounds, "Highlighted rows changed between sampling rounds.", first_label="first sampling round")

    if nutrient_areas:
        st.markdown("**Nutrients — By Submit Area**")
        areas = [{"label": a["area"], "date": a.get("date"), "items": a["nutrients"]} for a in nutrient_areas]
        render_compare_table(areas, "This block combines multiple sampled sub-areas — highlighted rows differ by area.", first_label="first submit area on file")

    if pathogen_areas and any(any(p["value"] is not None for p in a["pathogens"]) for a in pathogen_areas):
        st.markdown("**Pathogens — By Submit Area**")
        p_areas = [{"label": a["area"], "date": a.get("date"), "items": a["pathogens"]} for a in pathogen_areas]
        render_compare_table(p_areas, "This block combines multiple sampled sub-areas — highlighted rows differ by area.", first_label="first submit area on file")

    nut_title = "**Nutrients (latest)**" if history else ("**Nutrients (combined)**" if nutrient_areas else "**Nutrients**")
    st.markdown(nut_title)
    nut_html = "".join(
        f"""<span class="hsc-chip" style="background:{hexc(n['color'])}22; border-color:{hexc(n['color'])};">
            <span class="lbl">{n['label']}</span>
            <span class="val" style="color:{hexc(n['color'])};">{n['value']}{(' ' + n['unit']) if n.get('unit') else ''}</span>
        </span>"""
        for n in rec.get("nutrients", [])
    )
    st.markdown(nut_html, unsafe_allow_html=True)

    st.write("")
    path_title = "**Pathogens (combined)**" if pathogen_areas else "**Pathogens**"
    st.markdown(path_title)
    path_html = "".join(
        f"""<span class="hsc-chip" style="background:{hexc(p['color'])}22; border-color:{hexc(p['color'])};">
            <span class="lbl">{p['label']}</span>
            <span class="val" style="color:{hexc(p['color'])};">{p['value']}{(' ' + p['unit']) if p.get('unit') else ''}</span>
        </span>"""
        for p in rec.get("pathogens", [])
    )
    st.markdown(path_html, unsafe_allow_html=True)

    if rec.get("recommendations"):
        st.write("")
        st.markdown("**Recommendations**")
        st.info(rec["recommendations"])

    if rec.get("notes"):
        st.write("")
        st.markdown("**Notes**")
        for note in rec["notes"]:
            st.markdown(f"- {note}")

    photos = rec.get("photos") or []
    if photos:
        st.write("")
        st.markdown("**Field Photos**")
        photo_cols = st.columns(min(4, len(photos)))
        for i, p in enumerate(photos):
            try:
                header, b64 = p.split(",", 1) if "," in p else ("", p)
                img_bytes = base64.b64decode(b64)
                with photo_cols[i % len(photo_cols)]:
                    st.image(io.BytesIO(img_bytes), use_container_width=True)
            except Exception:
                continue

st.write("")
st.caption("Imio Re-Gen Soil Health Program · Holaday Seed Company — data current as of last tracker update.")
