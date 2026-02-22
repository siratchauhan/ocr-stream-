
def render_kv_table(fields):
    if not fields:
        return "<p style='color:#9ca3af;font-style:italic;font-size:0.82rem;'>No fields extracted.</p>"
    rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in fields.items())
    return f"""<table class=\"kv-table\">\n        <thead><tr><th>Field</th><th>Value</th></tr></thead>\n        <tbody>{rows}</tbody></table>"""


def render_confidence_bar(score):
    pct = min(max(int(score * 100), 0), 100)
    cls = "conf-high" if pct >= 70 else ("conf-mid" if pct >= 40 else "conf-low")
    return f"""<div class=\"conf-wrap\">\n        <span class=\"conf-label\">Confidence</span>\n        <div class=\"conf-bg\"><div class=\"conf-fill {cls}\" style=\"width:{pct}%\"></div></div>\n        <span class=\"conf-pct\">{pct}%</span></div>"""


def photo_html(b64, name="", doc_type=""):
    if b64:
        photo_div = f'<div class="photo-frame"><img src="data:image/jpeg;base64,{b64}"/></div>'
    else:
        photo_div = '<div class="photo-placeholder">👤<br/>No photo</div>'
    sub_map = {
        "aadhaar": "Aadhaar Card Holder · भारत सरकार",
        "pan": "PAN Card Holder · Income Tax Dept.",
        "dl": "Driving Licence Holder · Transport Dept.",
        "voter": "Voter ID Holder · Election Commission",
    }
    sub = sub_map.get(doc_type, "")
    return f"""<div class=\"photo-card\">\n        {photo_div}\n        <div class=\"photo-meta\">\n            <div class=\"photo-label\">ID Card Holder</div>\n            <div class=\"photo-name\">{name or '—'}</div>\n            <div class=\"photo-sub\">{sub}</div>\n        </div></div>"""
