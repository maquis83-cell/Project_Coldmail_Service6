"""F-01: AI Agent 업체 리스트업"""
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
import pandas as pd
from services.database import get_settings, get_all_companies, insert_company, delete_company, clear_companies
from services.agent_listup import search_companies

st.set_page_config(page_title="업체 검색", page_icon="🔍", layout="wide")
st.title("🔍 업체 리스트업")

settings = get_settings()
api_key = settings.get("openai_api_key", "")

if not api_key:
    st.warning("⚠️ 먼저 [설정] 페이지에서 OpenAI API 키를 저장하세요.")
    st.stop()

# ── 검색 조건 ───────────────────────────────────────────────────────────
st.subheader("검색 조건")
col1, col2, col3 = st.columns(3)
with col1:
    category = st.selectbox(
        "카테고리",
        ["샘플북제공", "제품제안", "신규안내"],
        index=["샘플북제공", "제품제안", "신규안내"].index(
            settings.get("default_category") or "샘플북제공"
        ) if settings.get("default_category") in ["샘플북제공", "제품제안", "신규안내"] else 0,
    )
with col2:
    rank_range = st.selectbox(
        "매출 순위 구간",
        ["1~50", "51~100", "101~150", "151~200"],
    )
with col3:
    min_results = st.number_input("최소 업체 수", min_value=5, max_value=50, value=10)

col_btn1, col_btn2 = st.columns([1, 5])
with col_btn1:
    search_btn = st.button("🤖 AI 검색 시작", type="primary")
with col_btn2:
    clear_btn = st.button("🗑️ 전체 초기화", type="secondary")

if clear_btn:
    clear_companies()
    st.success("업체 목록이 초기화되었습니다.")
    st.rerun()

if search_btn:
    with st.status("AI 에이전트가 업체를 탐색 중입니다...", expanded=True) as status:
        st.write(f"카테고리: **{category}** / 순위 구간: **{rank_range}위**")
        try:
            results = search_companies(api_key, category, rank_range, min_results)
            st.write(f"✅ {len(results)}개 업체 수집 완료")
            for r in results:
                r["category"] = category
                r["rank_range"] = rank_range
                insert_company(r)
            status.update(label=f"완료 — {len(results)}개 업체 저장됨", state="complete")
        except Exception as e:
            status.update(label="오류 발생", state="error")
            st.error(f"오류: {e}")
    st.rerun()

# ── 업체 목록 표시 ─────────────────────────────────────────────────────
st.divider()
st.subheader("업체 목록")

companies = get_all_companies()
if not companies:
    st.info("검색 결과가 없습니다. 위에서 AI 검색을 실행하세요.")
    st.stop()

df = pd.DataFrame(companies)
display_cols = ["company_name", "industry", "website_url", "url_status", "email", "email_status", "category", "rank_range"]
display_cols = [c for c in display_cols if c in df.columns]

STATUS_EMOJI = {
    "accessible": "✅", "inaccessible": "❌", "needs_review": "⚠️",
    "confirmed": "✅", "estimated": "🔶", "unknown": "❓",
}

def fmt_status(val):
    return STATUS_EMOJI.get(val, val or "-")

df_display = df[display_cols].copy()
for col in ["url_status", "email_status"]:
    if col in df_display.columns:
        df_display[col] = df_display[col].map(fmt_status)

df_display.columns = [
    {"company_name": "업체명", "industry": "업종", "website_url": "URL",
     "url_status": "URL상태", "email": "이메일", "email_status": "이메일상태",
     "category": "카테고리", "rank_range": "순위구간"}.get(c, c)
    for c in display_cols
]

st.dataframe(df_display, use_container_width=True)
st.caption(f"총 {len(companies)}개 업체")

# ── 수동 추가 ─────────────────────────────────────────────────────────
with st.expander("➕ 업체 수동 추가"):
    with st.form("add_company"):
        c1, c2 = st.columns(2)
        with c1:
            nm = st.text_input("업체명 *")
            ind = st.text_input("업종")
        with c2:
            url = st.text_input("홈페이지 URL")
            cat2 = st.selectbox("카테고리", ["샘플북제공", "제품제안", "신규안내"])
        if st.form_submit_button("추가"):
            if nm:
                insert_company({"company_name": nm, "industry": ind, "website_url": url, "category": cat2, "rank_range": "-"})
                st.success(f"'{nm}' 추가 완료")
                st.rerun()
            else:
                st.error("업체명은 필수입니다.")

# ── 개별 삭제 ──────────────────────────────────────────────────────────
with st.expander("🗑️ 업체 삭제"):
    names = {c["company_name"]: c["id"] for c in companies}
    selected = st.selectbox("삭제할 업체 선택", list(names.keys()))
    if st.button("삭제"):
        delete_company(names[selected])
        st.success(f"'{selected}' 삭제 완료")
        st.rerun()
