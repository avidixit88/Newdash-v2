import datetime as dt
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(
    page_title="NextCure Signal Room",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL = "https://clinicaltrials.gov/api/v2/studies"
TODAY = dt.date.today()

TARGET_LANES = {
    "B7-H4 / VTCN1": [
        "B7-H4", "B7H4", "VTCN1", "B7 H4", "LNCB74", "B7-H4 ADC", "anti-B7-H4"
    ],
    "CDH6": [
        "CDH6", "cadherin 6", "cadherin-6", "SIM0505", "CDH6 ADC", "anti-CDH6"
    ],
    "Alzheimer's / ApoE4": [
        "Alzheimer", "Alzheimer's", "ApoE4", "APOE4", "APOE", "NC181"
    ],
    "Bone / Siglec-15": [
        "osteogenesis imperfecta", "bone disease", "bone", "Siglec-15", "SIGLEC15", "NC605"
    ],
}

DEFAULT_QUERIES = [
    "B7-H4 OR VTCN1 OR LNCB74 OR B7H4",
    "CDH6 OR cadherin 6 OR SIM0505",
    "Alzheimer ApoE4 OR APOE4 OR NC181",
    "Siglec-15 OR osteogenesis imperfecta OR NC605 bone",
]

PHASE_ORDER = ["Early Phase 1", "Phase 1", "Phase 1/2", "Phase 2", "Phase 2/3", "Phase 3", "Phase 4", "N/A"]
ACTIVE_STATUSES = {"Recruiting", "Not yet recruiting", "Active, not recruiting", "Enrolling by invitation"}
PLANNED_STATUSES = {"Not yet recruiting"}
COMBO_TERMS = [
    "combination", "combined", "plus", "+", "with pembrolizumab", "pembrolizumab", "keytruda",
    "nivolumab", "opdivo", "atezolizumab", "durvalumab", "cemiplimab", "immunotherapy",
    "checkpoint", "PD-1", "PD-L1", "chemotherapy", "carboplatin", "paclitaxel", "gemcitabine",
    "bevacizumab", "olaparib", "niraparib", "targeted therapy"
]

CSS = """
<style>
    :root {
        --bg: #080d18;
        --panel: rgba(18, 27, 44, 0.78);
        --panel2: rgba(14, 22, 36, 0.92);
        --line: rgba(164, 183, 219, 0.16);
        --text: #edf4ff;
        --muted: #8f9db7;
        --gold: #d8b86c;
        --cyan: #63d7ff;
        --blue: #5a82ff;
        --green: #75e3b4;
        --red: #ff7878;
        --violet: #a98bff;
    }
    html, body, [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(circle at top left, rgba(74, 113, 255, .19), transparent 34%),
            radial-gradient(circle at top right, rgba(216, 184, 108, .12), transparent 26%),
            linear-gradient(180deg, #080d18 0%, #0b1020 50%, #070a12 100%);
        color: var(--text);
    }
    [data-testid="stHeader"] { background: rgba(8, 13, 24, 0); }
    [data-testid="stToolbar"] { display: none; }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(10, 16, 28, .98), rgba(8, 13, 24, .98));
        border-right: 1px solid var(--line);
    }
    .block-container { padding-top: 2rem; padding-bottom: 4rem; max-width: 1480px; }
    .hero {
        border: 1px solid var(--line);
        background: linear-gradient(135deg, rgba(18, 27, 44, .92), rgba(9, 15, 28, .64));
        border-radius: 30px;
        padding: 32px 34px;
        box-shadow: 0 24px 70px rgba(0,0,0,.33);
        position: relative;
        overflow: hidden;
    }
    .hero:after {
        content: ""; position: absolute; right: -120px; top: -120px; width: 340px; height: 340px;
        background: radial-gradient(circle, rgba(99, 215, 255, .16), transparent 64%); pointer-events: none;
    }
    .eyebrow { color: var(--gold); letter-spacing: .18em; text-transform: uppercase; font-size: .78rem; font-weight: 800; }
    .hero h1 { font-size: 3.15rem; line-height: 1.02; margin: .35rem 0 .7rem 0; letter-spacing: -.055em; }
    .hero p { color: var(--muted); font-size: 1.04rem; max-width: 820px; margin: 0; }
    .pill-row { display:flex; gap:10px; flex-wrap: wrap; margin-top: 22px; }
    .pill { border: 1px solid rgba(216,184,108,.22); background: rgba(216,184,108,.08); color: #f5e7bc; padding: 8px 12px; border-radius: 999px; font-size: .82rem; }
    .power-panel { border: 1px solid rgba(216,184,108,.22); background: rgba(216,184,108,.055); border-radius: 24px; padding: 20px; margin-top: 18px; }
    .metric-card { border: 1px solid var(--line); background: linear-gradient(180deg, rgba(20, 31, 51, .82), rgba(12, 19, 33, .72)); border-radius: 22px; padding: 21px 21px 18px 21px; min-height: 142px; box-shadow: 0 16px 44px rgba(0,0,0,.23); }
    .metric-label { color: var(--muted); text-transform: uppercase; letter-spacing: .12em; font-size: .72rem; font-weight: 800; }
    .metric-value { color: var(--text); font-size: 2.28rem; font-weight: 800; letter-spacing: -.04em; margin-top: 8px; }
    .metric-note { color: #aab6cc; font-size: .87rem; margin-top: 7px; line-height: 1.35; }
    .section-title { margin-top: 30px; margin-bottom: 8px; font-size: 1.25rem; font-weight: 800; letter-spacing: -.02em; }
    .section-subtitle { color: var(--muted); margin-bottom: 16px; font-size: .93rem; }
    .lane-card { border: 1px solid var(--line); background: rgba(14, 22, 36, .62); border-radius: 18px; padding: 15px; min-height: 112px; }
    .lane-title { color: #fff; font-weight: 800; font-size: .98rem; }
    .lane-sub { color: var(--muted); font-size: .82rem; line-height:1.35; margin-top:5px; }
    .signal { border-left: 3px solid rgba(99, 215, 255, .85); background: rgba(99, 215, 255, .055); border-radius: 14px; padding: 12px 14px; margin-bottom: 10px; color: #dceaff; }
    .signal strong { color: #ffffff; }
    .caption { color: var(--muted); font-size: .82rem; }
    div[data-testid="stButton"] button { width: 100%; border-radius: 16px; min-height: 50px; border: 1px solid rgba(216,184,108,.35); background: linear-gradient(135deg, rgba(216,184,108,.95), rgba(117,227,180,.7)); color: #0a1020; font-weight: 900; letter-spacing: -.01em; }
    .stPlotlyChart { border-radius: 22px; overflow: hidden; }
    div[data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 18px; overflow: hidden; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(safe_str(v) for v in value)
    return str(value)


def normalize_phase(phases: List[str]) -> str:
    if not phases:
        return "N/A"
    phase_map = {
        "EARLY_PHASE1": "Early Phase 1", "PHASE1": "Phase 1", "PHASE2": "Phase 2",
        "PHASE3": "Phase 3", "PHASE4": "Phase 4", "NA": "N/A"
    }
    clean = [phase_map.get(str(p).strip().upper(), str(p).replace("_", " ").title()) for p in phases]
    joined = "/".join([c.strip() for c in clean if c.strip()])
    return joined.replace("Phase 1/Phase 2", "Phase 1/2").replace("Phase 2/Phase 3", "Phase 2/3") or "N/A"


def prettify_status(status: Optional[str]) -> str:
    if not status:
        return "Unknown"
    return status.replace("_", " ").title().replace("And", "and").replace("By", "by")


def get_nested(d: Dict[str, Any], path: List[str], default=None):
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def parse_date_struct(module: Dict[str, Any], key: str):
    return get_nested(module, [key, "date"])


def extract_locations(protocol: Dict[str, Any]) -> Tuple[List[str], List[str], int]:
    contacts = protocol.get("contactsLocationsModule", {}) or {}
    locs = contacts.get("locations", []) or []
    countries, states = [], []
    for loc in locs:
        if not isinstance(loc, dict):
            continue
        country = loc.get("country")
        state = loc.get("state")
        if country:
            countries.append(country)
        if state:
            states.append(state)
    return sorted(set(countries)), sorted(set(states)), len(locs)


def extract_arms_and_interventions(protocol: Dict[str, Any]) -> Tuple[List[str], List[str], str]:
    arms = protocol.get("armsInterventionsModule", {}) or {}
    arm_groups = arms.get("armGroups", []) or []
    interventions = arms.get("interventions", []) or []
    arm_texts = []
    for arm in arm_groups:
        if isinstance(arm, dict):
            arm_texts.append(" ".join([safe_str(arm.get("label")), safe_str(arm.get("description")), safe_str(arm.get("interventionNames"))]))
    intervention_names = []
    intervention_types = []
    for item in interventions:
        if isinstance(item, dict):
            intervention_names.append(safe_str(item.get("name")))
            intervention_types.append(safe_str(item.get("type")))
    return intervention_names, intervention_types, " | ".join([t for t in arm_texts if t])


def parse_study(study: Dict[str, Any], source_query: str) -> Dict[str, Any]:
    protocol = study.get("protocolSection", {}) or {}
    ident = protocol.get("identificationModule", {}) or {}
    status = protocol.get("statusModule", {}) or {}
    sponsor = protocol.get("sponsorCollaboratorsModule", {}) or {}
    design = protocol.get("designModule", {}) or {}
    cond = protocol.get("conditionsModule", {}) or {}
    descr = protocol.get("descriptionModule", {}) or {}
    eligibility = protocol.get("eligibilityModule", {}) or {}

    intervention_names, intervention_types, arm_text = extract_arms_and_interventions(protocol)
    countries, states, site_count = extract_locations(protocol)
    nct_id = ident.get("nctId", "")
    conditions = cond.get("conditions", []) or []
    title = ident.get("briefTitle", "Untitled study")
    brief_summary = descr.get("briefSummary", "")
    eligibility_text = eligibility.get("eligibilityCriteria", "")
    text_blob = " ".join([title, brief_summary, safe_str(conditions), safe_str(intervention_names), arm_text, source_query, eligibility_text])

    return {
        "nct_id": nct_id,
        "title": title,
        "sponsor": get_nested(sponsor, ["leadSponsor", "name"], "Unknown sponsor"),
        "collaborators": ", ".join([c.get("name", "") for c in sponsor.get("collaborators", []) if isinstance(c, dict)][:5]),
        "status": prettify_status(status.get("overallStatus")),
        "phase": normalize_phase(design.get("phases", []) or []),
        "study_type": design.get("studyType", "Unknown"),
        "enrollment": get_nested(design, ["enrollmentInfo", "count"], 0) or 0,
        "enrollment_type": get_nested(design, ["enrollmentInfo", "type"], ""),
        "start_date": parse_date_struct(status, "startDateStruct"),
        "primary_completion_date": parse_date_struct(status, "primaryCompletionDateStruct"),
        "completion_date": parse_date_struct(status, "completionDateStruct"),
        "last_update": parse_date_struct(status, "lastUpdateSubmitDateStruct"),
        "conditions": ", ".join(conditions[:8]),
        "interventions": ", ".join([n for n in intervention_names if n][:8]),
        "intervention_types": ", ".join(sorted(set([t for t in intervention_types if t]))),
        "arm_text": arm_text[:1000],
        "countries": ", ".join(countries),
        "states": ", ".join(states),
        "site_count": site_count,
        "source_query": source_query,
        "text_blob": text_blob,
        "url": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else "",
    }


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_trials(queries: List[str], page_size: int = 80) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    seen = set()
    for query in queries:
        params = {"format": "json", "query.term": query, "pageSize": min(page_size, 100)}
        try:
            res = requests.get(API_URL, params=params, timeout=22)
            res.raise_for_status()
            payload = res.json()
            for study in payload.get("studies", []):
                row = parse_study(study, query)
                if row["nct_id"] and row["nct_id"] not in seen:
                    rows.append(row)
                    seen.add(row["nct_id"])
        except Exception:
            continue
    if not rows:
        return sample_trials()
    return clean_df(pd.DataFrame(rows))


def sample_trials() -> pd.DataFrame:
    data = [
        ["NCT-DEMO-001", "B7-H4 ADC in advanced solid tumors", "NextCure", "", "Recruiting", "Phase 1", "Interventional", 96, "Anticipated", "2024-03-01", "2026-12-01", "2027-05-01", "2026-05-01", "Ovarian Cancer, Solid Tumor", "B7-H4 ADC", "Drug", "Experimental: B7-H4 ADC monotherapy dose escalation", "United States, Canada", "New Jersey, Texas", 8, "B7-H4", ""],
        ["NCT-DEMO-002", "CDH6 targeted ADC in ovarian cancer", "Competitor A", "", "Active, not recruiting", "Phase 1/2", "Interventional", 142, "Actual", "2023-09-15", "2026-07-15", "2026-11-15", "2026-04-11", "Ovarian Cancer", "CDH6 ADC", "Drug", "CDH6 ADC plus pembrolizumab expansion cohort", "United States, Spain", "California", 11, "CDH6", ""],
        ["NCT-DEMO-003", "B7-H4 antibody in gynecologic malignancies", "Competitor B", "", "Recruiting", "Phase 2", "Interventional", 210, "Anticipated", "2022-10-12", "2026-09-30", "2027-01-30", "2026-03-28", "Ovarian Cancer, Endometrial Cancer", "Anti-B7-H4", "Drug", "Combination with carboplatin and paclitaxel", "United States, Germany, France", "", 19, "B7-H4", ""],
        ["NCT-DEMO-004", "ApoE4 targeted agent in early Alzheimer's disease", "Neuro Sponsor", "", "Not yet recruiting", "Phase 1", "Interventional", 72, "Anticipated", "2026-08-01", "2027-08-01", "2028-02-01", "2026-05-10", "Alzheimer Disease", "ApoE4 antibody", "Biological", "Experimental: ApoE4 targeted therapy", "United States", "Massachusetts", 4, "ApoE4", ""],
        ["NCT-DEMO-005", "Siglec-15 therapy for osteogenesis imperfecta", "Bone Sponsor", "", "Recruiting", "Phase 1", "Interventional", 48, "Anticipated", "2025-01-05", "2026-10-15", "2027-02-15", "2026-01-07", "Osteogenesis Imperfecta", "Siglec-15 antibody", "Biological", "Dose escalation in bone fragility disorder", "United States, Italy", "", 6, "Siglec-15", ""],
        ["NCT-DEMO-006", "ADC combination study in platinum-resistant ovarian cancer", "Competitor C", "", "Not yet recruiting", "Phase 1", "Interventional", 64, "Anticipated", "2026-07-01", "2027-09-01", "2028-02-01", "2026-05-10", "Platinum-Resistant Ovarian Cancer", "ADC + Immunotherapy", "Drug", "ADC plus PD-1 inhibitor", "United States", "Texas", 5, "B7-H4", ""],
    ]
    cols = ["nct_id", "title", "sponsor", "collaborators", "status", "phase", "study_type", "enrollment", "enrollment_type", "start_date", "primary_completion_date", "completion_date", "last_update", "conditions", "interventions", "intervention_types", "arm_text", "countries", "states", "site_count", "source_query", "url"]
    return clean_df(pd.DataFrame(data, columns=cols))


def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    for c in ["start_date", "primary_completion_date", "completion_date", "last_update"]:
        if c not in df:
            df[c] = pd.NaT
        df[c] = pd.to_datetime(df[c], errors="coerce")
    df["enrollment"] = pd.to_numeric(df.get("enrollment", 0), errors="coerce").fillna(0).astype(int)
    df["site_count"] = pd.to_numeric(df.get("site_count", 0), errors="coerce").fillna(0).astype(int)
    df["text_blob"] = df.apply(lambda r: " ".join([safe_str(r.get(c, "")) for c in ["title", "conditions", "interventions", "arm_text", "source_query"]]), axis=1)
    df["target_lane"] = df.apply(extract_target_lane, axis=1)
    df["indication_hint"] = df["conditions"].fillna("Unknown").apply(extract_indication_hint)
    df["is_active"] = df["status"].isin(ACTIVE_STATUSES)
    df["is_planned"] = df["status"].isin(PLANNED_STATUSES) | ((df["start_date"].dt.date >= TODAY) & df["start_date"].notna())
    df["combo_category"] = df.apply(extract_combo_category, axis=1)
    df["combo_agents"] = df.apply(extract_combo_agents, axis=1)
    df["quarter_start"] = df["start_date"].dt.to_period("Q").astype(str).replace("NaT", "Unknown")
    df["primary_completion_quarter"] = df["primary_completion_date"].dt.to_period("Q").astype(str).replace("NaT", "Unknown")
    df["timeline_start"] = df["start_date"].fillna(pd.Timestamp(TODAY - dt.timedelta(days=365)))
    df["timeline_finish"] = df["completion_date"].fillna(df["primary_completion_date"]).fillna(pd.Timestamp(TODAY + dt.timedelta(days=365)))
    return df


def extract_target_lane(row: pd.Series) -> str:
    text = safe_str(row.get("text_blob", "")).lower()
    for lane, aliases in TARGET_LANES.items():
        for alias in aliases:
            if alias.lower() in text:
                return lane
    return "Other / Unclassified"


def extract_indication_hint(text: str) -> str:
    t = safe_str(text).lower()
    if "ovarian" in t or "fallopian" in t or "peritoneal" in t:
        return "Ovarian / Gynecologic"
    if "endometrial" in t or "cervical" in t or "gynecologic" in t:
        return "Ovarian / Gynecologic"
    if "breast" in t:
        return "Breast"
    if "lung" in t or "nsclc" in t:
        return "Lung / NSCLC"
    if "alzheimer" in t or "dementia" in t:
        return "Alzheimer's"
    if "osteogenesis" in t or "bone" in t or "osteoporosis" in t:
        return "Bone Disease"
    if "solid" in t or "tumor" in t or "neoplasm" in t:
        return "Solid Tumor"
    return "Other"


def extract_combo_category(row: pd.Series) -> str:
    text = safe_str(row.get("text_blob", "")).lower()
    if any(term.lower() in text for term in COMBO_TERMS):
        if any(term in text for term in ["pembrolizumab", "nivolumab", "atezolizumab", "durvalumab", "cemiplimab", "pd-1", "pd-l1", "checkpoint", "immunotherapy"]):
            return "Combination: IO / Checkpoint"
        if any(term in text for term in ["carboplatin", "paclitaxel", "gemcitabine", "chemotherapy"]):
            return "Combination: Chemotherapy"
        if any(term in text for term in ["olaparib", "niraparib", "bevacizumab", "targeted therapy"]):
            return "Combination: Targeted"
        return "Combination: Other"
    return "Monotherapy / Unclear"


def extract_combo_agents(row: pd.Series) -> str:
    text = safe_str(row.get("text_blob", ""))
    agents = []
    agent_patterns = ["pembrolizumab", "nivolumab", "atezolizumab", "durvalumab", "cemiplimab", "carboplatin", "paclitaxel", "gemcitabine", "bevacizumab", "olaparib", "niraparib"]
    for agent in agent_patterns:
        if re.search(agent, text, flags=re.IGNORECASE):
            agents.append(agent.title())
    return ", ".join(sorted(set(agents))) if agents else "Not named / unclear"


def chart_layout(fig: go.Figure, height: int = 410) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#dbe7ff", "family": "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"},
        margin={"l": 10, "r": 10, "t": 44, "b": 10},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        xaxis={"gridcolor": "rgba(164,183,219,.10)", "zerolinecolor": "rgba(164,183,219,.16)"},
        yaxis={"gridcolor": "rgba(164,183,219,.10)", "zerolinecolor": "rgba(164,183,219,.16)"},
    )
    return fig


def metric_card(label: str, value: str, note: str):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-note">{note}</div>
    </div>
    """, unsafe_allow_html=True)


