import os
import base64
from datetime import datetime

import streamlit as st
from supabase import create_client, Client


def _safe_log(log_failure, context: str, message: str):
    if callable(log_failure):
        log_failure(context, message)


def _get_secret(key: str, default: str = "") -> str:
    val = os.getenv(key)
    if val:
        return val
    try:
        return st.secrets.get(key, default)
    except Exception:
        return default


SUPABASE_URL = _get_secret("SUPABASE_URL")
SUPABASE_KEY = _get_secret("SUPABASE_ANON_KEY")


@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def auth_login(supabase: Client, email: str, password: str):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = res.user
        st.session_state.access_token = res.session.access_token
        supabase.postgrest.auth(res.session.access_token)

        try:
            supabase.rpc("upsert_user_login", {
                "p_user_id": res.user.id,
                "p_email": res.user.email,
            }).execute()
            user_row = (
                supabase.table("users")
                .select("last_login, created_at")
                .eq("id", res.user.id)
                .single()
                .execute()
            )
            st.session_state.last_login = user_row.data.get("last_login") if user_row.data else None
            st.session_state.user_created_at = user_row.data.get("created_at") if user_row.data else None
        except Exception:
            st.session_state.last_login = None
            st.session_state.user_created_at = None

        return True, None
    except Exception as e:
        return False, str(e)


def auth_signup(supabase: Client, email: str, password: str):
    try:
        supabase.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {
                    "email_redirect_to": "https://ocr-stream-nhjd5pbhtxcm99hfgncbre.streamlit.app"
                },
            }
        )
        return True, None
    except Exception as e:
        return False, str(e)


def auth_logout(supabase: Client):
    supabase.auth.sign_out()
    st.session_state.user = None
    st.session_state.access_token = None


_CORE_COLUMNS = {
    "user_id", "doc_type", "file_name", "file_size_kb",
    "holder_name", "dob", "gender",
    "aadhaar_number", "address", "pincode", "state", "vid",
    "pan_number", "father_name", "account_type", "issued_by",
    "dl_number", "valid_till", "vehicle_class", "blood_group", "issuing_authority",
    "epic_number", "father_husband_name", "constituency", "part_no",
    "raw_text",
}

_EXTENDED_COLUMNS = {
    "enrolment_no", "date_of_issue", "son_daughter_wife_of",
    "serial_no", "polling_station", "mobile",
}


def upload_photo_to_storage(supabase: Client, photo_b64: str, doc_type: str, log_failure=None) -> str:
    if not photo_b64 or not st.session_state.user:
        return ""
    try:
        photo_bytes = base64.b64decode(photo_b64)
        user_id = st.session_state.user.id
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = f"{user_id}/{doc_type}_{timestamp}.jpg"

        supabase.storage.from_("id-photos").upload(
            file_path,
            photo_bytes,
            {"content-type": "image/jpeg", "upsert": "false"},
        )
        url_res = supabase.storage.from_("id-photos").create_signed_url(file_path, 315360000)
        return url_res.get("signedURL", "") if isinstance(url_res, dict) else ""
    except Exception as e:
        _safe_log(log_failure, "Photo Upload", str(e))
        return ""


