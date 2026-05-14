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
    openai_key = st.text_input(
        "OpenAI API Key",
        value=s.get("openai_api_key", ""),
        type="password",
    )

    st.subheader("기본값")
    default_lang = st.selectbox(
        "기본 언어",
        ["ko", "en", "ja", "zh"],
        index=["ko", "en", "ja", "zh"].index(s.get("default_language", "ko")),
        format_func=lambda x: {"ko": "한국어", "en": "영어", "ja": "일본어", "zh": "중국어"}[x],
    )

    submitted = st.form_submit_button("저장", type="primary")

if submitted:
    save_settings({
        "sender_name": sender_name,
        "sender_title": sender_title,
        "sender_company": sender_company,
        "sender_phone": sender_phone,
        "signature_block": signature_block,
        "openai_api_key": openai_key,
        "default_language": default_lang,
    })
    st.success("설정이 저장되었습니다.")

# API 키 연결 확인
st.divider()
st.subheader("API 키 연결 상태 확인")
if st.button("연결 확인"):
    key = s.get("openai_api_key", "") or openai_key
    if not key:
        st.error("OpenAI API 키를 먼저 저장하세요.")
    else:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=key)
            client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}],
            )
            st.success("OpenAI API 연결 성공!")
        except Exception as e:
            st.error(f"연결 실패: {e}")
