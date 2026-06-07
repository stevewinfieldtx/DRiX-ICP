# `speculative_data` JSONB shape (Section 8, compliant build)

```jsonc
{
  "website": {
    "has_case_studies": true, "case_study_count": null,
    "has_blog": true, "blog_article_count": 52, "last_blog_date": "2026",
    "has_press": true, "last_press_date": "2026",
    "team_mentions": {"sales_mentions": 12, "marketing_mentions": 4,
                      "engineering_mentions": 30, "support_mentions": 6},
    "open_roles": [{"title": "Account Executive", "department": "sales", "seniority": "ic"}],
    "roles_summary": {
      "open_roles_total": 7,
      "by_department": {"sales": 4, "engineering": 2, "marketing": 1},
      "by_seniority": {"leader": 2, "ic": 5},
      "by_department_seniority": {"sales_ic": 3, "sales_leader": 1, "engineering_ic": 2}
    },
    "hiring_for_new_function": ["possible_first_marketing_hire"],
    "leadership_count": 8, "partner_page": false,
    "has_security_page": false, "has_pricing_page": true, "pricing_model": "contact_sales",
    "pain_language": ["compliance", "hipaa", "encryption"],
    "social_links": {"linkedin": "https://linkedin.com/company/x"},
    "tech_mentions": ["microsoft 365", "salesforce"],
    "copyright_year": 2026, "pages_fetched": ["/", "about", "careers"],
    "_captured_at": "2026-06-06T..."
  },

  "dns": {
    "spf_present": true, "spf_record": "v=spf1 ...",
    "dmarc_present": true, "dmarc_policy": "none", "dmarc_record": "v=DMARC1; p=none",
    "mx_provider": "microsoft", "mx_hosts": ["...outlook.com"],
    "security_txt_present": false
  },

  "linkedin": {            // sourced via LICENSED people-data API, not scraping
    "company_size": "51-200",
    "sales_titles_count": 34, "marketing_titles_count": 8,
    "sales_leaders_count": 3, "marketing_leaders_count": 2,
    "followers": 5400, "specialties": [...], "description": "..."
  },

  "news":    [{"headline": "...", "date": "2026-05-12", "source": "TechCrunch"}],
  "funding": {"total_funding": 20000000, "latest_funding_stage": "Series B", "latest_funding_round_date": "2026-05-12"},

  "derived": {
    "ratios": {
      "gtm_to_build_ratio": 1.4,           // (sales+marketing) / engineering
      "technical_to_sales_ratio": 0.6,     // engineering / sales
      "sales_to_marketing_ratio": 4.25,
      "sales_leader_to_ic_ratio": 0.25,
      "_headcounts_used": {...}
    },
    "absence": {
      "missing_security_page": true, "missing_pricing_page": false,
      "missing_dmarc": false, "weak_dmarc_policy": true,
      "missing_spf": false, "no_security_txt": true
    },
    "triggers": {
      "hiring_for_new_function": ["possible_first_marketing_hire"],
      "open_roles_total": 7, "dormant_blog": false,
      "stale_copyright": false, "recent_funding": true
    }
  },

  "_captured_at": "2026-06-06T..."
}
```

## Why this shape

- **Raw + derived side by side.** Pattern mining (Section 9) can use either the
  raw counts or the pre-computed ratios, and can find *interaction* effects
  (e.g. "M365 + dmarc=none + regulated vertical + first security hire").
- **Absence is first-class.** Negative signals are recorded explicitly, not
  inferred from missing keys.
- **`_captured_at` on every snapshot.** Enables later diffing for true
  delta/velocity signals (hiring velocity, exec changes) without storing PII.
- **No personal data.** Only counts, ratios, booleans, public DNS, and the
  company's own public copy. Nothing here identifies individuals.
```
