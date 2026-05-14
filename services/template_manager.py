"""F-10: 템플릿 관리 + LLM 개선 제안"""
import anthropic
from services.database import get_templates, upsert_template, delete_template, increment_template_usage


def list_templates() -> list[dict]:
    return get_templates()


def save_template(data: dict) -> str:
    return upsert_template(data)


def remove_template(tid: str):
    delete_template(tid)


def use_template(tid: str) -> str | None:
    templates = get_templates()
    for t in templates:
        if t["id"] == tid:
            increment_template_usage(tid)
            return t["system_prompt"]
    return None


def improve_template(api_key: str, current_prompt: str) -> str:
    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": (
                "다음 콜드메일 시스템 프롬프트를 더 자연스럽고 효과적으로 개선해 주세요.\n"
                "개선된 프롬프트만 반환하세요 (설명 불필요):\n\n"
                + current_prompt
            ),
        }],
    )
    return resp.content[0].text.strip()
