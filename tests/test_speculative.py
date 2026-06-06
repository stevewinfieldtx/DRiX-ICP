"""Unit tests for the compliant Section 8 pure functions (no network)."""
from app.services.speculative import derived, dns_signals, site_scraper


def test_role_classification():
    assert site_scraper.classify_role("VP of Sales") == ("sales", "leader")
    assert site_scraper.classify_role("Account Executive") == ("sales", "ic")
    assert site_scraper.classify_role("Senior Software Engineer") == ("engineering", "ic")
    assert site_scraper.classify_role("Director of Marketing") == ("marketing", "leader")


def test_dmarc_policy_parse():
    assert dns_signals.parse_dmarc_policy(["v=DMARC1; p=reject; rua=..."]) == "reject"
    assert dns_signals.parse_dmarc_policy(["v=DMARC1; p=none"]) == "none"
    assert dns_signals.parse_dmarc_policy(["nothing here"]) is None


def test_mx_classification():
    assert dns_signals.classify_mx(["aspmx.l.google.com"]) == "google"
    assert dns_signals.classify_mx(["company-com.mail.protection.outlook.com"]) == "microsoft"
    assert dns_signals.classify_mx(["mx.self.example.com"]) == "self_hosted_or_other"
    assert dns_signals.classify_mx([]) is None


def test_ratios_none_safe():
    li = {"sales_titles_count": 40, "marketing_titles_count": 10, "sales_leaders_count": 4}
    web = {"roles_summary": {"by_department": {"engineering": 20},
                             "by_department_seniority": {"sales_ic": 12}}}
    r = derived.compute_ratios(li, web)
    assert r["technical_to_sales_ratio"] == 0.5      # 20 / 40
    assert r["gtm_to_build_ratio"] == 2.5            # (40+10) / 20
    assert r["sales_leader_to_ic_ratio"] == round(4 / 12, 2)
    # divide-by-zero / missing -> None, not a crash
    assert derived.compute_ratios({}, {})["technical_to_sales_ratio"] is None


def test_absence_flags_for_email_security_fit():
    web = {"has_security_page": False, "has_pricing_page": True}
    dns = {"dmarc_present": True, "dmarc_policy": "none", "spf_present": True,
           "security_txt_present": False}
    a = derived.compute_absence(web, dns)
    assert a["missing_security_page"] is True
    assert a["weak_dmarc_policy"] is True            # p=none counts as weak
    assert a["missing_dmarc"] is False
    assert a["no_security_txt"] is True


def test_triggers():
    web = {"hiring_for_new_function": ["possible_first_sales_hire"],
           "roles_summary": {"open_roles_total": 7},
           "last_blog_date": "2023", "copyright_year": 2022}
    t = derived.compute_triggers(web, funding=None, current_year=2026)
    assert t["dormant_blog"] is True
    assert t["stale_copyright"] is True
    assert t["open_roles_total"] == 7
    assert "possible_first_sales_hire" in t["hiring_for_new_function"]
