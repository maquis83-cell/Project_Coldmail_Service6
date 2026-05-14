"""F-01: AI Agent 기반 업체 리스트업 (Claude tool_use)"""
import json
import re
import anthropic


SYSTEM_PROMPT = """당신은 국내 기업 리서치 전문 AI입니다.
주어진 카테고리와 매출 순위 구간에 해당하는 국내 업체 목록을 조사하세요.
각 업체에 대해 반드시 다음 정보를 포함하세요:
- company_name: 업체명
- industry: 업종
- website_url: 홈페이지 URL (https:// 포함)
- ceo_name: 대표자명 (모르면 null)

실제로 존재하는 업체들을 기반으로, JSON 배열 형식으로만 응답하세요.
마크다운 코드블록 없이 순수 JSON 배열만 반환하세요.
"""

CATEGORY_DESC = {
    "샘플북제공": "샘플북이나 카탈로그를 받을 만한 소비재·유통·도소매",
    "제품제안": "B2B 제품 제안이 효과적인 제조·유통·서비스",
    "신규안내": "신규 제품 출시 안내가 적합한 리테일·이커머스·유통",
}


def search_companies(
    api_key: str,
    category: str,
    rank_range: str,
    min_results: int = 10,
) -> list[dict]:
    """Claude API로 업체 리스트를 생성한다."""
    client = anthropic.Anthropic(api_key=api_key)
    cat_desc = CATEGORY_DESC.get(category, category)

    user_msg = (
        f"카테고리: {category} ({cat_desc})\n"
        f"매출 순위 구간: {rank_range}위\n"
        f"위 조건에 맞는 국내 업체 {min_results}개 이상을 JSON 배열로 반환하세요."
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = response.content[0].text.strip()
    # 코드블록 제거
    raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # 배열 추출 재시도
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            data = []

    # 결과 부족 시 완화 재검색
    if len(data) < min_results:
        relaxed_msg = (
            f"카테고리: {category}\n"
            f"조건을 조금 완화해서 국내 업체 {min_results}개를 JSON 배열로 반환하세요. "
            "이미 반환한 업체는 제외하고 새 업체를 추가하세요.\n"
            f"기존 목록: {json.dumps([d.get('company_name') for d in data], ensure_ascii=False)}"
        )
        r2 = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": raw},
                {"role": "user", "content": relaxed_msg},
            ],
        )
        raw2 = r2.content[0].text.strip()
        raw2 = re.sub(r"```(?:json)?", "", raw2).strip().strip("`")
        try:
            extra = json.loads(raw2)
            data.extend(extra)
        except json.JSONDecodeError:
            pass

    # 정규화
    result = []
    for item in data:
        if not isinstance(item, dict):
            continue
        result.append({
            "company_name": item.get("company_name", ""),
            "industry": item.get("industry", ""),
            "website_url": item.get("website_url", ""),
            "ceo_name": item.get("ceo_name"),
            "category": category,
            "rank_range": rank_range,
        })
    return result
