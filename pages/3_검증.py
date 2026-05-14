"""F-02 + F-03: URL 접속 확인 & 이메일 검증"""
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
import pandas as pd
from services.database import get_all_companies, update_company
from services.url_checker import check_url
from services.email_validator import validate_email

st.set_page_config(page_title="검증", page_icon="✅", layout="wide")
st.title("✅ 홈페이지 & 이메일 검증")

companies = get_all_companies()
if not companies:
    st.info("먼저 [업체검색] 페이지에서 업체를 수집하세요.")
    st.stop()

total = len(companies)
url_done = sum(1 for c in companies if c.get("url_status"))
email_done = sum(1 for c in companies if c.get("email_status"))

col1, col2, col3 = st.columns(3)
col1.metric("전체 업체", total)
col2.metric("URL 검증 완료", url_done)
col3.metric("이메일 검증 완료", email_done)

st.divider()

# ── STEP 1: URL 검증 ────────────────────────────────────────────────────
st.subheader("STEP 1 — 홈페이지 접속 확인")
pending_url = [c for c in companies if not c.get("url_status")]
st.write(f"미검증: {len(pending_url)}개 / 전체: {total}개")

if st.button("🌐 URL 검증 시작", type="primary", disabled=len(pending_url) == 0):
    progress = st.progress(0)
    status_text = st.empty()
    targets = pending_url if pending_url else companies

    for i, c in enumerate(targets):
        status_text.text(f"[{i+1}/{len(targets)}] {c['company_name']} 확인 중...")
        url_status, final_url = check_url(c.get("website_url", ""))
        update_company(c["id"], {"url_status": url_status, "website_url": final_url})
        progress.progress((i + 1) / len(targets))

    status_text.success("URL 검증 완료!")
    st.rerun()

# ── STEP 2: 이메일 검증 ─────────────────────────────────────────────────
st.divider()
st.subheader("STEP 2 — 이메일 주소 검증")

companies = get_all_companies()
accessible = [c for c in companies if c.get("url_status") == "accessible"]
pending_email = [c for c in accessible if not c.get("email_status")]

st.write(f"접속가능 업체: {len(accessible)}개 / 이메일 미검증: {len(pending_email)}개")

if len(accessible) == 0:
    st.warning("접속 가능한 업체가 없습니다. 먼저 URL 검증을 완료하세요.")
elif st.button("📧 이메일 검증 시작", type="primary", disabled=len(pending_email) == 0):
    progress2 = st.progress(0)
    status_text2 = st.empty()
    targets2 = pending_email if pending_email else accessible

    for i, c in enumerate(targets2):
        status_text2.text(f"[{i+1}/{len(targets2)}] {c['company_name']} 이메일 검색 중...")
        email, email_status = validate_email(c.get("website_url", ""))
        update_company(c["id"], {"email": email, "email_status": email_status})
        progress2.progress((i + 1) / len(targets2))

    status_text2.success("이메일 검증 완료!")
    st.rerun()

# ── 결과 테이블 ────────────────────────────────────────────────────────
st.divider()
st.subheader("검증 결과")

companies = get_all_companies()
STATUS_EMOJI = {
    "accessible": "✅ 접속가능", "inaccessible": "❌ 불가", "needs_review": "⚠️ 재확인",
    "confirmed": "✅ 확인됨", "estimated": "🔶 추정", "unknown": "❓ 미확인",
}

df = pd.DataFrame(companies)
if not df.empty:
    show_cols = ["company_name", "website_url", "url_status", "email", "email_status"]
    show_cols = [c for c in show_cols if c in df.columns]
    df_show = df[show_cols].copy()
    for col in ["url_status", "email_status"]:
        if col in df_show.columns:
            df_show[col] = df_show[col].map(lambda v: STATUS_EMOJI.get(v, v or "-"))
    df_show.columns = ["업체명", "홈페이지", "URL상태", "이메일", "이메일상태"][:len(show_cols)]
    st.dataframe(df_show, use_container_width=True)
