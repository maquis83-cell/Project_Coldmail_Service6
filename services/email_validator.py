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
TIMEOUT = 10.0

# 직접 시도할 경로 (홈페이지 → 연락처 링크 탐색이 실패할 경우 후보)
CRAWL_PATHS = [
    "/contact", "/contact-us", "/contactus", "/about", "/about-us",
    "/연락처", "/문의", "/문의하기", "/support", "/help", "/",
]

# 연락처 페이지로 판단하는 패턴
CONTACT_LINK_RE = re.compile(
    r"contact|연락|문의|about|소개|reach|support|help",
    re.IGNORECASE,
)

# 제외할 패턴 (파일 확장자, 서비스 이메일 등)
SKIP_PATTERNS = [
    "example.com", "sentry.io", "noreply", "no-reply", "w3.org",
    "schema.org", "googleapis", "cloudflare", "jquery", "bootstrap",
    ".png@", ".jpg@", ".gif@", ".svg@", ".css@", ".js@",
    "@2x", "@3x",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

# 신뢰도 높은 로컬 파트 (점수 가산)
HIGH_TRUST_LOCAL = {"info", "contact", "hello", "mail", "sales",
                    "support", "cs", "help", "pr", "marketing"}


def _extract_domain(url: str) -> str:
    url = url.replace("https://", "").replace("http://", "").split("/")[0]
    return url.lower()


def _is_valid_email(email: str) -> bool:
    if not EMAIL_RE.fullmatch(email):
        return False
    return not any(skip in email.lower() for skip in SKIP_PATTERNS)


def _score_email(email: str) -> int:
    """낮을수록 더 신뢰도 높은 이메일."""
    local = email.split("@")[0].lower()
    if local in HIGH_TRUST_LOCAL:
        return 0
    if any(c.isdigit() for c in local):
        return 2  # 숫자 포함 개인 이메일일 가능성
    return 1


def _extract_emails_from_soup(soup: BeautifulSoup) -> list[str]:
    """soup에서 mailto: 링크(1순위)와 텍스트(2순위)로 이메일 추출."""
    found: list[tuple[int, str]] = []  # (priority, email)

    # 1순위: mailto: href
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.lower().startswith("mailto:"):
            raw = href[7:].split("?")[0].strip()
            if _is_valid_email(raw):
                found.append((0, raw))

    # 2순위: 페이지 전체 텍스트 정규식
    for email in EMAIL_RE.findall(soup.get_text()):
        if _is_valid_email(email):
            found.append((1, email))

    # 중복 제거 후 (priority, score) 기준 정렬
    seen: set[str] = set()
    result: list[str] = []
    for priority, email in sorted(found, key=lambda x: (x[0], _score_email(x[1]))):
        lower = email.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(email)
    return result


def _find_contact_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """홈페이지에서 연락처 관련 링크를 추출."""
    base = base_url.rstrip("/")
    links: list[str] = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        text = tag.get_text(strip=True)
        if CONTACT_LINK_RE.search(href) or CONTACT_LINK_RE.search(text):
            if href.startswith("http"):
                links.append(href)
            elif href.startswith("/"):
                links.append(base + href)
    # 중복 제거, 최대 4개
    seen: set[str] = set()
    unique: list[str] = []
    for link in links:
        if link not in seen:
            seen.add(link)
            unique.append(link)
    return unique[:4]


def _fetch_soup(client: httpx.Client, url: str) -> BeautifulSoup | None:
    try:
        resp = client.get(url, headers=HEADERS)
        if resp.status_code >= 400:
            return None
        return BeautifulSoup(resp.text, "html.parser")
    except Exception:
        return None


def _crawl_email(base_url: str) -> str | None:
    base = base_url.rstrip("/")

    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:

        # ── Step 1: 홈페이지 크롤링 ──────────────────────────────
        home_soup = _fetch_soup(client, base + "/")
        if home_soup:
            emails = _extract_emails_from_soup(home_soup)
            if emails:
                return emails[0]

            # ── Step 2: 연락처 링크 발견 → 해당 페이지 크롤링 ──
            contact_links = _find_contact_links(home_soup, base)
            for link in contact_links:
                soup = _fetch_soup(client, link)
                if soup:
                    emails = _extract_emails_from_soup(soup)
                    if emails:
                        return emails[0]

        # ── Step 3: 고정 경로 순차 시도 ─────────────────────────
        for path in CRAWL_PATHS:
            if path == "/":
                continue  # 홈은 이미 시도
            soup = _fetch_soup(client, base + path)
            if soup:
                emails = _extract_emails_from_soup(soup)
                if emails:
                    return emails[0]

    return None


def _check_mx(domain: str) -> bool:
    if not DNS_AVAILABLE:
        return True
    try:
        dns.resolver.resolve(domain, "MX")
        return True
    except Exception:
        return False


def validate_email(website_url: str) -> tuple[str, str]:
    """(email, status) 반환. status: confirmed | estimated | unknown"""
    domain = _extract_domain(website_url)

    # 크롤링으로 이메일 발견
    email = _crawl_email(website_url)
    if email:
        mx_ok = _check_mx(email.split("@")[1])
        status = "confirmed" if mx_ok else "estimated"
        return email, status

    # 크롤링 실패 → DNS 기반 추정
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
