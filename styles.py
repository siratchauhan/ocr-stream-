APP_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif !important;
        color: #1a1a2e;
    }
    .stApp {
        background: #f5f6fa !important;
        color: #1a1a2e;
    }
    h1,h2,h3 { font-family:'DM Sans',sans-serif !important; font-weight:700; color:#1a1a2e; }

    .ocr-header {
        background: #ffffff;
        border: 1px solid #e8eaf0;
        border-radius: 16px;
        padding: 22px 28px;
        margin-bottom: 18px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .ocr-header h1 { font-size:1.5rem; margin:0; color:#1a1a2e; letter-spacing:-0.3px; }
    .ocr-header p  { margin:4px 0 0; color:#374151; font-size:0.82rem; font-family:'DM Mono',monospace; line-height:1.5; }

    .panel-card {
        background: #ffffff;
        border: 1px solid #e8eaf0;
        border-radius: 14px;
        padding: 18px;
        box-shadow: 0 1px 6px rgba(0,0,0,0.04);
        height: 100%;
    }
    .info-card {
        background: #ffffff;
        border: 1px solid #e8eaf0;
        border-radius: 12px;
        padding: 16px 18px;
        margin-bottom: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .info-card.accent { border-left: 3px solid #6366f1; }
    .info-card.green  { border-left: 3px solid #10b981; }
    .info-card.blue   { border-left: 3px solid #3b82f6; }

    .section-label {
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        color: #4b5563;
        margin: 14px 0 6px;
    }

    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
    }
    .badge-aadhaar { background:#ecfdf5; color:#059669; border:1px solid #a7f3d0; }
    .badge-pan     { background:#eff6ff; color:#4f46e5; border:1px solid #bfdbfe; }
    .badge-unknown { background:#fef2f2; color:#dc2626; border:1px solid #fecaca; }
    .badge-normal  { background:#eff6ff; color:#3b82f6; border:1px solid #bfdbfe; }
    .badge-dl      { background:#f0fdf4; color:#16a34a; border:1px solid #bbf7d0; }
    .badge-voter   { background:#faf5ff; color:#7c3aed; border:1px solid #ddd6fe; }

    .kv-table { width:100%; border-collapse:collapse; font-family:'DM Mono',monospace; font-size:0.8rem; }
    .kv-table th {
        text-align:left; padding:8px 12px;
        background:#f5f6fa; color:#6366f1;
        font-weight:600; font-size:0.7rem; letter-spacing:1px; text-transform:uppercase;
        border-bottom:1px solid #e8eaf0;
    }
    .kv-table td { padding:8px 12px; border-bottom:1px solid #f0f1f5; color:#374151; vertical-align:top; }
    .kv-table td:first-child { color:#6b7280; width:38%; font-weight:500; }
    .kv-table tr:hover td { background:#fafbff; }

    .photo-card {
        background:#f9fafb; border:1px solid #e8eaf0; border-radius:10px;
        padding:12px; display:flex; align-items:center; gap:12px; margin-bottom:12px;
    }
    .photo-frame {
        width:48px; height:58px; border-radius:8px; border:1.5px solid #e8eaf0;
        background:#e8eaf0; display:flex; align-items:center; justify-content:center;
        font-size:1.3rem; flex-shrink:0; overflow:hidden;
    }
    .photo-frame img { width:100%; height:100%; object-fit:cover; }
    .photo-placeholder {
        width:48px; height:58px; border-radius:8px; border:2px dashed #d1d5db;
        background:#f9fafb; display:flex; flex-direction:column; align-items:center;
        justify-content:center; font-size:0.6rem; color:#9ca3af;
        font-family:'DM Mono',monospace; text-align:center; flex-shrink:0;
    }
    .photo-meta { flex:1; }
    .photo-label { font-size:0.62rem; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:#9ca3af; margin-bottom:3px; }
    .photo-name  { font-size:0.95rem; font-weight:700; color:#1a1a2e; margin-bottom:2px; }
    .photo-sub   { font-size:0.72rem; color:#4b5563; font-family:'DM Mono',monospace; line-height:1.5; }

    .conf-wrap { display:flex; align-items:center; gap:10px; margin:10px 0; }
    .conf-label { font-size:0.72rem; font-family:'DM Mono',monospace; color:#4b5563; min-width:72px; }
    .conf-bg { flex:1; background:#e8eaf0; border-radius:4px; height:6px; overflow:hidden; }
    .conf-fill { height:100%; border-radius:4px; }
    .conf-high { background:#10b981; }
    .conf-mid  { background:#f59e0b; }
    .conf-low  { background:#ef4444; }
    .conf-pct  { font-size:0.72rem; font-family:'DM Mono',monospace; color:#374151; min-width:32px; text-align:right; }

    .empty-state {
        display:flex; flex-direction:column; align-items:center; justify-content:center;
        text-align:center; padding:48px 20px; color:#9ca3af;
    }
    .empty-icon { font-size:2.5rem; opacity:0.35; margin-bottom:12px; }
    .empty-title { font-weight:600; font-size:0.9rem; margin-bottom:4px; }
    .empty-sub { font-size:0.76rem; font-family:'DM Mono',monospace; }

    .fail-log { background:#fff9f9; border:1px solid #fecaca; border-radius:12px; padding:16px; margin-top:12px; }
    .fail-log-title { color:#dc2626; font-weight:700; font-size:0.78rem; letter-spacing:1px; text-transform:uppercase; margin-bottom:10px; }
    .fail-entry { font-family:'DM Mono',monospace; font-size:0.76rem; color:#6b7280; padding:5px 0; border-bottom:1px solid #fee2e2; display:flex; gap:10px; flex-wrap:wrap; }
    .fail-entry:last-child { border-bottom:none; }
    .fail-ts  { color:#9ca3af; flex-shrink:0; }
    .fail-msg { color:#dc2626; }

    .stButton > button {
        background: linear-gradient(135deg,#4f46e5,#6366f1) !important;
        color: white !important; border: none !important;
        border-radius: 10px !important; padding: 10px 20px !important;
        font-family: 'DM Sans',sans-serif !important; font-weight: 600 !important;
        box-shadow: 0 2px 8px rgba(99,102,241,0.3) !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        opacity: 0.9 !important;
        box-shadow: 0 4px 14px rgba(99,102,241,0.4) !important;
        transform: translateY(-1px) !important;
    }

    .sec-btn > button {
        background: #ffffff !important; color: #4f46e5 !important;
        border: 1.5px solid #c7d2fe !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
    }
    .sec-btn > button:hover { background: #eef2ff !important; }

    .stDownloadButton > button {
        background: #ffffff !important; color: #4f46e5 !important;
        border: 1px solid #c7d2fe !important; border-radius: 8px !important;
        font-family: 'DM Sans',sans-serif !important; font-weight: 600 !important;
        box-shadow: none !important;
    }
    .stDownloadButton > button:hover { background: #eef2ff !important; border-color: #a5b4fc !important; }

    .stSelectbox > div > div {
        background: #ffffff !important; border: 1px solid #e8eaf0 !important;
        border-radius: 8px !important; color: #374151 !important;
        font-family: 'DM Sans',sans-serif !important;
    }
    [data-testid="stTextInputRootElement"] input {
        background: #eef2f7 !important;
        color: #0f172a !important;
        border: 1px solid #bcc7d8 !important;
        border-radius: 10px !important;
    }
    [data-testid="stTextInputRootElement"] input::placeholder {
        color: #64748b !important;
        opacity: 1 !important;
    }
    [data-testid="stTextInputRootElement"] input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 0 1px #6366f1 inset !important;
    }
    [data-testid="stWidgetLabel"] p {
        color: #111827 !important;
        font-weight: 600 !important;
    }
    .stTextArea textarea {
        background: #eef2f7 !important; color: #111827 !important;
        border: 1px solid #bcc7d8 !important; border-radius: 8px !important;
        font-family: 'DM Mono',monospace !important; font-size: 0.8rem !important;
    }

    [data-testid="stFileUploader"] {
        background: #fafbff !important; border: 2px dashed #c7d2fe !important;
        border-radius: 10px !important;
    }
    [data-testid="stFileUploader"]:hover { border-color: #6366f1 !important; }

    .stTabs [data-baseweb="tab-list"] {
        background: #e9edf4 !important; border-radius: 10px !important;
        padding: 4px !important; gap: 4px !important; border: 1px solid #cdd6e3 !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important; color: #374151 !important;
        border-radius: 7px !important; font-family: 'DM Sans',sans-serif !important;
        font-weight: 600 !important; padding: 7px 14px !important; border: none !important;
    }
    .stTabs [aria-selected="true"] {
        background: #ffffff !important; color: #111827 !important;
        font-weight: 700 !important; box-shadow: 0 1px 4px rgba(0,0,0,0.12) !important;
    }

    [data-testid="stExpander"] {
        background: #ffffff !important; border: 1px solid #e8eaf0 !important;
        border-radius: 10px !important; box-shadow: 0 1px 4px rgba(0,0,0,0.04) !important;
        margin-bottom: 8px !important;
    }
    [data-testid="stExpander"] summary {
        color: #374151 !important; font-weight: 600 !important;
        font-family: 'DM Sans',sans-serif !important; padding: 12px 16px !important;
    }

    [data-testid="stAlert"]   { border-radius: 10px !important; font-family:'DM Sans',sans-serif !important; }
    [data-testid="stInfo"]    { background:#eff6ff !important; border-color:#bfdbfe !important; color:#1e40af !important; }
    [data-testid="stWarning"] { background:#fffbeb !important; border-color:#fcd34d !important; }
    [data-testid="stSuccess"] { background:#ecfdf5 !important; border-color:#a7f3d0 !important; }

    [data-testid="stCameraInput"] {
        border:2px dashed #c7d2fe !important;
        border-radius:12px !important;
        background:#fafbff !important;
    }

    hr { border-color:#e8eaf0 !important; margin:16px 0 !important; }
    [data-testid="stCaptionContainer"] p { color:#4b5563 !important; font-family:'DM Mono',monospace !important; font-size:0.76rem !important; }
    .stSpinner > div { border-top-color:#6366f1 !important; }

    .vdivider {
        width: 1px; background: #e8eaf0; margin: 0 4px; border-radius: 2px;
        min-height: 400px;
    }

    @media (max-width:768px) {
        .photo-card { flex-direction:column; align-items:center; text-align:center; }
        .kv-table td, .kv-table th { padding:6px 8px; font-size:0.74rem; }
    }
</style>
"""

SIDEBAR_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=DM+Mono:wght@400;500&display=swap');

[data-testid="stSidebar"][aria-expanded="true"] {
    background: #ffffff !important;
    border-right: 1px solid #e8eaf0 !important;
    width: 280px !important;
    min-width: 280px !important;
    max-width: 280px !important;
    box-shadow: 2px 0 12px rgba(0,0,0,0.06) !important;
    padding-top: 0 !important;
}
[data-testid="stSidebar"][aria-expanded="false"] {
    min-width: 0 !important;
    width: 0 !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
    padding-left: 16px !important;
    padding-right: 16px !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] {
    background: #f9fafb !important;
    border: 1px solid #e8eaf0 !important;
    border-radius: 10px !important;
    margin-bottom: 6px !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary {
    font-size: 0.77rem !important;
    color: #374151 !important;
    padding: 8px 12px !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {
    background: #f0f4ff !important;
    border-radius: 8px !important;
}
.sb-header {
    font-size: 0.62rem;
    font-weight: 800;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    color: #6366f1;
    margin: 14px 0 8px;
    padding-bottom: 5px;
    border-bottom: 2px solid #e8eaf0;
}
.sb-record-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 20px;
    font-size: 0.62rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-right: 4px;
}
.sb-badge-aadhaar { background:#ecfdf5; color:#059669; border:1px solid #a7f3d0; }
.sb-badge-pan     { background:#eff6ff; color:#4f46e5; border:1px solid #c7d2fe; }
.sb-badge-dl      { background:#f0fdf4; color:#16a34a; border:1px solid #bbf7d0; }
.sb-badge-voter   { background:#faf5ff; color:#7c3aed; border:1px solid #ddd6fe; }
.sb-badge-other   { background:#f3f4f6; color:#6b7280; border:1px solid #e5e7eb; }
.sb-kv { font-family:'DM Mono',monospace; font-size:0.7rem; }
.sb-kv-row {
    display: flex;
    gap: 6px;
    padding: 3px 0;
    border-bottom: 1px solid #f0f1f5;
}
.sb-kv-row:last-child { border-bottom: none; }
.sb-key { color: #9ca3af; min-width: 82px; flex-shrink: 0; font-weight: 600; }
.sb-val { color: #1a1a2e; word-break: break-all; }
.sb-ts {
    font-size: 0.6rem;
    color: #9ca3af;
    font-family: 'DM Mono', monospace;
    margin-bottom: 5px;
    display: block;
}
.fail-entry-sb {
    font-family: 'DM Mono', monospace;
    font-size: 0.67rem;
    padding: 5px 0;
    border-bottom: 1px solid #fee2e2;
    display: flex;
    flex-direction: column;
    gap: 2px;
}
.fail-entry-sb:last-child { border-bottom: none; }
.fail-ts-sb  { color: #9ca3af; }
.fail-ctx-sb { color: #6366f1; font-weight: 700; }
.fail-msg-sb { color: #dc2626; }
[data-testid="stSidebar"] .stButton > button {
    background: #f8faff !important;
    color: #4f46e5 !important;
    border: 1px solid #c7d2fe !important;
    box-shadow: none !important;
    font-size: 0.78rem !important;
    padding: 5px 10px !important;
    border-radius: 8px !important;
    transform: none !important;
    transition: background 0.15s !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #eef2ff !important;
    transform: none !important;
    box-shadow: none !important;
}
.logout-btn > button {
    background: #fff1f2 !important;
    color: #dc2626 !important;
    border: 1px solid #fecaca !important;
}
[data-testid="stSidebar"] .logout-btn > button:hover {
    background: #fee2e2 !important;
}
[data-testid="stSidebar"] [data-testid="stTextInputRootElement"] input {
    font-size: 0.78rem !important;
    padding: 6px 10px !important;
    border-radius: 8px !important;
    background: #f5f6fa !important;
    border: 1px solid #e8eaf0 !important;
}
[data-testid="stSidebar"] [data-testid="stTextInputRootElement"] input:focus {
    border-color: #6366f1 !important;
    background: #ffffff !important;
    box-shadow: 0 0 0 2px rgba(99,102,241,0.12) !important;
}
</style>
"""
