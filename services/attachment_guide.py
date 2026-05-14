"""F-06: 첨부파일 안내"""

DEFAULT_ATTACHMENTS: dict[str, list[str]] = {
    "샘플북제공": ["샘플북_카탈로그.pdf", "제품_라인업_소개서.pdf"],
    "제품제안": ["적합_제품_제안서.pdf", "가격표.xlsx"],
    "신제품 안내": ["신제품_안내서.pdf", "출시_프로모션_안내.pdf"],
}


def get_attachment_text(category: str, custom_files: list[str] | None = None) -> str:
    files = DEFAULT_ATTACHMENTS.get(category, []) + (custom_files or [])
    if not files:
        return ""
    file_list = "\n".join(f"  - {f}" for f in files)
    return f"\n\n[첨부파일 안내]\n아래 파일을 함께 첨부해 주세요:\n{file_list}"


def get_default_files(category: str) -> list[str]:
    return list(DEFAULT_ATTACHMENTS.get(category, []))
