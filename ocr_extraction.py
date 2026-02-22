import os
import re
import io
import cv2
import base64
import requests
import numpy as np
from PIL import Image, ImageEnhance

OCR_URL = "https://api.ocr.space/parse/image"
OCR_API_KEY = os.getenv("OCR_API_KEY", "")
_LOGGER = None


def set_ocr_context(api_key: str = "", logger=None):
    global OCR_API_KEY, _LOGGER
    if api_key is not None:
        OCR_API_KEY = api_key
    _LOGGER = logger


def log_failure(context: str, message: str):
    if callable(_LOGGER):
        _LOGGER(context, message)

def get_file_type(f) -> str:
    try:
        t = getattr(f, "type", None)
        if t and isinstance(t, str) and t.strip():
            return t.strip()
        name = getattr(f, "name", "") or ""
        if name.lower().endswith(".pdf"):
            return "application/pdf"
        return "image/jpeg"
    except Exception:
        return "image/jpeg"

def detect_blur(file) -> float:
    try:
        file.seek(0)
        image = Image.open(file).convert("L")
        score = cv2.Laplacian(np.array(image), cv2.CV_64F).var()
        file.seek(0)
        return score
    except Exception as e:
        log_failure("Blur Detection", str(e))
        return 999

def compress_image_bytes(raw_bytes: bytes) -> bytes:
    try:
        img = Image.open(io.BytesIO(raw_bytes)).convert("L")
        if img.width > 1200:
            img = img.resize((1200, int(img.height * 1200 / img.width)), Image.LANCZOS)
        img = ImageEnhance.Contrast(img).enhance(1.5)
        img = ImageEnhance.Sharpness(img).enhance(1.4)
        for quality in [75, 60, 45, 30, 20]:
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            if len(buf.getvalue()) <= 280*1024 or quality == 20:
                return buf.getvalue()
        return buf.getvalue()
    except Exception as e:
        log_failure("Compress Image", str(e))
        return raw_bytes

def extract_face_photo(file):
    try:
        file.seek(0)
        img_pil = Image.open(file).convert("RGB")
        img_np  = np.array(img_pil)
        img_bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        h, w    = img_bgr.shape[:2]
        gray    = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        cascade_paths = [
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml",
            "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
        ]
        face_cascade = None
        for cp in cascade_paths:
            if os.path.exists(cp):
                face_cascade = cv2.CascadeClassifier(cp)
                break

        face_rect = None
        if face_cascade and not face_cascade.empty():
            faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(30,30))
            if len(faces) > 0:
                best, best_score = None, -1
                for (fx, fy, fw, fh) in faces:
                    score = (1 if fx > w*0.4 else 0) + (fw*fh)/(w*h)
                    if score > best_score:
                        best_score, best = score, (fx, fy, fw, fh)
                face_rect = best

        if face_rect:
            fx, fy, fw, fh = face_rect
            px, py = int(fw*0.2), int(fh*0.2)
            face_crop = img_pil.crop((max(0,fx-px), max(0,fy-py), min(w,fx+fw+px), min(h,fy+fh+py)))
        else:
            face_crop = img_pil.crop((int(w*0.6), int(h*0.1), int(w*0.85), int(h*0.7)))
            log_failure("Face Detection", "No face found — using ROI fallback")

        face_crop = face_crop.resize((100, 120), Image.LANCZOS)
        buf = io.BytesIO()
        face_crop.save(buf, format="JPEG", quality=85)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")
    except Exception as e:
        log_failure("Face Extraction", str(e))
        return None


