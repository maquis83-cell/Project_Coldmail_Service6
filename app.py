"""콜드메일 AI 에이전트 — 메인 대시보드 (F-11)"""
import sys
import os
# Streamlit Cloud: ensure project root is on sys.path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
import pandas as pd
from services.database import init_db, get_stats, get_all_companies

st.set_page_config(
    page_title="콜드메일 AI 에이전트",
    page_icon="📨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# DB 초기화 (최초 실행 시)
init_db()

# ── 사이드바 안내 ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📨 콜드메일 AI 에이전트")
    st.markdown("""
**작업 순서:**

1. ⚙️ **설정** — API 키 & 발신자 정보
2. 🔍 **업체검색** — AI로 업체 목록 수집
3. ✅ **검증** — URL & 이메일 확인
4. ✉️ **메일작성** — Claude 초안 생성
5. 📤 **발송준비** — BCC & 엑셀 다운로드
6. 📜 **발송이력** — 이력 관리
7. 📝 **템플릿** — 프롬프트 관리
""")
    st.divider()
    st.caption("Powered by Claude claude-sonnet-4-20250514")

# ── 대시보드 헤더 ──────────────────────────────────────────────────────
st.title("📨 콜드메일 AI 에이전트")
st.markdown("B2B 콜드메일 자동화 — 업체 탐색부터 발송 준비까지")
st.divider()

# ── 핵심 지표 카드 ─────────────────────────────────────────────────────
stats = get_stats()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("전체 업체", stats["total_companies"])
col2.metric("이메일 확인됨", stats["verified_count"])
col3.metric("발송 완료", stats["sent_count"])
col4.metric(
    "URL 미검증",
    stats["pending_url"],
    delta=f"-{stats['pending_url']}" if stats["pending_url"] else None,
    delta_color="inverse",
)
col5.metric(
    "이메일 미검증",
    stats["pending_email"],
    delta=f"-{stats['pending_email']}" if stats["pending_email"] else None,
    delta_color="inverse",
)

# ── 진행 현황 ─────────────────────────────────────────────────────────
st.divider()
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("카테고리별 발송 현황")
    if stats["category_breakdown"]:
        cat_df = pd.DataFrame(
            list(stats["category_breakdown"].items()),
            columns=["카테고리", "발송 수"],
        )
        st.bar_chart(cat_df.set_index("카테고리"))
    else:
        st.info("발송 이력이 없습니다.")

with col_right:
    st.subheader("최근 7일 활동")
    if stats["recent_activity"]:
        activity_df = pd.DataFrame(stats["recent_activity"])
        activity_df = activity_df.rename(columns={"target": "업체명", "ts": "일시"})
        st.dataframe(activity_df[["업체명", "일시"]], use_container_width=True)
    else:
        st.info("최근 활동이 없습니다.")

# ── 미완료 항목 안내 ─────────────────────────────────────────────────
st.divider()
st.subheader("🔔 미완료 항목")

alerts = []
if stats["pending_url"] > 0:
    alerts.append(f"⚠️ URL 미검증 업체 **{stats['pending_url']}개** — [검증] 페이지에서 처리하세요.")
if stats["pending_email"] > 0:
    alerts.append(f"⚠️ 이메일 미검증 업체 **{stats['pending_email']}개** — [검증] 페이지에서 처리하세요.")
if stats["total_companies"] == 0:
    alerts.append("📌 업체가 없습니다. [설정] 페이지에서 API 키를 설정하고 [업체검색]을 시작하세요.")

if alerts:
    for a in alerts:
        st.markdown(a)
else:
    st.success("✅ 모든 업체가 검증되었습니다. [메일작성]으로 이동하세요.")

# ── 업체 현황 테이블 (간략) ────────────────────────────────────────────
companies = get_all_companies()
if companies:
    st.divider()
    st.subheader("업체 현황 요약")
    df = pd.DataFrame(companies)

    STATUS_LABEL = {
        "accessible": "✅", "inaccessible": "❌", "needs_review": "⚠️", None: "-",
        "confirmed": "✅", "estimated": "🔶", "unknown": "❓",
    }

    summary_cols = ["company_name", "industry", "url_status", "email_status", "category"]
    summary_cols = [c for c in summary_cols if c in df.columns]
    df_s = df[summary_cols].copy()
    for col in ["url_status", "email_status"]:
        if col in df_s.columns:
            df_s[col] = df_s[col].map(STATUS_LABEL)
    df_s.columns = ["업체명", "업종", "URL", "이메일", "카테고리"][:len(summary_cols)]
    st.dataframe(df_s.head(20), use_container_width=True)
    if len(companies) > 20:
        st.caption(f"상위 20개 표시 중 (전체 {len(companies)}개)")
