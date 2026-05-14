"""F-01~04: 업체 리스트업 → URL 검증 → 이메일 검증 → 메일 초안 자동 생성"""
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
import pandas as pd
from services.database import (
    get_settings, get_all_companies, insert_company,
    delete_company, clear_companies, update_company, update_draft,
)
from services.agent_listup import search_companies
from services.url_checker import check_url
from services.email_validator import validate_email
from services.draft_generator import generate_draft

st.set_page_config(page_title="업체 검색", page_icon="🔍", layout="wide")
st.title("🔍 업체 리스트업")

settings = get_settings()
api_key = settings.get("openai_api_key", "")

if not api_key:
    st.warning("⚠️ 먼저 [설정] 페이지에서 OpenAI API 키를 저장하세요.")
    st.stop()

# ── 검색 조건 ──────────────────────────────────────────────────────────
st.subheader("검색 조건")

industry_type = st.text_input(
    "산업군",
    placeholder="예: 화장품 업체, 출판사, 식품 제조업체, IT 스타트업 ...",
)

col1, col2, col3 = st.columns(3)
with col1:
    category = st.selectbox(
        "메일 카테고리",
        ["샘플북제공", "제품제안", "신규안내"],
        help="자동 생성될 콜드메일의 주제 유형을 선택하세요.",
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

# ── 자동 전체 플로우 ───────────────────────────────────────────────────
if search_btn:
    if not industry_type.strip():
        st.warning("산업군을 입력하세요. (예: 화장품 업체, 출판사)")
        st.stop()

    with st.status("AI 에이전트가 작업 중입니다...", expanded=True) as status:

        # STEP 1: 업체 리스트업
        st.write("**[1/4]** 업체 리스트업 중...")
        try:
            results = search_companies(api_key, industry_type, rank_range, min_results)
        except Exception as e:
            status.update(label="오류 발생", state="error")
            st.error(f"업체 검색 오류: {e}")
            st.stop()

        cids = []
        for r in results:
            r["rank_range"] = rank_range
            r["category"] = category
            cid = insert_company(r)
            cids.append((cid, r))
        st.write(f"✅ {len(results)}개 업체 수집 완료")

        # STEP 2: URL 검증
        st.write("**[2/4]** 홈페이지 접속 확인 중...")
        prog2 = st.progress(0)
        for i, (cid, r) in enumerate(cids):
            url_status, final_url = check_url(r.get("website_url", ""))
            update_company(cid, {"url_status": url_status, "website_url": final_url})
            prog2.progress((i + 1) / len(cids))
        st.write("✅ URL 검증 완료")

        # STEP 3: 이메일 검증
        st.write("**[3/4]** 이메일 주소 검증 중...")
        prog3 = st.progress(0)
        all_companies = get_all_companies()
        new_companies = [c for c in all_companies if c["id"] in {cid for cid, _ in cids}]
        for i, c in enumerate(new_companies):
            if c.get("url_status") == "accessible":
                email, email_status = validate_email(c.get("website_url", ""))
            else:
                email, email_status = "", "unknown"
            update_company(c["id"], {"email": email, "email_status": email_status})
            prog3.progress((i + 1) / len(new_companies))
        st.write("✅ 이메일 검증 완료")

        # STEP 4: 메일 초안 자동 생성
        st.write("**[4/4]** 콜드메일 초안 생성 중...")
        prog4 = st.progress(0)
        all_companies = get_all_companies()
        new_companies = [c for c in all_companies if c["id"] in {cid for cid, _ in cids}]
        success_count = 0
        for i, c in enumerate(new_companies):
            try:
                draft = generate_draft(
                    api_key=api_key,
                    category=category,
                    company_name=c["company_name"],
                    industry=c.get("industry", ""),
                    sender=settings,
                )
                update_draft(c["id"], draft)
                success_count += 1
            except Exception:
                pass
            prog4.progress((i + 1) / len(new_companies))
        st.write(f"✅ {success_count}개 초안 생성 완료")

        status.update(
            label=f"완료 — {len(results)}개 업체 처리, {success_count}개 초안 생성",
            state="complete",
        )
    st.rerun()

# ── 업체 목록 표시 ─────────────────────────────────────────────────────
st.divider()
st.subheader("업체 목록")

companies = get_all_companies()
if not companies:
    st.info("검색 결과가 없습니다. 위에서 AI 검색을 실행하세요.")
    st.stop()

STATUS_EMOJI = {
    "accessible": "✅", "inaccessible": "❌", "needs_review": "⚠️",
    "confirmed": "✅", "estimated": "🔶", "unknown": "❓",
}

df = pd.DataFrame(companies)
display_cols = ["company_name", "industry", "url_status", "email", "email_status", "category", "rank_range"]
display_cols = [c for c in display_cols if c in df.columns]
df_display = df[display_cols].copy()
for col in ["url_status", "email_status"]:
    if col in df_display.columns:
        df_display[col] = df_display[col].map(lambda v: STATUS_EMOJI.get(v, v or "-"))

df_display.columns = [
    {"company_name": "업체명", "industry": "업종", "url_status": "URL",
     "email": "이메일", "email_status": "이메일상태",
     "category": "카테고리", "rank_range": "순위구간"}.get(c, c)
    for c in display_cols
]
st.dataframe(df_display, use_container_width=True)
st.caption(f"총 {len(companies)}개 업체 | 초안 생성 완료: {sum(1 for c in companies if c.get('draft_json'))}개")

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
                insert_company({"company_name": nm, "industry": ind,
                                "website_url": url, "category": cat2, "rank_range": "-"})
                st.success(f"'{nm}' 추가 완료")
                st.rerun()
            else:
                st.error("업체명은 필수입니다.")

# ── 개별 삭제 ─────────────────────────────────────────────────────────
with st.expander("🗑️ 업체 삭제"):
    names = {c["company_name"]: c["id"] for c in companies}
    selected = st.selectbox("삭제할 업체 선택", list(names.keys()))
    if st.button("삭제"):
        delete_company(names[selected])
        st.success(f"'{selected}' 삭제 완료")
        st.rerun()