# ── OCR ───────────────────────────────────────────────────────────
def perform_ocr(raw_bytes, language_code, engine_code, is_pdf=False, _retry=True):
    if not OCR_API_KEY:
        return {"error": "Missing OCR_API_KEY"}
    try:
        if is_pdf:
            safe_engine = 2 if engine_code == 3 else engine_code
            send_bytes, filename, mimetype = raw_bytes, "document.pdf", "application/pdf"
        else:
            safe_engine = engine_code
            send_bytes, filename, mimetype = compress_image_bytes(raw_bytes), "image.jpg", "image/jpeg"

        response = requests.post(OCR_URL, data={
            "apikey": OCR_API_KEY, "language": language_code,
            "OCREngine": safe_engine, "isOverlayRequired": False,
            "detectOrientation": True, "scale": True,
        }, files={"file": (filename, send_bytes, mimetype)}, timeout=90)
        response.raise_for_status()
        result = response.json()

        if result.get("IsErroredOnProcessing"):
            err_msgs = result.get("ErrorMessage", ["Unknown OCR error"])
            err_str = "; ".join(err_msgs) if isinstance(err_msgs, list) else str(err_msgs)
            if _retry and "timed out" in err_str.lower():
                return perform_ocr(raw_bytes, language_code, 1, is_pdf, _retry=False)
            log_failure("OCR Processing", err_str)
            return {"error": err_str}
        return result

    except requests.Timeout:
        if _retry:
            return perform_ocr(raw_bytes, language_code, 1, is_pdf, _retry=False)
        msg = "OCR timed out. Try Engine 1 or a smaller file."
        log_failure("OCR Timeout", msg)
        return {"error": msg}
    except Exception as e:
        log_failure("OCR Error", str(e))
        return {"error": str(e)}


# ================================================================
# DOCUMENT PARSING
# ================================================================

def clean_ocr_text(text):
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b-\u200f\ufeff]', '', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'(?<=\d)[Oo](?=\d)', '0', text)
    text = re.sub(r'(?<=\d)[Il](?=\d)', '1', text)
    return text.strip()


