import json
import streamlit as st


def render_sidebar(*, supabase, auth_logout_fn, load_extractions_fn):
    with st.sidebar:
        st.markdown(
            """
        <div style="display:flex;align-items:center;justify-content:space-between;
            padding:14px 0 8px;border-bottom:1px solid #e8eaf0;margin-bottom:4px;">
            <div style="display:flex;align-items:center;gap:9px;">
                <div style="width:28px;height:28px;
                    background:linear-gradient(135deg,#4f46e5,#818cf8);
                    border-radius:7px;display:flex;align-items:center;
                    justify-content:center;font-size:0.85rem;">📝</div>
                <div>
                    <div style="font-weight:800;font-size:0.88rem;
                        color:#1a1a2e;line-height:1.1;">OCR Stream</div>
                    <div style="font-size:0.58rem;color:#9ca3af;
                        font-family:'DM Mono',monospace;letter-spacing:0.5px;">
                        Document Extractor</div>
                </div>
            </div>
        </div>""",
            unsafe_allow_html=True,
        )

        st.markdown('<div class="logout-btn">', unsafe_allow_html=True)
        if st.button("⏻  Logout", key="sb_logout", use_container_width=True):
            auth_logout_fn(supabase)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<div class="sb-header">🗂 Saved Extractions</div>', unsafe_allow_html=True)
        sb_r1, sb_r2 = st.columns([4, 1])
        with sb_r2:
            if st.button("↺", key="sb_refresh", help="Refresh"):
                st.rerun()

        records = load_extractions_fn(supabase)

        if not records:
            st.markdown(
                """
            <div style="text-align:center;padding:24px 8px 16px;color:#9ca3af;">
                <div style="font-size:1.6rem;opacity:0.3;margin-bottom:6px;">🗃️</div>
                <div style="font-size:0.76rem;font-weight:600;">No extractions yet</div>
                <div style="font-size:0.63rem;font-family:'DM Mono',monospace;margin-top:3px;">
                    Extract a document to see it here
                </div>
            </div>""",
                unsafe_allow_html=True,
            )
        else:
            type_counts = {}
            for r in records:
                t = r.get("doc_type", "other")
                type_counts[t] = type_counts.get(t, 0) + 1

            label_map = {"aadhaar": "Aadhaar", "pan": "PAN", "dl": "DL", "voter": "Voter", "other": "Other"}
            badges_html = " ".join(
                f'<span class="sb-record-badge sb-badge-{t}">{label_map.get(t,t)} {c}</span>' for t, c in type_counts.items()
            )
            st.markdown(
                f'<div style="margin-bottom:8px;line-height:2.4;">{badges_html}'
                f'<span style="font-size:0.62rem;color:#9ca3af;margin-left:4px;">'
                f'({len(records)} total)</span></div>',
                unsafe_allow_html=True,
            )

            search_q = st.text_input("search", placeholder="🔍  Search by name, number…", key="sb_search", label_visibility="collapsed")

            for r in records:
                ts = r.get("created_at", "")[:16].replace("T", " ")
                dtype = r.get("doc_type", "other")
                dlabel = label_map.get(dtype, dtype.title())
                name = r.get("holder_name") or "—"
                rid = r.get("id", "x")

                if dtype == "aadhaar":
                    keys = [("Name", "holder_name"), ("Aadhaar No", "aadhaar_number"), ("DOB", "dob"), ("Gender", "gender"), ("Address", "address"), ("Pincode", "pincode"), ("State", "state"), ("VID", "vid"), ("Enrolment", "enrolment_no"), ("Mobile", "mobile")]
                elif dtype == "pan":
                    keys = [("Name", "holder_name"), ("PAN No", "pan_number"), ("Father", "father_name"), ("DOB", "dob"), ("Acct Type", "account_type"), ("Issued By", "issued_by")]
                elif dtype == "dl":
                    keys = [("Name", "holder_name"), ("DL No", "dl_number"), ("Issued", "date_of_issue"), ("Valid Till", "valid_till"), ("DOB", "dob"), ("Blood", "blood_group"), ("Vehicle", "vehicle_class"), ("S/D/W of", "son_daughter_wife_of"), ("Authority", "issuing_authority"), ("State", "state")]
                elif dtype == "voter":
                    keys = [("Name", "holder_name"), ("EPIC No", "epic_number"), ("Father/Husb", "father_husband_name"), ("DOB", "dob"), ("Gender", "gender"), ("Constitency", "constituency"), ("Part No", "part_no"), ("Serial No", "serial_no"), ("State", "state")]
                else:
                    keys = [("Raw Text", "raw_text")]

                display = {label: r[col] for label, col in keys if r.get(col)}
                if search_q:
                    searchable = " ".join(str(v) for v in display.values()).lower()
                    if search_q.lower() not in searchable:
                        continue

                doc_num = r.get("aadhaar_number") or r.get("pan_number") or r.get("dl_number") or r.get("epic_number") or ""
                short_num = (doc_num[:10] + "…") if len(doc_num) > 10 else doc_num

                with st.expander(f"{dlabel} · {name}", expanded=False):
                    st.markdown(
                        f'<span class="sb-ts">{ts}{(" · " + short_num) if short_num else ""}</span>',
                        unsafe_allow_html=True,
                    )
                    stored_url = r.get("photo_url", "")
                    if stored_url:
                        st.image(stored_url, width=64, caption="ID Photo")

                    rows_html = "".join(
                        f'<div class="sb-kv-row"><span class="sb-key">{k}</span><span class="sb-val">{v}</span></div>'
                        for k, v in display.items()
                    )
                    st.markdown(f'<div class="sb-kv">{rows_html}</div>', unsafe_allow_html=True)
                    st.download_button(
                        "⬇ JSON",
                        data=json.dumps(display, indent=2, ensure_ascii=False),
                        file_name=f"{dtype}_{rid[:8]}.json",
                        mime="application/json",
                        key=f"sb_dl_{rid}",
                        use_container_width=True,
                    )

        st.markdown('<div class="sb-header">🔴 Failure Log</div>', unsafe_allow_html=True)
        fail_count = len(st.session_state.failure_log)

        if fail_count == 0:
            st.markdown(
                "<p style='color:#9ca3af;font-size:0.73rem;font-family:monospace;text-align:center;padding:6px 0 0;margin:0;'>No failures ✓</p>",
                unsafe_allow_html=True,
            )
        else:
            fl_c1, fl_c2 = st.columns([3, 1])
            with fl_c1:
                st.markdown(
                    f"<p style='color:#dc2626;font-size:0.73rem;font-weight:700;margin:4px 0;'>{fail_count} error(s)</p>",
                    unsafe_allow_html=True,
                )
            with fl_c2:
                if st.button("🗑", key="sb_clear_log", help="Clear log"):
                    st.session_state.failure_log = []
                    st.rerun()

            entries_html = "".join(
                f'<div class="fail-entry-sb"><span class="fail-ts-sb">[{e["ts"]}] <span class="fail-ctx-sb">{e["ctx"]}</span></span><span class="fail-msg-sb">{e["msg"]}</span></div>'
                for e in reversed(st.session_state.failure_log)
            )
            st.markdown(
                f'<div style="background:#fff9f9;border:1px solid #fecaca;border-radius:8px;padding:10px 12px;max-height:220px;overflow-y:auto;margin-top:6px;">{entries_html}</div>',
                unsafe_allow_html=True,
            )

            log_text = "\n".join(f"[{e['ts']}] [{e['ctx']}] {e['msg']}" for e in st.session_state.failure_log)
            st.download_button(
                "⬇ Download Log",
                data=log_text,
                file_name="failure_log.txt",
                mime="text/plain",
                key="sb_dl_log",
                use_container_width=True,
            )
