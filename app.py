import os
import io
import json
import base64
from datetime import datetime

import streamlit as st

from styles import APP_CSS, SIDEBAR_CSS
from database import (
    get_supabase,
    auth_login,
    auth_signup,
    auth_logout,
    save_extraction,
    load_extractions,
)
from ocr_extraction import (
    set_ocr_context,
    get_file_type,
    detect_blur,
    extract_face_photo,
    perform_ocr,
    detect_doc_type,
    extract_aadhaar_fields,
    extract_pan_fields,
    extract_dl_fields,
    extract_voter_fields,
)
from ui_helpers import render_kv_table, render_confidence_bar, photo_html
from sidebar_ui import render_sidebar


# ================================================================
# 1. PAGE CONFIG
# ================================================================
st.set_page_config(page_title="OCR Stream", page_icon="📝", layout="wide", initial_sidebar_state="expanded")

# ================================================================
# 2. STYLES
# ================================================================
st.markdown(APP_CSS, unsafe_allow_html=True)

# ================================================================
# 3. CONFIG
# ================================================================
OCR_API_KEY = os.getenv("OCR_API_KEY", "")
supabase = get_supabase()

# ================================================================
# 4. SESSION STATE INIT
# ================================================================
for key, default in [
    ("user", None),
    ("access_token", None),
    ("failure_log", []),
    ("ocr_mode", "Normal"),
    ("camera_bytes", None),
    ("camera_fsize", 0),
    ("camera_open", False),
    ("camera_widget_nonce", 0),
    ("last_result", None),
    ("last_login", None),
    ("user_created_at", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ================================================================
# 5. HELPERS
# ================================================================
def log_failure(context: str, message: str):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.failure_log.append({"ts": ts, "ctx": context, "msg": message})


set_ocr_context(api_key=OCR_API_KEY, logger=log_failure)


def render_auth_ui():
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown(
            """
        <div style="text-align:center;margin-bottom:28px;margin-top:40px;">
            <div style="width:52px;height:52px;background:linear-gradient(135deg,#4f46e5,#818cf8);
                border-radius:14px;display:inline-flex;align-items:center;justify-content:center;
                font-size:1.5rem;margin-bottom:14px;box-shadow:0 4px 16px rgba(99,102,241,0.35);">📝</div>
            <h1 style="font-size:1.9rem;font-weight:800;color:#1a1a2e;margin:0 0 6px;">OCR Stream</h1>
            <p style="color:#374151;font-size:0.85rem;margin:0;font-family:'DM Mono',monospace;">
                Sign in to extract &amp; store document data</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        tab_login, tab_signup = st.tabs(["🔐 Login", "✍ Sign Up"])
        with tab_login:
            email = st.text_input("Email", key="login_email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", key="login_pw", placeholder="••••••••")
            if st.button("Login", use_container_width=True, key="btn_login"):
                ok, err = auth_login(supabase, email, password)
                if ok:
                    st.success("Logged in!")
                    st.rerun()
                else:
                    st.error(f"Login failed: {err}")

        with tab_signup:
            email = st.text_input("Email", key="signup_email", placeholder="you@example.com")
            password = st.text_input("Password (min 6 chars)", type="password", key="signup_pw", placeholder="••••••••")
            if st.button("Create Account", use_container_width=True, key="btn_signup"):
                ok, err = auth_signup(supabase, email, password)
                if ok:
                    st.success("Account created! Check your email to confirm, then log in.")
                else:
                    st.error(f"Sign up failed: {err}")


# ================================================================
# 6. AUTH GATE
# ================================================================
if not st.session_state.user:
    render_auth_ui()
    st.stop()

# ================================================================
# 7. USER BAR
# ================================================================
st.markdown(
    f"""<div style="display:flex;align-items:center;
        background:#ffffff;border:1px solid #e8eaf0;border-radius:10px;
        padding:8px 16px;box-shadow:0 1px 4px rgba(0,0,0,0.04);">
        <b style="color:#4f46e5;font-size:0.85rem;">{st.session_state.user.email}</b>
    </div>""",
    unsafe_allow_html=True,
)

# ================================================================
# 8. HEADER
# ================================================================
st.markdown(
    """
<div class="ocr-header">
    <div style="width:44px;height:44px;background:linear-gradient(135deg,#4f46e5,#818cf8);
        border-radius:12px;display:flex;align-items:center;justify-content:center;
        font-size:1.3rem;box-shadow:0 2px 10px rgba(99,102,241,0.3);flex-shrink:0;">📝</div>
    <div>
        <h1>OCR Stream</h1>
        <p>Extract text from images &amp; PDFs · Blur detection · Document-aware key-value extraction for Indian ID documents (Aadhaar, PAN, DL, Voter ID)</p>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# ================================================================
# 9. MODE + SETTINGS
# ================================================================
st.markdown('<div class="section-label">Select Mode</div>', unsafe_allow_html=True)
with st.container(border=True):
    mode = st.session_state.ocr_mode
    mode_label = "Text Extraction" if mode == "Normal" else "Document OCR"
    st.markdown(
        f"<p style='margin:0 0 10px;color:#334155;font-size:0.82rem;font-weight:600;'>Selected Mode: {mode_label}</p>",
        unsafe_allow_html=True,
    )
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if mode == "Normal":
            st.markdown(
                """<div style="background:#0f172a;color:#ffffff;border-radius:10px;padding:10px 12px;
                text-align:center;font-weight:700;border:1px solid #020617;">📄 Text Extraction</div>""",
                unsafe_allow_html=True,
            )
        else:
            if st.button("📄 Text Extraction", use_container_width=True, key="btn_mode_text"):
                st.session_state.ocr_mode = "Normal"
                st.session_state.last_result = None
                st.rerun()
    with col_m2:
        if mode == "Document":
            st.markdown(
                """<div style="background:#0f172a;color:#ffffff;border-radius:10px;padding:10px 12px;
                text-align:center;font-weight:700;border:1px solid #020617;">🪪 Document OCR</div>""",
                unsafe_allow_html=True,
            )
        else:
            if st.button("🪪 Document OCR", use_container_width=True, key="btn_mode_doc"):
                st.session_state.ocr_mode = "Document"
                st.session_state.last_result = None
                st.rerun()

mode = st.session_state.ocr_mode
if mode == "Document":
    st.markdown(
        """<div class="info-card accent">
        <div style="display:flex;align-items:center;gap:10px;">
            <span class="badge badge-pan">Document OCR</span>
            <span style="color:#6b7280;font-size:0.82rem;">Aadhaar, PAN, DL &amp; Voter ID key-value extraction with face detection</span>
        </div></div>""",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """<div class="info-card blue">
        <div style="display:flex;align-items:center;gap:10px;">
            <span class="badge badge-normal">Text Extraction</span>
            <span style="color:#6b7280;font-size:0.82rem;">Plain text extraction for any document or image</span>
        </div></div>""",
        unsafe_allow_html=True,
    )

st.divider()

st.markdown('<div class="section-label">🌍 Language &nbsp;&nbsp; ⚙ OCR Engine</div>', unsafe_allow_html=True)
col_l, col_e = st.columns(2)
languages = {
    "English": "eng",
    "Spanish": "spa",
    "French": "fre",
    "German": "ger",
    "Italian": "ita",
    "Chinese (Simplified)": "chs",
    "Chinese (Traditional)": "cht",
}
engine_options = {"Engine 1 (Fast)": 1, "Engine 2 (Better)": 2, "Engine 3 (Best - Handwriting)": 3}
with col_l:
    selected_language = st.selectbox("Language", list(languages.keys()), label_visibility="collapsed")
    language_code = languages[selected_language]
with col_e:
    selected_engine = st.selectbox("OCR Engine", list(engine_options.keys()), label_visibility="collapsed")
    engine_code = engine_options[selected_engine]

st.divider()

# ================================================================
# 10. SPLIT SCREEN — Left: Input  |  Right: Result
# ================================================================
MAX_FILE_BYTES = 5 * 1024 * 1024
col_left, col_right = st.columns([1, 1.4], gap="large")

with col_left:
    st.markdown('<div class="section-label" style="margin-top:0;">Input Source</div>', unsafe_allow_html=True)
    input_tab1, input_tab2 = st.tabs(["📂 Upload File", "📷 Camera"])

    uploaded_file = None

    with input_tab1:
        _uf = st.file_uploader(
            "Upload image or PDF (max 5 MB)",
            type=["png", "jpg", "jpeg", "webp", "pdf"],
            label_visibility="collapsed",
        )
        if _uf is not None:
            _uf.seek(0, 2)
            _sz = _uf.tell()
            _uf.seek(0)
            if _sz > MAX_FILE_BYTES:
                st.error(f"❌ File too large ({round(_sz/1024/1024,2)} MB). Max 5 MB.")
            else:
                uploaded_file = _uf
                st.session_state.camera_bytes = None
                file_type_check = get_file_type(_uf)
                if file_type_check.startswith("image"):
                    _uf.seek(0)
                    st.image(_uf, use_container_width=True, caption=f"📄 {_uf.name} · {round(_sz/1024,1)} KB")
                    _uf.seek(0)
                else:
                    st.caption(f"📄 {_uf.name} · {round(_sz/1024,1)} KB")

    with input_tab2:
        st.info("📱 Works best on mobile. Point camera at document and capture.", icon="ℹ️")
        b1, b2 = st.columns(2)
        with b1:
            if st.button("📸 Open Camera", use_container_width=True, key="btn_open_camera"):
                st.session_state.camera_open = True
                st.rerun()
        with b2:
            if st.button("✖ Close Camera", use_container_width=True, key="btn_close_camera"):
                st.session_state.camera_open = False
                st.rerun()

        camera_image = None
        if st.session_state.camera_open:
            st.markdown("<p style='margin:8px 0 6px;color:#0f172a;font-weight:700;'>Take Photo</p>", unsafe_allow_html=True)
            cam_key = f"camera_input_{st.session_state.camera_widget_nonce}"
            camera_image = st.camera_input("Take Photo", key=cam_key, label_visibility="visible")
        else:
            st.caption("Click `Open Camera` to show the take photo option.")

        if camera_image is not None:
            camera_image.seek(0, 2)
            _csz = camera_image.tell()
            camera_image.seek(0)
            if _csz > MAX_FILE_BYTES:
                st.error("❌ Capture too large.")
            else:
                st.session_state.camera_bytes = camera_image.read()
                st.session_state.camera_fsize = _csz
                st.session_state.camera_open = False

        if st.session_state.camera_bytes:
            cam_buf = io.BytesIO(st.session_state.camera_bytes)
            cam_buf.name = "camera_capture.jpg"
            cam_buf.type = "image/jpeg"
            cam_buf.seek(0)
            if uploaded_file is None:
                uploaded_file = cam_buf
            st.image(io.BytesIO(st.session_state.camera_bytes), use_container_width=True, caption=f"📷 {round(st.session_state.camera_fsize/1024,1)} KB")
            if st.button("🗑 Clear Photo", key="btn_clear_cam"):
                st.session_state.camera_bytes = None
                st.session_state.camera_fsize = 0
                st.session_state.camera_widget_nonce += 1
                st.session_state.camera_open = False
                st.rerun()

    st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
    extract_clicked = st.button("🚀 Extract Text", use_container_width=True, key="btn_extract")

    if extract_clicked and uploaded_file:
        try:
            uploaded_file.seek(0)
            raw_bytes = uploaded_file.read()
        except Exception as e:
            st.error(f"❌ Could not read file: {e}")
            raw_bytes = None

        if raw_bytes:
            file_type = get_file_type(uploaded_file)
            file_name = getattr(uploaded_file, "name", "camera_capture.jpg")
            is_pdf = file_type == "application/pdf" or file_name.lower().endswith(".pdf")

            if is_pdf and engine_code == 3:
                st.warning("⚠️ Engine 3 doesn't support PDFs — using Engine 2.")

            blur_ok = True
            if file_type.startswith("image"):
                blur_score = detect_blur(io.BytesIO(raw_bytes))
                if blur_score < 60:
                    st.error(f"⚠ Too blurry (score: {round(blur_score,1)}). Retake with better lighting.")
                    blur_ok = False
                elif blur_score < 120:
                    st.warning(f"Slightly soft (score: {round(blur_score,1)}). Will enhance.")

            if blur_ok:
                photo_b64 = None
                if file_type.startswith("image") and mode == "Document":
                    with st.spinner("📸 Detecting photo..."):
                        photo_b64 = extract_face_photo(io.BytesIO(raw_bytes))

                with st.spinner("🔍 Extracting text..."):
                    result = perform_ocr(raw_bytes, language_code, engine_code, is_pdf=is_pdf)

                st.session_state.camera_bytes = None

                if "error" in result:
                    st.error(f"❌ {result['error']}")
                elif result.get("ParsedResults"):
                    parsed_results = result["ParsedResults"]
                    processing_time = round(float(result.get("ProcessingTimeInMilliseconds", 0)) / 1000, 3)
                    combined_text = "\n".join(pr.get("ParsedText", "") for pr in parsed_results)

                    if mode == "Document":
                        doc_type = detect_doc_type(combined_text)
                        if doc_type == "aadhaar":
                            fields = extract_aadhaar_fields(combined_text)
                        elif doc_type == "pan":
                            fields = extract_pan_fields(combined_text)
                        elif doc_type == "dl":
                            fields = extract_dl_fields(combined_text)
                        elif doc_type == "voter":
                            fields = extract_voter_fields(combined_text)
                        else:
                            fields = {}
                    else:
                        doc_type = "normal"
                        fields = {}

                    st.session_state.last_result = {
                        "mode": mode,
                        "doc_type": doc_type,
                        "fields": fields,
                        "raw_text": combined_text,
                        "photo_b64": photo_b64,
                        "processing_time": processing_time,
                        "file_name": file_name,
                        "file_size_bytes": len(raw_bytes),
                        "parsed_results": parsed_results,
                    }

                    if mode == "Document" and fields:
                        saved, save_err = save_extraction(
                            supabase,
                            doc_type,
                            fields,
                            combined_text,
                            file_name,
                            len(raw_bytes),
                            photo_b64=photo_b64,
                            log_failure=log_failure,
                        )
                        st.session_state.last_result["saved"] = saved
                        st.session_state.last_result["save_err"] = save_err

                    st.rerun()
                else:
                    st.error("❌ No text could be extracted.")

    elif extract_clicked and not uploaded_file:
        st.warning("⚠️ Please upload a file or take a photo first.")

with col_right:
    st.markdown('<div class="section-label" style="margin-top:0;">Extracted Result</div>', unsafe_allow_html=True)
    res = st.session_state.last_result

    if res is None:
        st.markdown(
            """
        <div class="empty-state">
            <div class="empty-icon">📄</div>
            <div class="empty-title">No extraction yet</div>
            <div class="empty-sub">Upload a file and click Extract Text</div>
        </div>""",
            unsafe_allow_html=True,
        )
    else:
        if res["mode"] == "Document":
            doc_type = res["doc_type"]
            fields = res["fields"]
            photo_b64 = res.get("photo_b64")

            doc_label = {
                "aadhaar": "Aadhaar Card",
                "pan": "PAN Card",
                "dl": "Driving Licence",
                "voter": "Voter ID",
                "unknown": "Unknown Document",
            }.get(doc_type, "Document")
            badge_cls = {
                "aadhaar": "badge-aadhaar",
                "pan": "badge-pan",
                "dl": "badge-dl",
                "voter": "badge-voter",
                "unknown": "badge-unknown",
            }.get(doc_type, "badge-unknown")

            st.markdown(
                f"""
            <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px;margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:8px;">
                    <span class="badge {badge_cls}">{doc_label}</span>
                    <span style="color:#9ca3af;font-size:0.78rem;">Document OCR</span>
                </div>
                <span style="color:#9ca3af;font-size:0.72rem;font-family:'DM Mono',monospace;">
                    ⏱ {res['processing_time']}s
                </span>
            </div>""",
                unsafe_allow_html=True,
            )

            if doc_type == "unknown":
                st.warning("⚠️ Could not detect document type.")

            st.markdown(photo_html(photo_b64, fields.get("Name", ""), doc_type), unsafe_allow_html=True)
            if photo_b64:
                st.download_button(
                    "⬇ Download Photo",
                    data=base64.b64decode(photo_b64),
                    file_name=f"{doc_type}_photo.jpg",
                    mime="image/jpeg",
                    key="dl_photo",
                )

            if fields:
                st.markdown('<div class="section-label">Extracted Fields</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="info-card">{render_kv_table(fields)}</div>', unsafe_allow_html=True)

                expected = {"aadhaar": 8, "pan": 5, "dl": 8, "voter": 7}.get(doc_type, 4)
                st.markdown(render_confidence_bar(min(len(fields) / expected, 1.0)), unsafe_allow_html=True)

                saved = res.get("saved")
                save_err = res.get("save_err")
                if saved and save_err == "partial":
                    st.success("✅ Saved to your account (core fields only — run the SQL below to enable all fields).")
                    with st.expander("📋 Add missing columns to Supabase", expanded=False):
                        st.code(
                            """
ALTER TABLE extractions
  ADD COLUMN IF NOT EXISTS enrolment_no         TEXT,
  ADD COLUMN IF NOT EXISTS date_of_issue        TEXT,
  ADD COLUMN IF NOT EXISTS son_daughter_wife_of TEXT,
  ADD COLUMN IF NOT EXISTS serial_no            TEXT,
  ADD COLUMN IF NOT EXISTS polling_station      TEXT,
  ADD COLUMN IF NOT EXISTS mobile               TEXT,
  ADD COLUMN IF NOT EXISTS photo_url            TEXT;
""",
                            language="sql",
                        )
                elif saved:
                    st.success("✅ Saved to your account.")
                elif save_err == "duplicate":
                    st.info("ℹ️ Already saved — no duplicate created.")
                elif save_err:
                    st.warning(f"⚠️ Could not save: {save_err}")

                json_str = json.dumps(fields, indent=2, ensure_ascii=False)
                csv_str = "\n".join(f"{k},{v}" for k, v in fields.items())
                dl1, dl2 = st.columns(2)
                with dl1:
                    st.download_button("⬇ Download JSON", data=json_str, file_name=f"{doc_type}_fields.json", mime="application/json", key="dl_json")
                with dl2:
                    st.download_button("⬇ Download CSV", data=csv_str, file_name=f"{doc_type}_fields.csv", mime="text/csv", key="dl_csv")
            else:
                st.warning("No structured fields extracted.")

            with st.expander("📄 Raw OCR Text"):
                for i, pr in enumerate(res["parsed_results"]):
                    raw = pr.get("ParsedText", "").strip()
                    st.text_area(
                        f"Page {i+1}" if len(res["parsed_results"]) > 1 else "Raw Text",
                        value=raw or "No text found.",
                        height=160,
                        key=f"raw_{i}",
                    )
                    st.download_button(
                        "⬇ Raw Text",
                        data=raw,
                        file_name=f"raw_p{i+1}.txt",
                        mime="text/plain",
                        key=f"dl_raw_{i}",
                    )

        else:
            parsed_results = res["parsed_results"]
            st.markdown(
                f"""
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
                <span class="badge badge-normal">Text Extraction</span>
                <span style="color:#9ca3af;font-size:0.72rem;font-family:'DM Mono',monospace;">
                    ⏱ {res['processing_time']}s · {len(parsed_results)} page(s)</span>
            </div>""",
                unsafe_allow_html=True,
            )

            if len(parsed_results) > 1:
                tabs = st.tabs([f"Page {i+1}" for i in range(len(parsed_results))])
                for i, tab in enumerate(tabs):
                    with tab:
                        text = parsed_results[i].get("ParsedText", "").strip()
                        edited = st.text_area("Text", value=text or "No text found.", height=300, key=f"norm_text_{i}")
                        st.download_button("⬇ Download", data=edited, file_name=f"page_{i+1}.txt", mime="text/plain", key=f"dl_norm_{i}")
            else:
                text = parsed_results[0].get("ParsedText", "").strip()
                edited = st.text_area("Extracted Text", value=text or "No text found.", height=300)
                st.download_button("⬇ Download Text", data=edited, file_name="ocr_text.txt", mime="text/plain", key="dl_norm")

        if st.button("✖ Clear Result", key="btn_clear_result"):
            st.session_state.last_result = None
            st.rerun()


# ================================================================
# 11. SIDEBAR — Saved Extractions + Failure Log
# ================================================================
st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)
render_sidebar(
    supabase=supabase,
    auth_logout_fn=auth_logout,
    load_extractions_fn=lambda s: load_extractions(s, log_failure=log_failure),
)
