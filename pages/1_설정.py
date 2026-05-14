"""F-12: 사용자 설정 & 발신자 정보"""
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
from services.database import get_settings, save_settings

st.set_page_config(page_title="설정", page_icon="⚙️", layout="wide")
st.title("⚙️ 사용자 설정")

s = get_settings()

with st.form("settings_form"):
    st.subheader("발신자 정보")
    col1, col2 = st.columns(2)
    with col1:
        sender_name = st.text_input("이름", value=s.get("sender_name", ""))
        sender_title = st.text_input("직책", value=s.get("sender_title", ""))
    with col2:
        sender_company = st.text_input("회사명", value=s.get("sender_company", ""))
        sender_phone = st.text_input("연락처", value=s.get("sender_phone", ""))

    signature_block = st.text_area(
        "서명 (비워두면 위 정보로 자동 구성)",
        value=s.get("signature_block", ""),
        height=100,
    )

    st.subheader("API 키")
    col3, col4 = st.columns(2)
    with col3:
        anthropic_key = st.text_input(
            "Anthropic API Key",
            value=s.get("anthropic_api_key", ""),
            type="password",
        )
    with col4:
        openai_key = st.text_input(
            "OpenAI API Key (선택)",
            value=s.get("openai_api_key", ""),
            type="password",
        )

    st.subheader("기본값")
    col5, col6 = st.columns(2)
    with col5:
        default_lang = st.selectbox(
            "기본 언어",
            ["ko", "en", "ja", "zh"],
            index=["ko", "en", "ja", "zh"].index(s.get("default_language", "ko")),
            format_func=lambda x: {"ko": "한국어", "en": "영어", "ja": "일본어", "zh": "중국어"}[x],
        )
    with col6:
        default_cat = st.selectbox(
            "기본 카테고리",
            ["", "샘플북제공", "제품제안", "신규안내"],
            index=["", "샘플북제공", "제품제안", "신규안내"].index(
                s.get("default_category", "") or ""
            ),
        )

    submitted = st.form_submit_button("저장", type="primary")

if submitted:
    save_settings({
        "sender_name": sender_name,
        "sender_title": sender_title,
        "sender_company": sender_company,
        "sender_phone": sender_phone,
        "signature_block": signature_block,
        "anthropic_api_key": anthropic_key,
        "openai_api_key": openai_key,
        "default_language": default_lang,
        "default_category": default_cat,
    })
    st.success("설정이 저장되었습니다.")

# API 키 연결 확인
st.divider()
st.subheader("API 키 연결 상태 확인")
if st.button("연결 확인"):
    key = s.get("anthropic_api_key", "") or anthropic_key
    if not key:
        st.error("Anthropic API 키를 먼저 저장하세요.")
    else:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=key)
            client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            st.success("Anthropic API 연결 성공!")
        except Exception as e:
            st.error(f"연결 실패: {e}")
