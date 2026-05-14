"""F-03: 대표 이메일 주소 검증 (크롤링 + DNS + 룰베이스)"""
import re
import httpx
from bs4 import BeautifulSoup

try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
TIMEOUT = 8.0
CRAWL_PATHS = ["/contact", "/about", "/about-us", "/contactus", "/"]


def _extract_domain(url: str) -> str:
    url = url.replace("https://", "").replace("http://", "").split("/")[0]
    return url.lower()


def _crawl_email(base_url: str) -> str | None:
    base = base_url.rstrip("/")
    for path in CRAWL_PATHS:
        try:
            with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
                resp = client.get(base + path)
                soup = BeautifulSoup(resp.text, "html.parser")
                emails = EMAIL_RE.findall(soup.get_text())
                # 일반적인 서비스 이메일 제외
                filtered = [e for e in emails if not any(skip in e for skip in
                    ["example.com", "sentry", "noreply", "no-reply", "w3.org"])]
                if filtered:
                    return filtered[0]
        except Exception:
            continue
    return None


def _check_mx(domain: str) -> bool:
    if not DNS_AVAILABLE:
        return True  # DNS 모듈 없으면 통과 처리
    try:
        dns.resolver.resolve(domain, "MX")
        return True
    except Exception:
        return False


def validate_email(website_url: str) -> tuple[str, str]:
    """(email, status) 반환. status: confirmed | estimated | unknown"""
    domain = _extract_domain(website_url)

    # 1단계: 크롤링
    email = _crawl_email(website_url)
    if email:
        status = "confirmed" if _check_mx(email.split("@")[1]) else "estimated"
        return email, status

    # 2단계: 일반 패턴 후보
    candidates = [f"info@{domain}", f"contact@{domain}", f"hello@{domain}"]
    if _check_mx(domain):
        return candidates[0], "estimated"

    return candidates[0], "unknown"


def batch_validate_emails(companies: list[dict]) -> list[dict]:
    updated = []
    for c in companies:
        if c.get("url_status") != "accessible":
            updated.append({**c, "email": c.get("email", ""), "email_status": "unknown"})
            continue
        email, status = validate_email(c.get("website_url", ""))
        updated.append({**c, "email": email, "email_status": status})
    return updated
