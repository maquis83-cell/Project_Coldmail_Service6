"""F-01: AI Agent 기반 업체 리스트업 (GPT-4o) — 산업군 기반 검색"""
import json
import re
from openai import OpenAI


SYSTEM_PROMPT = """당신은 국내 기업 리서치 전문 AI입니다.
사용자가 입력한 산업군에 해당하는 실제 국내 업체 목록을 조사하세요.
각 업체에 대해 반드시 다음 정보를 포함하세요:
- company_name: 업체명
- industry: 업종 (구체적으로)
- website_url: 홈페이지 URL (https:// 포함, 모르면 빈 문자열)
- ceo_name: 대표자명 (모르면 null)

실제로 존재하는 업체만 포함하세요.
마크다운 코드블록 없이 순수 JSON 배열만 반환하세요.
"""


def _call(client: OpenAI, messages: list[dict]) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=4096,
        messages=messages,
    )
    return response.choices[0].message.content.strip()


def search_companies(
    api_key: str,
    industry_type: str,
    rank_range: str,
    min_results: int = 10,
) -> list[dict]:
    """GPT-4o로 산업군 기반 업체 리스트를 생성한다."""
    client = OpenAI(api_key=api_key)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"산업군: {industry_type}\n"
            f"매출 규모 순위 구간: {rank_range}위 수준\n"
            f"위 산업군에 해당하는 국내 업체 {min_results}개 이상을 JSON 배열로 반환하세요."
        )},
    ]

    raw = _call(client, messages)
    raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        data = json.loads(match.group()) if match else []

    # 결과 부족 시 완화 재검색
    if len(data) < min_results:
        messages += [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": (
                f"더 많은 {industry_type} 업체를 추가해 주세요. "
                f"총 {min_results}개가 되도록 새 업체만 JSON 배열로 반환하세요.\n"
                f"기존 목록: {json.dumps([d.get('company_name') for d in data], ensure_ascii=False)}"
            )},
        ]
        raw2 = _call(client, messages)
        raw2 = re.sub(r"```(?:json)?", "", raw2).strip().strip("`")
        try:
            data.extend(json.loads(raw2))
        except json.JSONDecodeError:
            pass

    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        result.append({
            "company_name": item.get("company_name", ""),
            "industry": item.get("industry", industry_type),
            "website_url": item.get("website_url", ""),
            "ceo_name": item.get("ceo_name"),
            "rank_range": rank_range,
        })
    return result