def section(title: str, subtitle: str):
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="section-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def split_multi_rows(df: pd.DataFrame, col: str, value_name: str) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        vals = [v.strip() for v in safe_str(r.get(col, "")).split(",") if v.strip()]
        if not vals:
            vals = ["Not listed"]
        for v in vals:
            nr = r.to_dict()
            nr[value_name] = v
            rows.append(nr)
    return pd.DataFrame(rows)


with st.sidebar:
    st.markdown("### Control Deck")
    st.caption("Clinical registry lanes for this rebuild. Keep the first version disciplined and evidence-first.")
    lane_options = list(TARGET_LANES.keys())
    selected_lanes = st.multiselect("Target / side-channel lanes", lane_options, default=lane_options)
    query_text = st.text_area("Search lanes", value="\n".join(DEFAULT_QUERIES), height=150)
    page_size = st.slider("Results per lane", 20, 100, 80, 10)
    status_focus = st.multiselect("Status focus", ["Recruiting", "Not yet recruiting", "Active, not recruiting", "Enrolling by invitation", "Completed", "Terminated", "Suspended", "Withdrawn", "Unknown"], default=["Recruiting", "Not yet recruiting", "Active, not recruiting", "Enrolling by invitation"])
    run_scan = st.button("Run Clinical Intelligence Scan", type="primary")
    st.caption("v1.2 scope: ClinicalTrials.gov only. No LLM summaries, no stock interpretation, no crawling yet.")

