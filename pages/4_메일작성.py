"""F-04~06: 공통 콜드메일 초안 작성 & 전체 발송 기록"""
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json
import streamlit as st
from services.database import (
    init_db, get_settings, get_all_companies,
    insert_history, check_duplicate,
)
from services.draft_generator import generate_draft, translate_draft, SUPPORTED_LANGUAGES
from services.attachment_guide import get_attachment_text, get_default_files

init_db()

st.set_page_config(page_title="메일 작성", page_icon="✉️", layout="wide")
st.title("✉️ 콜드메일 초안")

settings = get_settings()
api_key = settings.get("openai_api_key", "")
if not api_key:
    st.warning("⚠️ 먼저 [설정] 페이지에서 API 키를 저장하세요.")
    st.stop()

companies = get_all_companies()
with_drafts = [c for c in companies if c.get("draft_json")]

if not with_drafts:
    st.info("아직 생성된 초안이 없습니다. [업체검색] 페이지에서 검색을 시작하면 초안이 자동으로 생성됩니다.")
    st.stop()

# ── 세션 상태 초기화 (첫 진입 or 새 검색 후) ──────────────────────────
first_draft_key = with_drafts[0]["id"]
if st.session_state.get("draft_source") != first_draft_key:
    first_draft = json.loads(with_drafts[0]["draft_json"])
    st.session_state.mail_subject = first_draft.get("subject", "")
    st.session_state.mail_body = first_draft.get("body", "")
    st.session_state.draft_source = first_draft_key

# ── 상단 요약 ─────────────────────────────────────────────────────────
total = len(with_drafts)
sent_count = sum(1 for c in with_drafts if check_duplicate(c["id"]))
c1, c2, c3 = st.columns(3)
c1.metric("수신 업체 수", total)
c2.metric("발송 완료", sent_count)
c3.metric("미발송", total - sent_count)

st.divider()

# ── 카테고리 & 재생성 ─────────────────────────────────────────────────
col_cat, col_lang, col_btn = st.columns([2, 2, 1])
with col_cat:
    category = st.selectbox(
        "카테고리",
        ["샘플북제공", "제품제안", "신제품 안내"],
        index=["샘플북제공", "제품제안", "신제품 안내"].index(
            with_drafts[0].get("category", "샘플북제공")
            if with_drafts[0].get("category") in ["샘플북제공", "제품제안", "신제품 안내"]
            else "샘플북제공"
        ),
    )
with col_lang:
    tr_lang = st.selectbox(
        "번역 언어",
        ["없음"] + [k for k in SUPPORTED_LANGUAGES if k != "ko"],
        format_func=lambda x: "번역 안 함" if x == "없음" else SUPPORTED_LANGUAGES[x],
    )
with col_btn:
    st.write("")
    regen = st.button("🔄 재생성", use_container_width=True)

if regen:
    with st.spinner("초안 재생성 중..."):
        try:
            ref = with_drafts[0]
            new_draft = generate_draft(
                api_key=api_key,
                category=category,
                company_name=ref.get("company_name", ""),
                industry=ref.get("industry", ""),
                sender=settings,
            )
            if tr_lang != "없음":
                new_draft = translate_draft(api_key, new_draft, tr_lang)
            st.session_state.mail_subject = new_draft.get("subject", "")
            st.session_state.mail_body = new_draft.get("body", "")
            st.rerun()
        except Exception as e:
            st.error(f"오류: {e}")

# ── 제목 & 본문 ────────────────────────────────────────────────────────
st.text_input("제목", key="mail_subject")
st.text_area("본문", height=280, key="mail_body")

# ── 서명 & 첨부파일 ───────────────────────────────────────────────────
col_sig, col_att = st.columns(2)
with col_sig:
    sig = st.text_area(
        "서명",
        value=settings.get("signature_block") or (
            "\n".join(filter(None, [
                settings.get("sender_name", ""),
                settings.get("sender_title", ""),
                settings.get("sender_company", ""),
                settings.get("sender_phone", ""),
            ]))
        ),
        height=110,
    )
with col_att:
    attach_input = st.text_area(
        "첨부파일 (한 줄에 하나)",
        value="\n".join(get_default_files(category)),
        height=110,
    )

# ── 복사용 전체 텍스트 ────────────────────────────────────────────────
extra_files = [f.strip() for f in attach_input.splitlines()
               if f.strip() and f.strip() not in get_default_files(category)]
attach_guide = get_attachment_text(category, extra_files)
full_mail = (
    f"제목: {st.session_state.mail_subject}\n\n"
    f"{st.session_state.mail_body}"
    f"{attach_guide}\n\n"
    f"---\n{sig}"
)
st.divider()
st.text_area("📋 복사용 전체 텍스트", value=full_mail, height=220)

# ── BCC & 발송 기록 ────────────────────────────────────────────────────
st.divider()
email_list = [c.get("email", "") for c in with_drafts if c.get("email")]
bcc_str = ";".join(email_list)
st.text_area(f"📬 BCC 주소 ({total}개 업체, 복사 후 메일 클라이언트에 붙여넣기)", value=bcc_str, height=80)

note = st.text_input("메모 (전체 공통)", placeholder="특이사항 등")
if st.button("📬 전체 발송 기록 저장", type="primary", use_container_width=True):
    count = 0
    for c in with_drafts:
        insert_history({
            "company_id": c["id"],
            "company_name": c["company_name"],
            "category": category,
            "sender_name": settings.get("sender_name", ""),
            "draft_subject": st.session_state.mail_subject,
            "language": tr_lang if tr_lang != "없음" else "ko",
            "note": note,
        })
        count += 1
    st.success(f"총 {count}개 업체 발송 이력이 저장되었습니다.")
    st.rerun()
