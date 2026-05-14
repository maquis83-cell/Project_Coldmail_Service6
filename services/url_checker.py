"""F-02: 홈페이지 접속 가능성 확인 (룰베이스 + 동기 httpx)"""
import httpx

TIMEOUT = 8.0
OK_CODES = {200, 301, 302, 303, 307, 308}


def check_url(url: str) -> tuple[str, str]:
    """(status, final_url) 반환. status: accessible | inaccessible | needs_review"""
    if not url or not url.startswith("http"):
        url = "https://" + url.lstrip("/")
    try:
        with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code in OK_CODES:
                return "accessible", str(resp.url)
            return "inaccessible", url
    except httpx.TimeoutException:
        return "needs_review", url
    except Exception:
        # https 실패 → http 재시도
        http_url = url.replace("https://", "http://", 1)
        try:
            with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
                resp = client.get(http_url)
                if resp.status_code in OK_CODES:
                    return "accessible", str(resp.url)
        except Exception:
            pass
        return "inaccessible", url


def batch_check_urls(companies: list[dict]) -> list[dict]:
    """companies 리스트를 순회하며 url_status 갱신한 결과를 반환."""
    updated = []
    for c in companies:
        status, final_url = check_url(c.get("website_url", ""))
        updated.append({**c, "url_status": status, "website_url": final_url})
    return updated
