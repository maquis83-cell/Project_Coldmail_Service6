"""F-07: BCC 주소 일괄 생성"""

def build_bcc(companies: list[dict], include_statuses: list[str] | None = None) -> dict:
    if include_statuses is None:
        include_statuses = ["confirmed", "estimated"]

    emails = [
        c["email"] for c in companies
        if c.get("email") and c.get("email_status") in include_statuses
    ]
    unique = list(dict.fromkeys(emails))
    domains = [e.split("@")[1] for e in unique if "@" in e]
    dup_domains = [d for d in set(domains) if domains.count(d) > 1]

    return {
        "bcc_string": ";".join(unique),
        "total_count": len(unique),
        "duplicate_domains": dup_domains,
        "emails": unique,
    }
