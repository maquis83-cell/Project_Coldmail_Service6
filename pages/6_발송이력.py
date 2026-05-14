"""F-09: 발송 이력 관리"""
import sys, os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import streamlit as st
import pandas as pd
from io import BytesIO
from services.database import get_history
from openpyxl import Workbook

st.set_page_config(page_title="발송 이력", page_icon="📜", layout="wide")
st.title("📜 발송 이력")

history = get_history()

if not history:
    st.info("발송 이력이 없습니다. [메일작성] 페이지에서 발송 완료 기록을 저장하세요.")
    st.stop()

df = pd.DataFrame(history)
display_cols = ["company_name", "category", "sender_name", "sent_at", "draft_subject", "language", "note"]
display_cols = [c for c in display_cols if c in df.columns]

df_show = df[display_cols].copy()
df_show.columns = [
    {"company_name": "업체명", "category": "카테고리", "sender_name": "발신자",
     "sent_at": "발송일시", "draft_subject": "메일 제목", "language": "언어", "note": "메모"
     }.get(c, c) for c in display_cols
]

# 필터
col1, col2 = st.columns(2)
with col1:
    cat_filter = st.multiselect("카테고리 필터", ["샘플북제공", "제품제안", "신제품 안내"])
with col2:
    search = st.text_input("업체명 검색")

filtered = df_show.copy()
if cat_filter:
    filtered = filtered[filtered["카테고리"].isin(cat_filter)]
if search:
    filtered = filtered[filtered["업체명"].str.contains(search, na=False)]

st.dataframe(filtered, use_container_width=True)
st.caption(f"총 {len(filtered)}건")

# 엑셀 내보내기
def _to_xlsx(df: pd.DataFrame) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "발송이력"
    ws.append(list(df.columns))
    for row in df.itertuples(index=False):
        ws.append(list(row))
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()

st.download_button(
    "⬇️ 이력 엑셀 다운로드",
    data=_to_xlsx(filtered),
    file_name="send_history.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
