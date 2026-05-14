"""F-04~06: 자동 생성된 콜드메일 초안 확인 & 편집 & 발송 기록"""
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import json
import streamlit as st
from services.database import (
    get_settings, get_all_companies, insert_history,
    check_duplicate, update_draft,
)
from services.draft_generator import generate_draft, translate_draft, SUPPORTED_LANGUAGES
from services.attachment_guide import get_attachment_text, get_default_files

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

# ── 상단 요약 ─────────────────────────────────────────────────────────
total = len(with_drafts)
sent_count = sum(1 for c in with_drafts if check_duplicate(c["id"]))
col1, col2, col3 = st.columns(3)
col1.metric("전체 초안", total)
col2.metric("발송 완료", sent_count)
col3.metric("미발송", total - sent_count)
st.divider()

# ── 업체별 초안 ────────────────────────────────────────────────────────
for c in with_drafts:
    try:
        draft = json.loads(c["draft_json"])
    except Exception:
        continue

    cid = c["id"]
    is_sent = check_duplicate(cid)
    sent_label = " ✅ 발송됨" if is_sent else ""
    email_label = c.get("email", "이메일 없음")

    with st.expander(f"**{c['company_name']}** | {c.get('industry', '-')} | {email_label}{sent_label}"):

        if is_sent:
            st.warning("⚠️ 최근 30일 이내에 발송한 이력이 있습니다.")

        col_l, col_r = st.columns([3, 1])

        with col_l:
            new_subject = st.text_input(
                "제목", value=draft.get("subject", ""), key=f"subj_{cid}"
            )
            new_body = st.text_area(
                "본문", value=draft.get("body", ""), height=180, key=f"body_{cid}"
            )
            dept = st.text_input(
                "전달 부서", value=draft.get("target_dept", ""), key=f"dept_{cid}"
            )

        with col_r:
            category = st.selectbox(
                "카테고리",
                ["샘플북제공", "제품제안", "신규안내"],
                index=["샘플북제공", "제품제안", "신규안내"].index(
                    c.get("category", "샘플북제공")
                    if c.get("category") in ["샘플북제공", "제품제안", "신규안내"]
                    else "샘플북제공"
                ),
                key=f"cat_{cid}",
            )
            sig = st.text_area(
                "서명", value=draft.get("signature", ""), height=110, key=f"sig_{cid}"
            )
            attach_files = st.text_area(
                "첨부파일 (한 줄에 하나)",
                value="\n".join(get_default_files(category)),
                height=80,
                key=f"att_{cid}",
            )

        # 복사용 전체 텍스트
        attach_guide = get_attachment_text(
            category,
            [f.strip() for f in attach_files.splitlines()
             if f.strip() and f.strip() not in get_default_files(category)],
        )
        full_mail = (
            f"수신: {c.get('email', '')}\n"
            f"제목: {new_subject}\n\n"
            f"{new_body}"
            f"{attach_guide}\n\n"
            f"---\n{sig}"
        )
        st.text_area("📋 복사용 전체 텍스트", value=full_mail, height=200, key=f"copy_{cid}")

        # 액션 버튼
        btn1, btn2, btn3, btn4 = st.columns(4)

        with btn1:
            if st.button("🔄 재생성", key=f"regen_{cid}"):
                with st.spinner("초안 재생성 중..."):
                    try:
                        new_draft = generate_draft(
                            api_key=api_key,
                            category=category,
                            company_name=c["company_name"],
                            industry=c.get("industry", ""),
                            sender=settings,
                        )
                        update_draft(cid, new_draft)
                        st.success("재생성 완료!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

        with btn2:
            if st.button("💾 초안 저장", key=f"save_{cid}"):
                updated = {**draft, "subject": new_subject, "body": new_body,
                           "target_dept": dept, "signature": sig}
                update_draft(cid, updated)
                st.success("저장 완료!")

        with btn3:
            tr_lang = st.selectbox(
                "번역",
                [k for k in SUPPORTED_LANGUAGES if k != "ko"],
                format_func=lambda x: SUPPORTED_LANGUAGES[x],
                key=f"trlang_{cid}",
            )
            if st.button("🌍 번역", key=f"tr_{cid}"):
                with st.spinner("번역 중..."):
                    try:
                        translated = translate_draft(
                            api_key, {"subject": new_subject, "body": new_body}, tr_lang
                        )
                        update_draft(cid, {**draft,
                                           "subject": translated["subject"],
                                           "body": translated["body"],
                                           "language": tr_lang})
                        st.success("번역 완료!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"오류: {e}")

        with btn4:
            note = st.text_input("메모", key=f"note_{cid}", placeholder="특이사항")
            if st.button("📬 발송 기록", key=f"sent_{cid}", type="primary"):
                insert_history({
                    "company_id": cid,
                    "company_name": c["company_name"],
                    "category": category,
                    "sender_name": settings.get("sender_name", ""),
                    "draft_subject": new_subject,
                    "language": draft.get("language", "ko"),
                    "note": note,
                })
                st.success(f"'{c['company_name']}' 발송 이력 저장 완료!")
                st.rerun()
