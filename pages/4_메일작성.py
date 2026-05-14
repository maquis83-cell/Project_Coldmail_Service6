"""F-04 + F-05 + F-06: 콜드메일 초안 작성 & 번역 & 첨부파일"""
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
from services.database import get_settings, get_all_companies, insert_history, check_duplicate
from services.draft_generator import generate_draft, translate_draft, SUPPORTED_LANGUAGES
from services.attachment_guide import get_attachment_text, get_default_files
from services.template_manager import list_templates

st.set_page_config(page_title="메일 작성", page_icon="✉️", layout="wide")
st.title("✉️ 콜드메일 초안 작성")

settings = get_settings()
api_key = settings.get("anthropic_api_key", "")
if not api_key:
    st.warning("⚠️ 먼저 [설정] 페이지에서 API 키를 저장하세요.")
    st.stop()

companies = get_all_companies()
verified = [c for c in companies if c.get("email_status") in ("confirmed", "estimated")]
if not verified:
    st.info("이메일이 검증된 업체가 없습니다. 먼저 [검증] 페이지를 완료하세요.")
    st.stop()

# ── 업체 선택 ─────────────────────────────────────────────────────────
st.subheader("업체 선택")
company_options = {f"{c['company_name']} ({c.get('industry', '-')})": c for c in verified}
selected_label = st.selectbox("메일을 작성할 업체", list(company_options.keys()))
selected = company_options[selected_label]

# 중복 발송 경고
if check_duplicate(selected["id"]):
    st.warning("⚠️ 이 업체에는 최근 30일 이내에 발송한 이력이 있습니다. 계속하시겠습니까?")

col1, col2 = st.columns(2)
with col1:
    category = st.selectbox(
        "카테고리",
        ["샘플북제공", "제품제안", "신규안내"],
        index=["샘플북제공", "제품제안", "신규안내"].index(
            selected.get("category", "샘플북제공")
            if selected.get("category") in ["샘플북제공", "제품제안", "신규안내"]
            else "샘플북제공"
        ),
    )
with col2:
    target_lang = st.selectbox(
        "출력 언어",
        list(SUPPORTED_LANGUAGES.keys()),
        format_func=lambda x: SUPPORTED_LANGUAGES[x],
        index=list(SUPPORTED_LANGUAGES.keys()).index(settings.get("default_language", "ko")),
    )

# 템플릿 선택
templates = list_templates()
template_options = {"기본 프롬프트 사용": None}
template_options.update({t["name"]: t for t in templates})
selected_tmpl_name = st.selectbox("사용할 템플릿", list(template_options.keys()))
custom_system = None
if selected_tmpl_name != "기본 프롬프트 사용":
    custom_system = template_options[selected_tmpl_name]["system_prompt"]

# ── 초안 생성 ─────────────────────────────────────────────────────────
if "draft" not in st.session_state:
    st.session_state.draft = None

col_gen, col_regen = st.columns([2, 1])
with col_gen:
    gen_btn = st.button("🤖 초안 생성", type="primary")
with col_regen:
    regen_btn = st.button("🔄 재생성")

if gen_btn or regen_btn:
    with st.spinner("Claude가 메일을 작성하고 있습니다..."):
        try:
            draft = generate_draft(
                api_key=api_key,
                category=category,
                company_name=selected["company_name"],
                industry=selected.get("industry", ""),
                sender=settings,
                custom_system=custom_system,
            )
            if target_lang != "ko":
                draft = translate_draft(api_key, draft, target_lang)
            st.session_state.draft = draft
        except Exception as e:
            st.error(f"오류: {e}")

# ── 초안 편집 & 표시 ───────────────────────────────────────────────────
if st.session_state.draft:
    draft = st.session_state.draft
    st.divider()
    st.subheader("메일 초안 편집")

    col_a, col_b = st.columns([3, 1])
    with col_a:
        new_subject = st.text_input("제목", value=draft.get("subject", ""))
        new_body = st.text_area("본문", value=draft.get("body", ""), height=200)
        dept = st.text_input("전달 요청 부서", value=draft.get("target_dept", ""))

    with col_b:
        st.markdown("**서명**")
        sig_text = st.text_area("서명", value=draft.get("signature", ""), height=120, label_visibility="collapsed")

        st.markdown("**첨부파일 안내**")
        default_files = get_default_files(category)
        custom_files_input = st.text_area(
            "추가 첨부파일 (한 줄에 하나씩)",
            value="\n".join(default_files),
            height=100,
        )
        custom_files = [f.strip() for f in custom_files_input.strip().splitlines() if f.strip()]

    # 첨부파일 안내 텍스트
    attach_guide = get_attachment_text(category, [f for f in custom_files if f not in default_files])

    # 최종 미리보기
    st.divider()
    st.subheader("최종 미리보기")
    preview = f"""**수신:** {selected.get('email', '')}
**제목:** {new_subject}

{new_body}

{attach_guide}

---
{sig_text}
"""
    st.markdown(preview)

    # 메일 전체 텍스트 복사용
    full_mail = f"수신: {selected.get('email', '')}\n제목: {new_subject}\n\n{new_body}{attach_guide}\n\n---\n{sig_text}"
    st.text_area("복사용 전체 텍스트", value=full_mail, height=250)

    # 다국어 번역
    st.divider()
    with st.expander("🌍 다국어 번역"):
        tr_lang = st.selectbox("번역 언어", [k for k in SUPPORTED_LANGUAGES if k != "ko"],
                               format_func=lambda x: SUPPORTED_LANGUAGES[x])
        if st.button("번역"):
            with st.spinner("번역 중..."):
                translated = translate_draft(api_key, {
                    "subject": new_subject, "body": new_body,
                    "target_dept": dept, "signature": sig_text,
                }, tr_lang)
                st.text_input("번역 제목", value=translated.get("subject", ""))
                st.text_area("번역 본문", value=translated.get("body", ""), height=200)

    # 발송 이력 저장
    st.divider()
    note = st.text_input("메모 (선택)", placeholder="특이사항 등")
    if st.button("📬 발송 완료 기록", type="primary"):
        insert_history({
            "company_id": selected["id"],
            "company_name": selected["company_name"],
            "category": category,
            "sender_name": settings.get("sender_name", ""),
            "draft_subject": new_subject,
            "language": draft.get("language", "ko"),
            "note": note,
        })
        st.success(f"'{selected['company_name']}' 발송 이력이 저장되었습니다.")
        st.session_state.draft = None
        st.rerun()