def detect_doc_type(text):
    t = clean_ocr_text(text).lower()

    aadhaar_signals = [
        "aadhaar", "aadhar", "uidai", "uid", "unique identification authority",
        "enrollment no", "enrolment no", "भारत सरकार", "आधार", "मेरा आधार",
        "government of india", "xxxx xxxx", "virtual id", "vid :"
    ]
    pan_signals = [
        "permanent account number", "income tax department", "income tax",
        "आयकर विभाग", "govt. of india", "pan", "स्थायी लेखा"
    ]
    dl_signals = [
        "driving licence", "driving license", "dl no", "licence no",
        "transport department", "vehicle class", "cov", "lmv", "mcwg", "rto",
        "union of india", "date of issue", "valid till", "son/daughter/wife"
    ]
    voter_signals = [
        "election commission", "voter", "electors photo", "epic",
        "electoral", "निर्वाचन आयोग", "मतदाता", "part no",
        "assembly constituency", "elector photo identity card", "kkd", "kk"
    ]

    pan_pat     = re.search(r'\b[A-Z]{5}[0-9]{4}[A-Z]\b', text)
    aadhaar_pat = re.search(r'\b\d{4}[\s\-]\d{4}[\s\-]\d{4}\b|\b\d{12}\b|XXXX\s*XXXX\s*\d{4}', text, re.IGNORECASE)
    dl_pat      = re.search(r'\b[A-Z]{2}[\s\-]?\d{2}[\s\-]?\d{4,11}\b', text)
    epic_pat    = re.search(r'\b[A-Z]{3}\d{7}\b', text)

    scores = {
        "aadhaar": sum(2 for s in aadhaar_signals if s in t) + (6 if aadhaar_pat else 0),
        "pan":     sum(2 for s in pan_signals     if s in t) + (6 if pan_pat     else 0),
        "dl":      sum(2 for s in dl_signals      if s in t) + (6 if dl_pat      else 0),
        "voter":   sum(2 for s in voter_signals   if s in t) + (6 if epic_pat    else 0),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"


def extract_aadhaar_fields(text):
    fields = {}
    text = clean_ocr_text(text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    full  = text

    masked_m = re.search(r'\b(XXXX[\s]*XXXX[\s]*\d{4})\b', full, re.IGNORECASE)
    if masked_m:
        fields["Aadhaar Number"] = re.sub(r'\s+', ' ', masked_m.group(1).upper()).strip()
    else:
        for pat, fmt in [
            (r'\b(\d{4})\s(\d{4})\s(\d{4})\b',
             lambda m: f"{m.group(1)} {m.group(2)} {m.group(3)}"),
            (r'\b(\d{4})-(\d{4})-(\d{4})\b',
             lambda m: f"{m.group(1)} {m.group(2)} {m.group(3)}"),
            (r'(?<!\d)(\d{12})(?!\d)',
             lambda m: f"{m.group(1)[:4]} {m.group(1)[4:8]} {m.group(1)[8:]}"),
        ]:
            m = re.search(pat, full)
            if m:
                fields["Aadhaar Number"] = fmt(m)
                break

    vid_m = re.search(
        r'(?:vid|virtual\s*id|virtual\s*identification)\s*[:\-]?\s*(\d[\d\s]{14,18})',
        full, re.IGNORECASE)
    if not vid_m:
        vid_m = re.search(r'VID\s*[:\-]\s*([\d\s]{16,20})', full, re.IGNORECASE)
    if vid_m:
        raw_vid = re.sub(r'\s', '', vid_m.group(1))
        if len(raw_vid) == 16:
            fields["VID"] = f"{raw_vid[:4]} {raw_vid[4:8]} {raw_vid[8:12]} {raw_vid[12:]}"
        else:
            fields["VID"] = raw_vid

    enrol_m = re.search(
        r'(?:enrolment|enrollment)\s*(?:no\.?|number)?\s*[:\-]?\s*([\d/\s]{14,25})',
        full, re.IGNORECASE)
    if enrol_m:
        fields["Enrolment No"] = enrol_m.group(1).strip()

    for i, line in enumerate(lines):
        if line.strip().lower() == 'to' and i + 1 < len(lines):
            candidate = re.sub(r'[^A-Za-z\s\.]', '', lines[i + 1]).strip()
            words = candidate.split()
            if 1 <= len(words) <= 5 and all(len(w) >= 2 for w in words):
                fields["Name"] = candidate.title()
            break

    if "Name" not in fields:
        m = re.search(
            r'(?:^|\n)\s*(?:name|naam|नाम)\s*[:\-]\s*([A-Za-z][A-Za-z\s\.]{2,40})',
            full, re.IGNORECASE | re.MULTILINE)
        if m:
            candidate = re.sub(r'\s+', ' ', m.group(1)).strip().rstrip('.')
            if len(candidate.split()) >= 1 and len(candidate) >= 4:
                fields["Name"] = candidate.title()

    if "Name" not in fields:
        skip_words = {
            'male', 'female', 'dob', 'date', 'birth', 'address', 'government',
            'india', 'aadhaar', 'aadhar', 'uid', 'enrollment', 'year', 'of',
            'और', 'भारत', 'unique', 'identification', 'authority', 'enrolment'
        }
        for line in lines[1:15]:
            candidate = re.sub(r'[^A-Za-z\s]', '', line).strip()
            words = [w for w in candidate.split() if len(w) >= 2]
            if 2 <= len(words) <= 5 and not {w.lower() for w in words}.intersection(skip_words):
                if all(w.isalpha() for w in words):
                    fields["Name"] = candidate.title()
                    break

    for pat in [
        r'(?:dob|date\s*of\s*birth|d\.o\.b|जन्म\s*तिथि)\s*[:\-/]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
        r'DOB\s*[:/]?\s*(\d{2}/\d{2}/\d{4})',
        r'\b(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})\b',
    ]:
        m = re.search(pat, full, re.IGNORECASE)
        if m:
            fields["Date of Birth"] = m.group(1).strip()
            break

    for token, label in [
        ('female', 'Female'), ('male', 'Male'), ('transgender', 'Transgender'),
        ('महिला', 'Female'), ('पुरुष', 'Male'),
    ]:
        if re.search(r'\b' + re.escape(token) + r'\b', full, re.IGNORECASE):
            fields["Gender"] = label
            break

    addr_m = re.search(
        r'(?:s[/\\]o|d[/\\]o|w[/\\]o|c[/\\]o|address|पता)\s*[:\-]?\s*(.+)',
        full, re.IGNORECASE | re.DOTALL)
    if addr_m:
        addr_raw = addr_m.group(1)
        addr_raw = re.split(
            r'\b(XXXX|VID\b|\d{4}[\s\-]\d{4}[\s\-]\d{4}|dob\b|male\b|female\b|'
            r'मेरा\s*आधार|government|aadhaar\s*no)',
            addr_raw, flags=re.IGNORECASE)[0]
        addr_clean = re.sub(r'\s+', ' ', addr_raw).strip().rstrip(',').strip()
        if len(addr_clean) > 8:
            fields["Address"] = addr_clean[:300]

    used_digits = fields.get("Aadhaar Number", "").replace(" ", "")
    for m in re.finditer(r'\b(\d{6})\b', full):
        pin = m.group(1)
        if pin in used_digits:
            continue
        fields["Pincode"] = pin
        break

    state_pat = (
        r'\b(andhra\s*pradesh|arunachal\s*pradesh|assam|bihar|chhattisgarh|goa|gujarat|'
        r'haryana|himachal\s*pradesh|jharkhand|karnataka|kerala|madhya\s*pradesh|'
        r'maharashtra|manipur|meghalaya|mizoram|nagaland|odisha|punjab|rajasthan|'
        r'sikkim|tamil\s*nadu|telangana|tripura|uttar\s*pradesh|uttarakhand|'
        r'west\s*bengal|delhi|jammu|ladakh|chandigarh|puducherry)\b'
    )
    sm = re.search(state_pat, full, re.IGNORECASE)
    if sm:
        fields["State"] = sm.group(1).title()

    aadhaar_digits = fields.get("Aadhaar Number", "").replace(" ", "")
    for m in re.finditer(r'(?<!\d)([6-9]\d{9})(?!\d)', full):
        mob = m.group(1)
        if mob not in aadhaar_digits:
            fields["Mobile"] = mob
            break

    return fields


def extract_pan_fields(text):
    fields = {}
    text = clean_ocr_text(text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    full  = text

    m = re.search(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', full)
    if m:
        fields["PAN Number"] = m.group(1)

    name_found = False
    for i, line in enumerate(lines):
        if re.search(r'(?:^|/)\s*name\s*$', line, re.IGNORECASE) or \
           re.fullmatch(r'(?:naam|नाम\s*/\s*name)', line.strip(), re.IGNORECASE):
            if i + 1 < len(lines):
                candidate = re.sub(r'[^A-Za-z\s\.]', '', lines[i + 1]).strip()
                if len(candidate) >= 3:
                    fields["Name"] = candidate.title()
                    name_found = True
            break

    if not name_found:
        m2 = re.search(r'(?:name|naam)\s*[:\-]\s*([A-Za-z][A-Za-z\s\.]{2,50})', full, re.IGNORECASE)
        if m2:
            candidate = re.sub(r'\s+', ' ', m2.group(1)).strip().rstrip('.')
            if len(candidate) >= 3:
                fields["Name"] = candidate.title()
                name_found = True

    if not name_found:
        for line in lines:
            words = line.split()
            if (2 <= len(words) <= 5
                    and all(w.isupper() and w.isalpha() and len(w) >= 2 for w in words)
                    and not any(skip in line.lower() for skip in
                                ['income', 'tax', 'govt', 'government', 'permanent',
                                 'account', 'india', 'department'])):
                fields["Name"] = line.title()
                name_found = True
                break

    fname_found = False
    for i, line in enumerate(lines):
        if re.search(r"father'?s?\s*name", line, re.IGNORECASE) or \
           re.search(r'पिता\s*का\s*नाम', line):
            same_line = re.sub(r"(?:father'?s?\s*name|पिता\s*का\s*नाम)\s*[:\-/]?\s*", '', line, flags=re.IGNORECASE).strip()
            if len(same_line) >= 3 and re.search(r'[A-Za-z]', same_line):
                candidate = re.sub(r'[^A-Za-z\s\.]', '', same_line).strip()
                if len(candidate) >= 3:
                    fields["Father's Name"] = candidate.title()
                    fname_found = True
                    break
            if not fname_found and i + 1 < len(lines):
                candidate = re.sub(r'[^A-Za-z\s\.]', '', lines[i + 1]).strip()
                if len(candidate) >= 3:
                    fields["Father's Name"] = candidate.title()
                    fname_found = True
            break

    if not fname_found:
        m3 = re.search(
            r"(?:father'?s?\s*(?:name)?|पिता)\s*[:\-/]\s*([A-Za-z][A-Za-z\s\.]{2,50})",
            full, re.IGNORECASE)
        if m3:
            candidate = re.sub(r'\s+', ' ', m3.group(1)).strip().rstrip('.')
            if len(candidate) >= 3:
                fields["Father's Name"] = candidate.title()

    for i, line in enumerate(lines):
        if re.search(r'date\s*of\s*birth|dob|जन्म\s*की\s*तारीख', line, re.IGNORECASE):
            m4 = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})', line)
            if m4:
                fields["Date of Birth"] = m4.group(1).strip()
                break
            if i + 1 < len(lines):
                m4 = re.search(r'(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})', lines[i + 1])
                if m4:
                    fields["Date of Birth"] = m4.group(1).strip()
            break

    if "Date of Birth" not in fields:
        m5 = re.search(r'\b(\d{2}[\/\-\.]\d{2}[\/\-\.]\d{4})\b', full)
        if m5:
            fields["Date of Birth"] = m5.group(1).strip()

    type_m = re.search(
        r'\b(individual|company|firm|huf|trust|aop|boi|llp|partnership)\b',
        full, re.IGNORECASE)
    if type_m:
        fields["Account Type"] = type_m.group(1).title()

    if re.search(r'income\s*tax|आयकर', full, re.IGNORECASE):
        fields["Issued By"] = "Income Tax Department, Govt. of India"

    return fields


def extract_dl_fields(text):
    fields = {}
    text = clean_ocr_text(text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    full  = text

    dl_patterns = [
        r'\b([A-Z]{2})[\s\-]?(\d{2})[\s\-]?(\d{4})[\s\-]?(\d{7})\b',
        r'\b([A-Z]{2}\d{2}[A-Z]?\d{10,11})\b',
        r'\b([A-Z]{2}\d{13})\b',
    ]
    for pat in dl_patterns:
        dl_m = re.search(pat, full)
        if dl_m:
            if dl_m.lastindex == 4:
                fields["DL Number"] = (
                    f"{dl_m.group(1)}-{dl_m.group(2)}-{dl_m.group(3)}-{dl_m.group(4)}"
                )
            else:
                fields["DL Number"] = dl_m.group(1)
            break

    all_dates = re.findall(r'(\d{1,2}[\-/\.]\d{1,2}[\-/\.]\d{4})', full)

    issue_m = re.search(
        r'(?:date\s*of\s*issue|d\.?\s*o\.?\s*i\.?|issued\s*on)\s*[:\-]?\s*(\d{1,2}[\-/\.]\d{1,2}[\-/\.]\d{4})',
        full, re.IGNORECASE)
    if issue_m:
        fields["Date of Issue"] = issue_m.group(1)

    valid_m = re.search(
        r'(?:valid\s*till|validity|expiry|expires?\s*on|valid\s*upto)\s*[:\-]?\s*(\d{1,2}[\-/\.]\d{1,2}[\-/\.]\d{4})',
        full, re.IGNORECASE)
    if valid_m:
        fields["Valid Till"] = valid_m.group(1)

    dob_m = re.search(
        r'(?:date\s*of\s*birth|d\.?\s*o\.?\s*b\.?|dob)\s*[:\-]?\s*(\d{1,2}[\-/\.]\d{1,2}[\-/\.]\d{4})',
        full, re.IGNORECASE)
    if dob_m:
        fields["Date of Birth"] = dob_m.group(1)

    if all_dates and len(all_dates) >= 2:
        if "Date of Issue" not in fields and "Valid Till" not in fields:
            block_m = re.search(
                r'(\d{1,2}[\-/\.]\d{1,2}[\-/\.]\d{4})\s+(\d{1,2}[\-/\.]\d{1,2}[\-/\.]\d{4})',
                full)
            if block_m:
                fields["Date of Issue"] = block_m.group(1)
                fields["Valid Till"]    = block_m.group(2)
        if "Date of Birth" not in fields and len(all_dates) >= 3:
            used = {fields.get("Date of Issue",""), fields.get("Valid Till","")}
            for d in all_dates:
                if d not in used:
                    fields["Date of Birth"] = d
                    break

    bg_m = re.search(r'\b(A|B|AB|O)[\+\-]\b', full)
    if bg_m:
        fields["Blood Group"] = bg_m.group(0)
    else:
        bg_m2 = re.search(r'blood\s*group\s*[:\-]?\s*([ABO]{1,2}[\+\-]?)', full, re.IGNORECASE)
        if bg_m2:
            fields["Blood Group"] = bg_m2.group(1).upper()

    name_found = False
    for i, line in enumerate(lines):
        if re.search(r'(?:^|\s)(?:name|naam)\s*$', line, re.IGNORECASE):
            if i + 1 < len(lines):
                candidate = re.sub(r'[^A-Za-z\s\.]', '', lines[i + 1]).strip()
                if len(candidate) >= 3:
                    fields["Name"] = candidate.title()
                    name_found = True
            break
    if not name_found:
        m = re.search(
            r'(?:name|naam)\s*[:\-]\s*([A-Za-z][A-Za-z\s\.]{2,45})',
            full, re.IGNORECASE)
        if m:
            candidate = re.sub(r'[^A-Za-z\s\.]', '', m.group(1)).strip()
            if len(candidate) >= 3:
                fields["Name"] = candidate.title()
                name_found = True

    if not name_found:
        for line in lines:
            words = line.strip().split()
            if (1 <= len(words) <= 4
                    and all(w.isupper() and w.isalpha() and len(w) >= 2 for w in words)
                    and not any(skip in line.upper() for skip in [
                        'DRIVING', 'LICENCE', 'LICENSE', 'UNION', 'INDIA',
                        'TRANSPORT', 'AUTHORITY', 'VEHICLE', 'CLASS', 'BLOOD',
                        'VALID', 'ISSUE', 'BIRTH', 'GROUP', 'LMV', 'MCWG', 'COV'])):
                fields["Name"] = line.title()
                break

    sdw_m = re.search(
        r'(?:son|daughter|wife)\s*/?\s*(?:daughter\s*/\s*)?(?:son\s*/\s*)?(?:wife\s*of|of)\s*[:\-]?\s*([A-Za-z][A-Za-z\s\.]{2,50})',
        full, re.IGNORECASE)
    if sdw_m:
        candidate = re.sub(r'[^A-Za-z\s\.]', '', sdw_m.group(1)).strip()
        if len(candidate) >= 3:
            fields["Son/Daughter/Wife of"] = candidate.title()

    cov_m = re.search(
        r'(?:cov|class\s*of\s*vehicle|vehicle\s*class|authorised\s*to\s*drive)\s*[:\-]?\s*([A-Z0-9,/\s\-]{2,40})',
        full, re.IGNORECASE)
    if cov_m:
        vc = cov_m.group(1).strip().rstrip(',').strip()[:60]
        if vc:
            fields["Vehicle Class"] = vc

    rto_m = re.search(
        r'(?:licensing\s*authority|issued\s*by|issuing\s*authority|licencing\s*authority|rto)\s*[:\-]?\s*([A-Za-z\s,\.]{4,60})',
        full, re.IGNORECASE)
    if rto_m:
        fields["Issuing Authority"] = rto_m.group(1).strip()

    addr_m = re.search(
        r'(?:address|addr|पता)\s*[:\-]?\s*(.+?)(?:\n\n|\bDL\b|\bLicen|\bValid|\bCOV\b|$)',
        full, re.IGNORECASE | re.DOTALL)
    if addr_m:
        addr_raw = addr_m.group(1)
        addr_clean = re.sub(r'\s+', ' ', addr_raw).strip().rstrip(',')[:250]
        if len(addr_clean) > 6:
            fields["Address"] = addr_clean

    if "DL Number" in fields:
        state_code_map = {
            "AN": "Andaman & Nicobar", "AP": "Andhra Pradesh", "AR": "Arunachal Pradesh",
            "AS": "Assam", "BR": "Bihar", "CH": "Chandigarh", "CG": "Chhattisgarh",
            "DN": "Dadra & Nagar Haveli", "DD": "Daman & Diu", "DL": "Delhi",
            "GA": "Goa", "GJ": "Gujarat", "HR": "Haryana", "HP": "Himachal Pradesh",
            "JK": "Jammu & Kashmir", "JH": "Jharkhand", "KA": "Karnataka",
            "KL": "Kerala", "LD": "Lakshadweep", "MP": "Madhya Pradesh",
            "MH": "Maharashtra", "MN": "Manipur", "ML": "Meghalaya", "MZ": "Mizoram",
            "NL": "Nagaland", "OD": "Odisha", "OR": "Odisha", "PY": "Puducherry",
            "PB": "Punjab", "RJ": "Rajasthan", "SK": "Sikkim", "TN": "Tamil Nadu",
            "TG": "Telangana", "TR": "Tripura", "UP": "Uttar Pradesh",
            "UK": "Uttarakhand", "WB": "West Bengal",
        }
        dl_prefix = fields["DL Number"][:2].upper()
        if dl_prefix in state_code_map:
            fields["State"] = state_code_map[dl_prefix]

    return fields


def extract_voter_fields(text):
    fields = {}
    text = clean_ocr_text(text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    full  = text

    epic_m = re.search(r'\b([A-Z]{2,3}\d{7})\b', full)
    if epic_m:
        fields["EPIC Number"] = epic_m.group(1)

    name_found = False
    for pat in [
        r'(?:elector\s*name|name\s*of\s*elector|name|नाम)\s*[:\-]\s*([A-Za-z][A-Za-z\s\.]{2,50})',
        r'Name\s*:\s*([A-Za-z][A-Za-z\s\.]{2,50})',
    ]:
        m = re.search(pat, full, re.IGNORECASE)
        if m:
            candidate = re.sub(r'[^A-Za-z\s\.]', '', m.group(1)).strip()
            if len(candidate) >= 4:
                fields["Name"] = candidate.title()
                name_found = True
                break

    if not name_found:
        for i, line in enumerate(lines):
            if re.fullmatch(r'(?:name|naam)', line.strip(), re.IGNORECASE):
                if i + 1 < len(lines):
                    candidate = re.sub(r'[^A-Za-z\s\.]', '', lines[i + 1]).strip()
                    if len(candidate) >= 4:
                        fields["Name"] = candidate.title()
                        name_found = True
                break

    rel_patterns = [
        r"(?:father'?s?\s*name|father\s*name|पिता\s*का\s*नाम)\s*[:\-]?\s*([A-Za-z][A-Za-z\s\.]{2,50})",
        r"(?:husband'?s?\s*name|पति\s*का\s*नाम)\s*[:\-]?\s*([A-Za-z][A-Za-z\s\.]{2,50})",
        r"Father'?s?\s*Name\s*:\s*([A-Za-z][A-Za-z\s\.]{2,50})",
    ]
    for pat in rel_patterns:
        rel_m = re.search(pat, full, re.IGNORECASE)
        if rel_m:
            candidate = re.sub(r'[^A-Za-z\s\.]', '', rel_m.group(1)).strip()
            if len(candidate) >= 4:
                fields["Father's Name"] = candidate.title()
                break

    if "Father's Name" not in fields:
        for i, line in enumerate(lines):
            if re.search(r"father'?s?\s*name|पिता", line, re.IGNORECASE):
                same = re.sub(r"father'?s?\s*name\s*[:\-]?", '', line, flags=re.IGNORECASE).strip()
                same = re.sub(r'[^A-Za-z\s\.]', '', same).strip()
                if len(same) >= 4:
                    fields["Father's Name"] = same.title()
                    break
                if i + 1 < len(lines):
                    nxt = re.sub(r'[^A-Za-z\s\.]', '', lines[i + 1]).strip()
                    if len(nxt) >= 4:
                        fields["Father's Name"] = nxt.title()
                break

    dob_m = re.search(
        r'(?:date\s*of\s*birth|dob|जन्म\s*तिथि|जन्म\s*दिनांक)\s*[:\-/]?\s*(\d{1,2}[\-/\.]\d{1,2}[\-/\.]\d{2,4})',
        full, re.IGNORECASE)
    if dob_m:
        fields["Date of Birth"] = dob_m.group(1)
    else:
        date_m = re.search(r'\b(\d{2}[\-/\.]\d{2}[\-/\.]\d{4})\b', full)
        if date_m:
            fields["Date of Birth"] = date_m.group(1)

    if "Date of Birth" not in fields:
        age_m = re.search(r'(?:age|आयु)\s*[:\-/]?\s*(\d{2,3})', full, re.IGNORECASE)
        if age_m:
            fields["Age"] = age_m.group(1)

    for token, label in [
        ('female', 'Female'), ('male', 'Male'),
        ('पुरुष', 'Male'), ('महिला', 'Female'),
    ]:
        if re.search(r'\b' + re.escape(token) + r'\b', full, re.IGNORECASE):
            fields["Gender"] = label
            break

    const_m = re.search(
        r'(?:assembly\s*constituency|parliamentary\s*constituency|विधान\s*सभा)\s*[:\-]?\s*([A-Za-z\s\(\)\d]{3,60})',
        full, re.IGNORECASE)
    if const_m:
        fields["Constituency"] = const_m.group(1).strip().rstrip('.')

    part_m = re.search(r'part\s*(?:no\.?|number|संख्या)?\s*[:\-]?\s*(\d+)', full, re.IGNORECASE)
    if part_m:
        fields["Part No"] = part_m.group(1)

    serial_m = re.search(r'(?:serial|sl\.?|क्रमांक)\s*(?:no\.?|number)?\s*[:\-]?\s*(\d+)', full, re.IGNORECASE)
    if serial_m:
        fields["Serial No"] = serial_m.group(1)

    poll_m = re.search(
        r'polling\s*station\s*[:\-]?\s*([A-Za-z0-9\s,\.]{4,80})',
        full, re.IGNORECASE)
    if poll_m:
        fields["Polling Station"] = poll_m.group(1).strip()

    state_pat = (
        r'\b(andhra\s*pradesh|arunachal\s*pradesh|assam|bihar|chhattisgarh|goa|gujarat|'
        r'haryana|himachal\s*pradesh|jharkhand|karnataka|kerala|madhya\s*pradesh|'
        r'maharashtra|manipur|meghalaya|mizoram|nagaland|odisha|punjab|rajasthan|'
        r'sikkim|tamil\s*nadu|telangana|tripura|uttar\s*pradesh|uttarakhand|'
        r'west\s*bengal|delhi|jammu|ladakh|chandigarh|puducherry)\b'
    )
    sm = re.search(state_pat, full, re.IGNORECASE)
    if sm:
        fields["State"] = sm.group(1).title()

    return fields