def _build_row(fields, doc_type, file_name, size_kb, raw_text, include_extended=True, photo_url=""):
    row = {
        "user_id": st.session_state.user.id,
        "doc_type": doc_type if doc_type in ("aadhaar", "pan", "dl", "voter") else "other",
        "file_name": file_name,
        "file_size_kb": size_kb,
        "holder_name": fields.get("Name", ""),
        "dob": fields.get("Date of Birth", ""),
        "gender": fields.get("Gender", ""),
        "aadhaar_number": fields.get("Aadhaar Number", ""),
        "address": fields.get("Address", ""),
        "pincode": fields.get("Pincode", ""),
        "state": fields.get("State", ""),
        "vid": fields.get("VID", ""),
        "pan_number": fields.get("PAN Number", ""),
        "father_name": fields.get("Father's Name", ""),
        "account_type": fields.get("Account Type", ""),
        "issued_by": fields.get("Issued By", ""),
        "dl_number": fields.get("DL Number", ""),
        "valid_till": fields.get("Valid Till", ""),
        "vehicle_class": fields.get("Vehicle Class", ""),
        "blood_group": fields.get("Blood Group", ""),
        "issuing_authority": fields.get("Issuing Authority", ""),
        "epic_number": fields.get("EPIC Number", ""),
        "father_husband_name": fields.get("Father's Name", "") or fields.get("Father/Husband Name", ""),
        "constituency": fields.get("Constituency", ""),
        "part_no": fields.get("Part No", ""),
        "raw_text": raw_text[:4000],
        "photo_url": photo_url,
    }
    if include_extended:
        row.update(
            {
                "enrolment_no": fields.get("Enrolment No", ""),
                "date_of_issue": fields.get("Date of Issue", ""),
                "son_daughter_wife_of": fields.get("Son/Daughter/Wife of", ""),
                "serial_no": fields.get("Serial No", ""),
                "polling_station": fields.get("Polling Station", ""),
                "mobile": fields.get("Mobile", ""),
            }
        )
    return {k: v for k, v in row.items() if v != ""}


def _get_doc_unique_key(doc_type, fields):
    mapping = {
        "aadhaar": ("aadhaar_number", fields.get("Aadhaar Number", "").replace(" ", "")),
        "pan": ("pan_number", fields.get("PAN Number", "")),
        "dl": ("dl_number", fields.get("DL Number", "").replace(" ", "").replace("-", "")),
        "voter": ("epic_number", fields.get("EPIC Number", "")),
    }
    return mapping.get(doc_type, (None, None))


def check_duplicate(supabase: Client, doc_type, fields):
    col, val = _get_doc_unique_key(doc_type, fields)
    if not col or not val:
        return False
    try:
        existing = (
            supabase.table("extractions")
            .select("id")
            .eq("user_id", st.session_state.user.id)
            .eq("doc_type", doc_type)
            .execute()
        )
        if not existing.data:
            return False
        norm_val = val.replace(" ", "").replace("-", "").upper()
        for row in existing.data:
            stored = str(row.get(col) or "").replace(" ", "").replace("-", "").upper()
            if stored and stored == norm_val:
                return True
        return False
    except Exception:
        return False


def save_extraction(
    supabase: Client,
    doc_type,
    fields,
    raw_text="",
    file_name="",
    file_size_bytes=0,
    photo_b64=None,
    log_failure=None,
):
    if not st.session_state.user:
        return False, "Not logged in"

    supabase.postgrest.auth(st.session_state.access_token)
    size_kb = round(file_size_bytes / 1024, 1) if file_size_bytes else 0

    if check_duplicate(supabase, doc_type, fields):
        return False, "duplicate"

    photo_url = ""
    if photo_b64:
        with st.spinner("📤 Uploading photo to storage..."):
            photo_url = upload_photo_to_storage(supabase, photo_b64, doc_type, log_failure)

    try:
        row = _build_row(fields, doc_type, file_name, size_kb, raw_text, include_extended=True, photo_url=photo_url)
        supabase.table("extractions").insert(row).execute()
        return True, None
    except Exception as e:
        err = str(e)
        if "duplicate" in err.lower() or "unique" in err.lower() or "23505" in err:
            return False, "duplicate"
        is_column_error = "PGRST204" in err or "column" in err.lower() or "schema cache" in err.lower()
        if not is_column_error:
            return False, err

    try:
        row = _build_row(fields, doc_type, file_name, size_kb, raw_text, include_extended=False, photo_url=photo_url)
        supabase.table("extractions").insert(row).execute()
        return True, "partial"
    except Exception as e2:
        err2 = str(e2)
        if "duplicate" in err2.lower() or "unique" in err2.lower() or "23505" in err2:
            return False, "duplicate"
        return False, err2


def load_extractions(supabase: Client, log_failure=None):
    if not st.session_state.user:
        return []
    try:
        supabase.postgrest.auth(st.session_state.access_token)
        res = (
            supabase.table("extractions")
            .select("*")
            .eq("user_id", st.session_state.user.id)
            .order("created_at", desc=True)
            .execute()
        )
        return res.data or []
    except Exception as e:
        _safe_log(log_failure, "Supabase Fetch", str(e))
        return []
