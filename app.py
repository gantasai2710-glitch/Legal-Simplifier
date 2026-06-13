import time
import html
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
import torch
from dotenv import load_dotenv
load_dotenv()

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="Legal Text Simplifier",
    page_icon="⚖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── PDF extractor (cached by bytes) ──────────────────────────────────────────
@st.cache_data(show_spinner=False)
def extract_pdf_text(file_bytes: bytes):
    import fitz  # PyMuPDF
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = "\n".join([page.get_text() for page in doc])
    return text, len(doc)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=Playfair+Display:ital@1&display=swap');

:root {
    --bg:      #0a0c10;
    --surface: #111318;
    --border:  #1e2128;
    --blue:    #4f8ef7;
    --amber:   #f59e0b;
    --green:   #22c55e;
    --purple:  #a78bfa;
    --text:    #f0f2f7;
    --muted:   #6b7280;
    --ghost:   #2a2d35;
}

/* Hide Streamlit chrome */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
[data-testid="stStatusWidget"]  {display: none !important;}
[data-testid="stBottom"]        {display: none !important;}

section[data-testid="stMain"] .block-container {
    max-width: 780px !important;
    padding: 0 24px 80px 24px !important;
    margin: 0 auto !important;
}

html, body, .stApp {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: "IBM Plex Sans", sans-serif !important;
}

/* Textarea */
.stTextArea textarea {
    background-color: var(--surface) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    font-family: "IBM Plex Sans", sans-serif !important;
    font-size: 14px !important;
    resize: vertical;
}
.stTextArea textarea:focus {
    border-color: var(--blue) !important;
    box-shadow: 0 0 0 2px rgba(79,142,247,0.15) !important;
    outline: none;
}
.stTextArea label {
    color: var(--text) !important;
    font-size: 12px !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    font-weight: 500 !important;
}

/* File uploader */
[data-testid="stFileUploaderDropzone"] {
    background-color: var(--surface) !important;
    border: 1px dashed #2a2d35 !important;
    border-radius: 12px !important;
    max-width: 400px !important;
    margin: 0 auto !important;
}
[data-testid="stFileUploaderDropzone"]:hover {
    border-color: var(--blue) !important;
}
[data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {
    display: none !important;
}
[data-testid="stFileUploader"] label {
    color: var(--muted) !important;
    font-size: 12px !important;
    letter-spacing: 1.5px !important;
    text-transform: uppercase !important;
    width: 100%;
    text-align: center;
    display: block;
}

/* Primary button */
div.stButton > button[kind="primary"] {
    height: 52px !important;
    background-color: var(--blue) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-size: 15px !important;
    font-weight: 500 !important;
    width: 100% !important;
    transition: background-color 0.2s, transform 0.15s;
}
div.stButton > button[kind="primary"]:hover {
    background-color: #3a7de0 !important;
    transform: translateY(-1px) !important;
}
div.stButton > button[kind="primary"]:disabled {
    background-color: #1e2a40 !important;
    color: var(--muted) !important;
    cursor: not-allowed !important;
    transform: none !important;
}

/* Secondary button */
div.stButton > button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid var(--border) !important;
    color: var(--muted) !important;
    border-radius: 8px !important;
    transition: color 0.2s, border-color 0.2s;
}
div.stButton > button[kind="secondary"]:hover {
    color: var(--text) !important;
    border-color: var(--text) !important;
}

/* Warning / alert */
.stAlert {
    background-color: #1a1500 !important;
    border: 1px solid #f59e0b44 !important;
    border-radius: 8px !important;
}