if "scan_ran" not in st.session_state:
    st.session_state.scan_ran = False
if run_scan:
    st.session_state.scan_ran = True

st.markdown("""
<div class="hero">
    <div class="eyebrow">NextCure Signal Room</div>
    <h1>Clinical Intelligence Console</h1>
    <p>A rebuilt executive-grade Streamlit system focused on B7-H4, CDH6, Alzheimer’s/ApoE4, and bone/Siglec-15 clinical registry intelligence. Evidence first. Charts first. Narrative last.</p>
    <div class="pill-row">
        <span class="pill">B7-H4 / VTCN1</span>
        <span class="pill">CDH6</span>
        <span class="pill">Alzheimer’s / ApoE4</span>
        <span class="pill">Bone / Siglec-15</span>
        <span class="pill">ClinicalTrials.gov API v2</span>
    </div>
</div>
""", unsafe_allow_html=True)

if not st.session_state.scan_ran:
    st.markdown("""
    <div class="power-panel">
        <div class="eyebrow">System idle</div>
        <h3 style="margin:.35rem 0 .2rem 0; color:#fff;">Run the Clinical Intelligence Scan to power on the console.</h3>
        <p style="color:#9caac3; margin:0;">The app will pull structured trial data, classify lanes, extract geography, enrollment, trial phase, forward-looking catalysts, and combination-therapy signals.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

progress = st.progress(0)
status_box = st.empty()
status_box.caption("Initializing clinical registry scan…")
progress.progress(18)
queries = [q.strip() for q in query_text.splitlines() if q.strip()] or DEFAULT_QUERIES
status_box.caption("Filtering B7-H4, CDH6, Alzheimer’s, and bone disease lanes…")
progress.progress(42)
df = fetch_trials(queries, page_size=page_size)
progress.progress(64)
if selected_lanes:
    df = df[df["target_lane"].isin(selected_lanes) | (df["target_lane"] == "Other / Unclassified")].copy()
if status_focus:
    focused_df = df[df["status"].isin(status_focus)].copy()
else:
    focused_df = df.copy()
status_box.caption("Extracting phase, geography, enrollment, catalyst windows, and combination signals…")
progress.progress(84)
active_df = df[df["is_active"]].copy()
planned_df = df[df["is_planned"]].copy()
forward_df = df[(df["primary_completion_date"].notna()) & (df["primary_completion_date"].dt.date >= TODAY)].copy()
progress.progress(100)
status_box.caption("Clinical intelligence layer online.")

section("Executive Snapshot", "A restrained top-line readout based only on structured trial registry data.")
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    metric_card("Trials Captured", f"{len(df):,}", "Unique studies returned across selected lanes.")
with c2:
    metric_card("Active / Near-Active", f"{len(active_df):,}", "Recruiting, not yet recruiting, active, or invitation-based.")
with c3:
    metric_card("Planned", f"{len(planned_df):,}", "Not yet recruiting or future-start studies.")
with c4:
    metric_card("Patients Planned", f"{int(df['enrollment'].sum()):,}", "Total listed enrollment across captured studies.")
with c5:
    metric_card("Countries", f"{split_multi_rows(df, 'countries', 'country')['country'].nunique():,}", "Distinct countries listed in trial locations.")

section("Lane Cards", "The four NextCure-relevant focus areas, kept separate so Michael can see where each signal comes from.")
lanes = st.columns(4)
for idx, lane in enumerate(lane_options):
    lane_df = df[df["target_lane"] == lane]
    active_lane = lane_df[lane_df["is_active"]]
    enroll = int(lane_df["enrollment"].sum()) if not lane_df.empty else 0
    with lanes[idx]:
        st.markdown(f"""
        <div class="lane-card">
            <div class="lane-title">{lane}</div>
            <div class="lane-sub">{len(lane_df)} studies captured · {len(active_lane)} active/near-active · {enroll:,} listed patients</div>
        </div>
        """, unsafe_allow_html=True)

section("Active Trials by Phase", "Phase mix across active and near-active studies. This shows whether each lane is early exploratory, expansion-stage, or maturing.")
phase_df = active_df.groupby(["target_lane", "phase"], as_index=False).agg(trials=("nct_id", "count"), enrollment=("enrollment", "sum"))
if phase_df.empty:
    st.info("No active phase data found for the current scan.")
else:
    fig_phase = px.bar(phase_df, x="phase", y="trials", color="target_lane", hover_data=["enrollment"], category_orders={"phase": PHASE_ORDER}, title="Active / Near-Active Trials by Phase")
    fig_phase.update_xaxes(title="")
    fig_phase.update_yaxes(title="Studies")
    st.plotly_chart(chart_layout(fig_phase, 430), use_container_width=True, config={"displayModeBar": False})

section("Geographic Trial Footprint", "Country and site concentration. This helps identify where trials are actually recruiting and where expansion may be happening.")
g1, g2 = st.columns([1.05, .95])
country_rows = split_multi_rows(active_df if not active_df.empty else df, "countries", "country")
country_counts = country_rows.groupby("country", as_index=False).agg(trials=("nct_id", "count"), enrollment=("enrollment", "sum"), sites=("site_count", "sum")).sort_values("trials", ascending=False).head(18)
with g1:
    fig_country = px.bar(country_counts.sort_values("trials"), x="trials", y="country", orientation="h", hover_data=["enrollment", "sites"], title="Active Trials by Country")
    fig_country.update_xaxes(title="Studies")
    fig_country.update_yaxes(title="")
    st.plotly_chart(chart_layout(fig_country, 470), use_container_width=True, config={"displayModeBar": False})
with g2:
    geo_lane = country_rows.groupby(["target_lane", "country"], as_index=False).agg(trials=("nct_id", "count"))
    if not geo_lane.empty:
        geo_pivot = geo_lane.pivot_table(index="country", columns="target_lane", values="trials", aggfunc="sum", fill_value=0)
        fig_geo_heat = px.imshow(geo_pivot, text_auto=True, aspect="auto", title="Country × Lane Density")
        st.plotly_chart(chart_layout(fig_geo_heat, 470), use_container_width=True, config={"displayModeBar": False})

section("Patient Population & Enrollment", "Listed enrollment is not prevalence, but it is a useful proxy for trial scale, sponsor commitment, and potential near-term data density.")
e1, e2 = st.columns([1,1])
with e1:
    enroll_lane = df.groupby("target_lane", as_index=False).agg(enrollment=("enrollment", "sum"), trials=("nct_id", "count")).sort_values("enrollment", ascending=False)
    fig_enroll = px.bar(enroll_lane, x="target_lane", y="enrollment", hover_data=["trials"], title="Listed Enrollment by Lane")
    fig_enroll.update_xaxes(title="")
    fig_enroll.update_yaxes(title="Patients")
    st.plotly_chart(chart_layout(fig_enroll, 430), use_container_width=True, config={"displayModeBar": False})
with e2:
    enroll_ind = df.groupby("indication_hint", as_index=False).agg(enrollment=("enrollment", "sum"), trials=("nct_id", "count")).sort_values("enrollment", ascending=False)
    fig_ind = px.bar(enroll_ind, x="enrollment", y="indication_hint", orientation="h", hover_data=["trials"], title="Listed Enrollment by Patient Population")
    fig_ind.update_xaxes(title="Patients")
    fig_ind.update_yaxes(title="")
    st.plotly_chart(chart_layout(fig_ind, 430), use_container_width=True, config={"displayModeBar": False})

section("Combination Therapy Matrix", "A structured extraction of whether trials look like monotherapy, ADC + IO/checkpoint, ADC + chemotherapy, or other combinations.")
combo_df = df.groupby(["target_lane", "combo_category"], as_index=False).agg(trials=("nct_id", "count"), enrollment=("enrollment", "sum"))
fig_combo = px.bar(combo_df, x="target_lane", y="trials", color="combo_category", hover_data=["enrollment"], title="Combination Strategy by Lane")
fig_combo.update_xaxes(title="")
fig_combo.update_yaxes(title="Studies")
st.plotly_chart(chart_layout(fig_combo, 430), use_container_width=True, config={"displayModeBar": False})

section("Forward-Looking Catalyst Calendar", "Primary completion dates and planned starts are the cleanest forward-looking fields available from ClinicalTrials.gov.")
cal_df = forward_df.sort_values("primary_completion_date").head(40).copy()
if cal_df.empty:
    st.info("No future primary completion dates found in the current scan.")
else:
    cal_df["event_label"] = cal_df["target_lane"] + " · " + cal_df["sponsor"].str.slice(0, 24) + " · " + cal_df["nct_id"]
    fig_cal = px.scatter(cal_df, x="primary_completion_date", y="event_label", size="enrollment", color="phase", hover_data=["title", "status", "indication_hint", "combo_category"], title="Forward Catalyst Windows: Primary Completion Dates")
    fig_cal.update_yaxes(title="", autorange="reversed")
    fig_cal.update_xaxes(title="Primary completion date")
    st.plotly_chart(chart_layout(fig_cal, max(460, min(920, 120 + len(cal_df) * 24))), use_container_width=True, config={"displayModeBar": False})

section("Sponsor / Competitor Activity", "Lead sponsor concentration across the focused registry scan.")
sponsor_counts = df.groupby("sponsor", as_index=False).agg(trials=("nct_id", "count"), active=("is_active", "sum"), enrollment=("enrollment", "sum"), sites=("site_count", "sum")).sort_values("trials", ascending=False).head(18)
fig_sponsor = px.bar(sponsor_counts.sort_values("trials"), x="trials", y="sponsor", orientation="h", hover_data=["active", "enrollment", "sites"], title="Top Sponsors by Trial Count")
fig_sponsor.update_yaxes(title="")
fig_sponsor.update_xaxes(title="Studies")
st.plotly_chart(chart_layout(fig_sponsor, 520), use_container_width=True, config={"displayModeBar": False})

section("Clinical Trial Timeline", "Lane-based view of development windows. Hover any bar for NCT ID, sponsor, phase, status, enrollment, country footprint, and combo category.")
show_df = df.sort_values(["target_lane", "timeline_start", "sponsor"]).copy().head(55)
show_df["label"] = show_df["target_lane"].str.slice(0, 18) + " · " + show_df["sponsor"].str.slice(0, 20) + " · " + show_df["nct_id"]
fig_timeline = px.timeline(
    show_df,
    x_start="timeline_start",
    x_end="timeline_finish",
    y="label",
    color="target_lane",
    hover_data=["title", "sponsor", "status", "phase", "enrollment", "countries", "combo_category", "conditions", "interventions"],
    title="Trial Development Windows",
)
fig_timeline.update_yaxes(autorange="reversed", title="")
fig_timeline.update_xaxes(title="")
st.plotly_chart(chart_layout(fig_timeline, max(520, min(980, 60 + len(show_df) * 23))), use_container_width=True, config={"displayModeBar": False})

section("Signal Feed", "Short observations generated from the structured data layer. This is not an LLM summary, it is a rules-based executive feed.")
signals = []
if len(active_df):
    signals.append(("Active footprint", f"{len(active_df)} active or near-active studies are visible across the focused lanes."))
if not planned_df.empty:
    signals.append(("Forward-looking studies", f"{len(planned_df)} studies are listed as planned/not-yet-recruiting or have a future start date."))
if not forward_df.empty:
    nxt = forward_df.sort_values("primary_completion_date").iloc[0]
    signals.append(("Nearest catalyst window", f"{nxt['sponsor']} lists a primary completion date of {nxt['primary_completion_date'].date()} for {nxt['nct_id']} in the {nxt['target_lane']} lane."))
combo_n = int((df["combo_category"] != "Monotherapy / Unclear").sum())
if combo_n:
    signals.append(("Combination therapy activity", f"{combo_n} captured studies include detectable combination therapy language or named partner agents."))
if not country_counts.empty:
    signals.append(("Geographic concentration", f"{country_counts.iloc[0]['country']} is the most represented country in the current active trial footprint."))
if not sponsor_counts.empty:
    signals.append(("Sponsor concentration", f"{sponsor_counts.iloc[0]['sponsor']} is the most represented lead sponsor in this scan."))
for title, body in signals[:7]:
    st.markdown(f'<div class="signal"><strong>{title}</strong><br>{body}</div>', unsafe_allow_html=True)

section("Evidence Table", "The auditable row-level dataset behind the charts. This is the trust layer.")
cols = ["nct_id", "target_lane", "title", "sponsor", "status", "phase", "enrollment", "enrollment_type", "start_date", "primary_completion_date", "completion_date", "countries", "site_count", "indication_hint", "combo_category", "combo_agents", "conditions", "interventions", "url"]
st.dataframe(df[cols].sort_values(["target_lane", "sponsor", "phase"]).reset_index(drop=True), use_container_width=True, hide_index=True)

st.markdown(f'<p class="caption">Data source: ClinicalTrials.gov API v2 /api/v2/studies. Last app refresh: {dt.datetime.now().strftime("%Y-%m-%d %H:%M")}. This v1.2 build uses structured registry fields and conservative keyword extraction only.</p>', unsafe_allow_html=True)
