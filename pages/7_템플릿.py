"""F-10: 메일 템플릿 관리"""
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
from services.database import get_settings
from services.template_manager import list_templates, save_template, remove_template, improve_template

st.set_page_config(page_title="템플릿", page_icon="📝", layout="wide")
st.title("📝 메일 템플릿 관리")

settings = get_settings()
api_key = settings.get("anthropic_api_key", "")

templates = list_templates()

# ── 템플릿 목록 ─────────────────────────────────────────────────────
st.subheader("저장된 템플릿")
if not templates:
    st.info("저장된 템플릿이 없습니다. 아래에서 새 템플릿을 추가하세요.")
else:
    for t in templates:
        with st.expander(f"{'🌐' if t['is_shared'] else '👤'} {t['name']} — {t.get('category', '전체')} (사용 {t['usage_count']}회)"):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.text_area("시스템 프롬프트", value=t["system_prompt"], height=150,
                             key=f"view_{t['id']}", disabled=True)
            with col2:
                st.write(f"수정일: {t['updated_at'][:10]}")
                if st.button("삭제", key=f"del_{t['id']}"):
                    remove_template(t["id"])
                    st.success("삭제 완료")
                    st.rerun()

            # LLM 개선 제안
            if api_key and st.button("🤖 AI 개선 제안", key=f"improve_{t['id']}"):
                with st.spinner("Claude가 프롬프트를 개선 중..."):
                    improved = improve_template(api_key, t["system_prompt"])
                    st.text_area("개선된 프롬프트 (복사 후 수정 저장)", value=improved, height=150,
                                 key=f"improved_{t['id']}")

# ── 새 템플릿 추가 / 편집 ───────────────────────────────────────────
st.divider()
st.subheader("새 템플릿 추가")

with st.form("new_template"):
    tmpl_name = st.text_input("템플릿 이름 *")
    tmpl_cat = st.selectbox("카테고리", ["", "샘플북제공", "제품제안", "신규안내"],
                            format_func=lambda x: x or "전체")
    tmpl_prompt = st.text_area("시스템 프롬프트 *", height=200,
                                placeholder="LLM에게 전달할 메일 작성 지침을 입력하세요...")
    tmpl_shared = st.checkbox("팀 공유 템플릿")

    if st.form_submit_button("저장", type="primary"):
        if tmpl_name and tmpl_prompt:
            save_template({
                "name": tmpl_name,
                "category": tmpl_cat,
                "system_prompt": tmpl_prompt,
                "is_shared": tmpl_shared,
            })
            st.success(f"'{tmpl_name}' 템플릿이 저장되었습니다.")
            st.rerun()
        else:
            st.error("이름과 프롬프트는 필수입니다.")