/* Divider */
hr { border-color: var(--border) !important; }
</style>
""", unsafe_allow_html=True)


# ── Session state defaults ────────────────────────────────────────────────────
defaults = {
    "input_text": "",
    "file_info": None,
    "last_uploaded": None,
    "processing": False,
    "results": None,
    "kw_expanded": False,
    "simplified_expanded": False,
    "summary_expanded": False,
    "models_ready": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── Hero banner (full width) ──────────────────────────────────────────────────
st.markdown("""
<div style="
    width:100%;
    background:linear-gradient(135deg, #0d1117 0%, #111827 100%);
    border-bottom:1px solid #1e2128;
    padding:40px 60px 32px 60px;
    display:flex;align-items:center;
    box-sizing:border-box;
    margin-bottom:32px;
">
    <div style="
        width:3px;height:52px;
        background:#4f8ef7;
        margin-right:20px;flex-shrink:0;
    "></div>
    <div>
        <div style="
            font-family:'Playfair Display',serif;
            font-style:italic;font-size:38px;
            color:#f0f2f7;line-height:1.1;
        ">⚖ Legal Text Simplifier</div>
        <div style="
            font-size:12px;color:#6b7280;
            letter-spacing:2px;text-transform:uppercase;
            margin-top:8px;
        ">Decode legal language in plain English</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  INPUT SECTION
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state["results"] is None and not st.session_state["processing"]:

    # Textarea — no `key` so value= always respected after PDF rerun
    input_text = st.text_area(
        "ENTER LEGAL TEXT",
        value=st.session_state["input_text"],
        height=180,
        placeholder="Paste your legal contract, clause, or document here…",
    )
    # Only update session state from the widget when the user is typing
    # (not when content came from a PDF upload on this same rerun)
    if not st.session_state.get("pdf_just_loaded"):
        st.session_state["input_text"] = input_text
    st.session_state["pdf_just_loaded"] = False

    # Word count (right-aligned, shown only when there's input)
    if input_text.strip():
        word_count = len(input_text.split())
        count_color = "#f59e0b" if word_count > 21000 else "#6b7280"
        st.markdown(
            f'<div style="text-align:right;font-size:12px;'
            f'color:{count_color};margin-top:-8px;margin-bottom:4px;">'
            f'{word_count:,} words'
            f'{"  ·  MAX 21,000" if word_count > 21000 else ""}'
            f'</div>',
            unsafe_allow_html=True,
        )
        if word_count > 21000:
            st.warning(
                "⚠️ Input exceeds 21,000 words. "
                "Only the first 21,000 words will be processed.",
                icon=None,
            )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # OR separator
    st.markdown(
        '<div style="text-align:center;font-size:11px;'
        'color:#6b7280;letter-spacing:2px;text-transform:uppercase;'
        'margin-bottom:12px;">OR UPLOAD PDF</div>',
        unsafe_allow_html=True,
    )

    # File uploader (centered)
    uploaded = st.file_uploader(
        "Upload a PDF document",
        type=["pdf"],
        key="pdf_uploader",
        label_visibility="collapsed",
    )

    # Handle upload: extract text once per unique file
    if uploaded is not None:
        file_bytes = uploaded.read()
        file_id = (uploaded.name, len(file_bytes))
        if st.session_state.get("last_uploaded") != file_id:
            with st.spinner("Reading PDF…"):
                pdf_text, num_pages = extract_pdf_text(file_bytes)
            st.session_state["input_text"] = pdf_text
            st.session_state["file_info"] = {
                "name": uploaded.name,
                "pages": num_pages,
                "words": len(pdf_text.split()),
            }
            st.session_state["last_uploaded"] = file_id
            st.session_state["pdf_just_loaded"] = True  # guard textarea overwrite
            st.rerun()

    # File pill (shown after successful upload)
    if st.session_state["file_info"]:
        fi = st.session_state["file_info"]
        safe_name = html.escape(fi["name"])
        st.markdown(
            f'<div style="text-align:center;margin-top:10px;">'
            f'<span style="'
            f'display:inline-block;'
            f'background:#0d1a30;'
            f'border:1px solid #4f8ef744;'
            f'border-radius:999px;'
            f'padding:6px 16px;'
            f'font-size:12px;color:#4f8ef7;'
            f'letter-spacing:0.5px;">'
            f'📄 {safe_name} · {fi["pages"]} page{"s" if fi["pages"]!=1 else ""}'
            f' · {fi["words"]:,} words'
            f'</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # Analyze button (centered, 360px wide via columns)
    active_text = st.session_state["input_text"].strip()
    btn_disabled = len(active_text) < 20
    _, btn_col, _ = st.columns([1, 2, 1])
    with btn_col:
        if st.button(
            "⚡ Analyze Document",
            type="primary",
            disabled=btn_disabled,
            use_container_width=True,
        ):
            st.session_state["processing"] = True
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
#  PROCESSING TRACKER
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state["processing"]:

    tracker_placeholder = st.empty()
    step_times = {}  # track per-step durations

    def render_tracker(step_times: dict = {}):
        elapsed = step_times.get(0)
        time_label = f' ({elapsed:.1f}s)' if elapsed is not None else ''
        lbl = "Analyzing with Gemini AI" + (time_label if elapsed is not None else '…')
        
        tracker_html = (
            '<div style="max-width:480px;margin:0 auto;padding:24px 0">'
            '<div style="background:#1e2128;border-radius:999px;'
            'height:3px;margin-bottom:24px">'
            '<div style="width:100%;height:3px;'
            'border-radius:999px;'
            'background:linear-gradient(90deg,#4f8ef7,#a78bfa);'
            'transition:width 0.4s ease">'
            '</div></div>'
            '<div style="display:flex;justify-content:center">'
            '<div style="display:flex;flex-direction:column;align-items:center;gap:6px;">'
            '<div style="width:10px;height:10px;border-radius:50%;background:#4f8ef7"></div>'
            '<div style="font-size:11px;color:#f0f2f7;font-weight:500;letter-spacing:0.5px">'
            + lbl +
            '</div></div></div></div>'
        )
        tracker_placeholder.markdown(tracker_html, unsafe_allow_html=True)

    try:
        from simplifier import simplify_text

        text_in = st.session_state["input_text"]

        t0 = time.time()
        render_tracker(step_times)
        
        results = simplify_text(text_in)
        
        step_times[0] = time.time() - t0
        render_tracker(step_times)

        if "error" in results:
            st.error(f"**{results['error']}**\n\n{results['message']}")
            st.session_state["processing"] = False
            st.stop()

        st.session_state["results"] = results
        st.session_state["processing"] = False
        st.rerun()

    except Exception as e:
        st.error(f"Processing error: {e}")
        st.session_state["processing"] = False
        # Preserve input so user can retry


# ═══════════════════════════════════════════════════════════════════════════════
#  RESULTS SECTION — UI PANELS
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state["results"] is not None:
    res = st.session_state["results"]

    # ── Top Card: SUMMARY ─────────────────────────────────────────────────────
    st.markdown("### Summary")
    st.markdown(
        f'<div style="'
        f'background:var(--surface);'
        f'border-left:4px solid var(--green);'
        f'border-radius:12px;'
        f'padding:20px 24px;'
        f'margin-bottom:24px;'
        f'color:var(--text);'
        f'font-size:16px;'
        f'line-height:1.6;">'
        f'{html.escape(res.get("summary", ""))}</div>',
        unsafe_allow_html=True,
    )

    # ── Warning Container: KEY RISKS ──────────────────────────────────────────
    risks = res.get("key_risks", [])
    if risks:
        st.markdown("### Key Risks")
        risk_list = "".join([f"<li>{html.escape(r)}</li>" for r in risks])
        st.markdown(
            f'<div style="'
            f'background:#1a1010;'
            f'border:1px solid #ef4444;'
            f'border-radius:12px;'
            f'padding:20px 24px;'
            f'margin-bottom:24px;'
            f'color:#fca5a5;'
            f'font-size:15px;'
            f'line-height:1.6;">'
            f'<ul style="margin:0;padding-left:20px;">{risk_list}</ul></div>',
            unsafe_allow_html=True,
        )

    # ── Split Screen: ORIGINAL vs SIMPLIFIED ──────────────────────────────────
    st.markdown("### Translation")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("<h4 style='color:var(--muted); font-size:14px; text-transform:uppercase;'>Original Legal Text</h4>", unsafe_allow_html=True)
        st.markdown(
            f'<div style="'
            f'background:var(--surface);'
            f'border:1px solid var(--border);'
            f'border-radius:12px;'
            f'padding:20px;'
            f'height:400px;overflow-y:auto;'
            f'color:var(--muted);'
            f'font-size:14px;'
            f'line-height:1.6;">'
            f'{html.escape(st.session_state["input_text"]).replace(chr(10), "<br>")}</div>',
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown("<h4 style='color:var(--blue); font-size:14px; text-transform:uppercase;'>Simplified Plain English</h4>", unsafe_allow_html=True)
        # Use markdown directly inside the div if we have bullet points from simplified text
        st.markdown(
            f'<div style="'
            f'background:var(--surface);'
            f'border:1px solid var(--blue);'
            f'border-radius:12px;'
            f'padding:20px;'
            f'height:400px;overflow-y:auto;'
            f'color:var(--text);'
            f'font-size:14px;'
            f'line-height:1.6;">'
            f'{html.escape(res.get("simplified_text", "")).replace(chr(10), "<br>")}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── Bottom Section: GLOSSARY ──────────────────────────────────────────────
    glossary = res.get("glossary", [])
    if glossary:
        st.markdown("### Glossary")
        st.markdown(
            f'<table style="width:100%; border-collapse:collapse; margin-bottom:24px; font-size:14px;">'
            f'<thead><tr style="border-bottom:1px solid var(--border); text-align:left; color:var(--muted);">'
            f'<th style="padding:12px;">Term</th><th style="padding:12px;">Definition</th></tr></thead>'
            f'<tbody>'
            + "".join([
                f'<tr style="border-bottom:1px solid #1e2128;">'
                f'<td style="padding:12px; color:var(--blue); font-weight:500;">{html.escape(item.get("term", ""))}</td>'
                f'<td style="padding:12px; color:var(--text);">{html.escape(item.get("definition", ""))}</td>'
                f'</tr>'
                for item in glossary
            ]) +
            f'</tbody></table>',
            unsafe_allow_html=True,
        )

    # ── Reset button ──────────────────────────────────────────────────────────
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    _, reset_col, _ = st.columns([1, 2, 1])
    with reset_col:
        if st.button(
            "↺ Analyze Another Document",
            type="secondary",
            use_container_width=True,
        ):
            for key in [
                "results", "input_text", "file_info",
                "last_uploaded"
            ]:
                if key in ["input_text"]:
                    st.session_state[key] = ""
                else:
                    st.session_state[key] = None
            st.rerun()
