"""F-04: 카테고리별 콜드메일 초안 생성 + F-05: 다국어 번역"""
import json
import re
from openai import OpenAI

SYSTEM_PROMPTS = {
    "샘플북제공": """당신은 B2B 영업 전문가입니다.
수신 업체에 샘플북 제공을 제안하는 콜드메일 초안을 작성하세요.
- 본문은 반드시 "안녕하세요."로 시작하세요. 부서명이나 팀명을 인사말에 포함하지 마세요.
- 업체의 업종을 고려해 샘플북이 어떻게 도움이 될지 구체적으로 설명하세요.
- 구매팀 또는 상품기획팀에 전달을 요청하는 문구를 포함하세요.
- 분량: 본문 150~200자 (한국어 기준)
- 출력 형식: 반드시 JSON {"subject": "...", "body": "...", "target_dept": "..."}만 반환""",

    "제품제안": """당신은 B2B 영업 전문가입니다.
수신 업체에 적합한 제품을 제안하는 콜드메일 초안을 작성하세요.
- 본문은 반드시 "안녕하세요."로 시작하세요. 부서명이나 팀명을 인사말에 포함하지 마세요.
- 업체의 업종에 맞는 제품 카테고리를 언급하세요.
- 마케팅팀 또는 상품팀에 전달을 요청하는 문구를 포함하세요.
- 분량: 본문 150~200자 (한국어 기준)
- 출력 형식: 반드시 JSON {"subject": "...", "body": "...", "target_dept": "..."}만 반환""",

    "신규안내": """당신은 B2B 영업 전문가입니다.
신규 제품 출시를 안내하는 콜드메일 초안을 작성하세요.
- 본문은 반드시 "안녕하세요."로 시작하세요. 부서명이나 팀명을 인사말에 포함하지 마세요.
- 신제품이 업체에 어떤 가치를 줄 수 있는지 설명하세요.
- 담당 부서(구매팀/개발팀)에 전달을 요청하는 문구를 포함하세요.
- 분량: 본문 150~200자 (한국어 기준)
- 출력 형식: 반드시 JSON {"subject": "...", "body": "...", "target_dept": "..."}만 반환""",
}

SUPPORTED_LANGUAGES = {"ko": "한국어", "en": "영어", "ja": "일본어", "zh": "중국어"}

DEFAULT_SYSTEM = SYSTEM_PROMPTS["샘플북제공"]


def _build_signature(sender: dict) -> str:
    lines = [
        sender.get("sender_name", ""),
        sender.get("sender_title", ""),
        sender.get("sender_company", ""),
        sender.get("sender_phone", ""),
    ]
    sig = sender.get("signature_block", "")
    if sig:
        return sig
    return "\n".join(l for l in lines if l)


def _parse_json(raw: str) -> dict:
    raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {"subject": "", "body": raw, "target_dept": ""}


def generate_draft(
    api_key: str,
    category: str,
    company_name: str,
    industry: str,
    sender: dict,
    custom_system: str | None = None,
) -> dict:
    client = OpenAI(api_key=api_key)
    system = custom_system or SYSTEM_PROMPTS.get(category, DEFAULT_SYSTEM)
    user_msg = (
        f"업체명: {company_name}\n"
        f"업종: {industry}\n"
        f"발신자: {sender.get('sender_name', '')} "
        f"({sender.get('sender_title', '')}, {sender.get('sender_company', '')})"
    )

    resp = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1024,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
    )

    draft = _parse_json(resp.choices[0].message.content)
    draft["signature"] = _build_signature(sender)
    draft["language"] = "ko"
    return draft


def translate_draft(api_key: str, draft: dict, target_lang: str) -> dict:
    if target_lang == "ko":
        return draft

    lang_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)
    client = OpenAI(api_key=api_key)
    prompt = (
        f"다음 콜드메일 제목과 본문을 {lang_name}로 번역하세요.\n"
        "자연스러운 비즈니스 문체를 유지하세요.\n"
        '출력 형식: JSON {"subject": "...", "body": "..."}\n\n'
        f"제목: {draft['subject']}\n본문: {draft['body']}"
    )

    resp = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    translated = _parse_json(resp.choices[0].message.content)
    return {**draft, **translated, "language": target_lang}
