"""F-07 + F-08: BCC 생성 & 엑셀 다운로드"""
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
from services.database import get_all_companies
from services.bcc_builder import build_bcc
from services.excel_exporter import export_xlsx, get_filename

st.set_page_config(page_title="발송 준비", page_icon="📤", layout="wide")
st.title("📤 발송 준비")

companies = get_all_companies()
if not companies:
    st.info("업체 목록이 없습니다. 먼저 [업체검색] 페이지를 완료하세요.")
    st.stop()

# ── 필터 ─────────────────────────────────────────────────────────────
st.subheader("이메일 필터 옵션")
col1, col2 = st.columns(2)
with col1:
    include_confirmed = st.checkbox("✅ 확인됨 (confirmed)", value=True)
    include_estimated = st.checkbox("🔶 추정 (estimated)", value=True)
with col2:
    include_unknown = st.checkbox("❓ 미확인 (unknown)", value=False)

include_statuses = []
if include_confirmed:
    include_statuses.append("confirmed")
if include_estimated:
    include_statuses.append("estimated")
if include_unknown:
    include_statuses.append("unknown")

# ── BCC 생성 ─────────────────────────────────────────────────────────
st.divider()
st.subheader("📋 BCC 주소 일괄 생성")

bcc_data = build_bcc(companies, include_statuses)
st.metric("BCC 주소 수", bcc_data["total_count"])

if bcc_data["duplicate_domains"]:
    st.warning(f"중복 도메인 발견: {', '.join(bcc_data['duplicate_domains'])}")

if bcc_data["bcc_string"]:
    st.text_area(
        "BCC 주소 (복사하여 메일 클라이언트에 붙여넣기)",
        value=bcc_data["bcc_string"],
        height=120,
    )
    st.caption("Outlook/Gmail의 BCC 필드에 위 전체 텍스트를 붙여넣으세요.")

    # 주소 목록 표시
    with st.expander("📧 개별 주소 목록"):
        for i, email in enumerate(bcc_data["emails"], 1):
            st.text(f"{i:3d}. {email}")
else:
    st.info("선택한 조건에 해당하는 이메일 주소가 없습니다.")

# ── 엑셀 다운로드 ────────────────────────────────────────────────────
st.divider()
st.subheader("📊 엑셀 다운로드")

col3, col4 = st.columns(2)
with col3:
    sheet_mode = st.radio(
        "시트 구성",
        ["all", "confirmed", "unknown"],
        format_func={"all": "전체 (시트 분리)", "confirmed": "검증완료만", "unknown": "미확인만"}.get,
    )
with col4:
    st.markdown("**포함 컬럼**")
    st.markdown("업체명 / 업종 / 홈페이지 URL / 이메일 / 검증상태 / URL상태 / 카테고리 / 순위구간")

xlsx_bytes = export_xlsx(companies, sheet_mode)
fname = get_filename()

st.download_button(
    label="⬇️ 엑셀 다운로드",
    data=xlsx_bytes,
    file_name=fname,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    type="primary",
)

# ── 요약 통계 ────────────────────────────────────────────────────────
st.divider()
st.subheader("요약 통계")

total = len(companies)
accessible = sum(1 for c in companies if c.get("url_status") == "accessible")
confirmed = sum(1 for c in companies if c.get("email_status") == "confirmed")
estimated = sum(1 for c in companies if c.get("email_status") == "estimated")
unknown = sum(1 for c in companies if c.get("email_status") == "unknown")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("전체", total)
c2.metric("접속가능", accessible)
c3.metric("이메일 확인됨", confirmed)
c4.metric("이메일 추정", estimated)
c5.metric("이메일 미확인", unknown)
