from datetime import date, datetime, timedelta, timezone

from db.retention import (
    MAX_DESCRIPTION_CHARS,
    minimize_description,
    parse_deadline,
    plan_deletions,
    retention_tier,
)

NOW = datetime(2026, 11, 3, tzinfo=timezone.utc)
HEALTHY = {"greenhouse": NOW - timedelta(days=1)}


def job(job_id, company="Unknown Co", days_ago=1, status="active", deadline=None, source="greenhouse"):
    return {
        "id": job_id,
        "source": source,
        "company_name": company,
        "status": status,
        "deadline": deadline,
        "last_seen": NOW - timedelta(days=days_ago),
    }


def reason_for(job_id, plan):
    return next((reason for reason, ids in plan.items() if job_id in ids), None)


def test_tier_matches_whole_words_only():
    assert retention_tier("Google") == 1
    assert retention_tier("Google LLC") == 1
    assert retention_tier("Nicola Labs") == 0  # contains "ola"
    assert retention_tier("Whatsapp Tools") == 0  # contains "hp"
    assert retention_tier("Canva") == 2
    assert retention_tier("") == 0
    assert retention_tier(None) == 0


def test_description_is_short_plain_text():
    raw = "&lt;p&gt;Build &amp; ship &lt;b&gt;APIs&lt;/b&gt;&lt;/p&gt;"
    assert minimize_description(raw) == "Build & ship APIs"
    assert minimize_description(None) == ""

    long_text = minimize_description("word " * 500)
    assert len(long_text) <= MAX_DESCRIPTION_CHARS
    assert long_text.endswith("word…")


def test_trimming_a_trimmed_description_is_stable():
    once = minimize_description("<p>" + "word " * 500 + "</p>")
    assert minimize_description(once) == once


def test_parse_deadline_formats():
    assert parse_deadline({"last_date": "29 Aug' 26"}) == date(2026, 8, 29)
    assert parse_deadline({"deadline": date(2026, 12, 1)}) == date(2026, 12, 1)
    assert parse_deadline({"last_date": "soon"}) is None
    assert parse_deadline({"last_date": "1 Jan 1990"}) is None
    assert parse_deadline({}) is None


def test_google_is_kept_for_five_months_but_others_are_not():
    rows = [
        job("fresh", days_ago=0),
        job("google_4mo", "Google", days_ago=120),
        job("google_6mo", "Google", days_ago=180),
        job("canva_45d", "Canva", days_ago=45),
        job("canva_90d", "Canva", days_ago=90),
        job("other_20d", days_ago=20),
        job("other_45d", days_ago=45),
    ]
    plan, _ = plan_deletions(rows, NOW, HEALTHY)
    assert plan["too_old"] == ["google_6mo", "canva_90d", "other_45d"]


def test_deadlines_override_age():
    rows = [
        job("fresh", days_ago=0),
        job("future", days_ago=200, deadline=date(2026, 12, 1)),
        job("passed", "Google", days_ago=1, deadline=date(2026, 11, 1)),
        job("today", days_ago=200, deadline=NOW.date()),
    ]
    plan, _ = plan_deletions(rows, NOW, HEALTHY)
    assert reason_for("future", plan) is None
    assert reason_for("today", plan) is None
    assert reason_for("passed", plan) == "deadline_passed"


def test_stale_scraper_never_empties_the_site():
    rows = [job(str(i), days_ago=69) for i in range(50)] + [job("expired", days_ago=69, status="expired")]
    plan, scraper_recent = plan_deletions(rows, NOW, {}, max_jobs=10)
    assert scraper_recent is False
    assert not any(plan.values())


def test_expired_status_alone_does_not_delete_a_job():
    rows = [
        job("amazon_expired", "Amazon", days_ago=69, status="expired"),
        job("amazon_expired_6mo", "Amazon", days_ago=180, status="expired"),
        job("hidden_old", days_ago=69, status="unverified"),
    ]
    plan, _ = plan_deletions(rows, NOW, HEALTHY)
    assert reason_for("amazon_expired", plan) is None
    assert sorted(plan["too_old"]) == ["amazon_expired_6mo", "hidden_old"]


def test_sign_in_redirect_is_not_a_closed_job():
    from utils.url_classifier import is_job_listing_page, is_sign_in_page

    assert is_sign_in_page("https://passport.amazon.jobs/")
    assert is_sign_in_page("https://example.com/users/sign-in")
    assert not is_job_listing_page("https://passport.amazon.jobs/")
    assert is_job_listing_page("https://apply.careers.microsoft.com/careers")
    assert is_job_listing_page("https://example.com/")
    assert not is_sign_in_page("https://example.com/careers")




def test_over_limit_removes_lowest_priority_first():
    rows = [
        job("other_new", days_ago=0),
        job("other_old", days_ago=5),
        job("canva", "Canva", days_ago=10),
        job("google", "Google", days_ago=20),
    ]
    plan, _ = plan_deletions(rows, NOW, HEALTHY, max_jobs=2)
    assert sorted(plan["over_limit"]) == ["other_new", "other_old"]

    plan, _ = plan_deletions(rows, NOW, HEALTHY, max_jobs=3)
    assert plan["over_limit"] == ["other_old"]


def test_link_checks_alone_do_not_count_as_a_scrape():
    rows = [job("checked_today", days_ago=0), job("old", days_ago=69)]
    plan, scraper_recent = plan_deletions(rows, NOW, {"greenhouse": NOW - timedelta(days=30)})
    assert scraper_recent is False
    assert reason_for("old", plan) is None


def test_failing_scraper_keeps_its_jobs_while_others_age_out():
    rows = [
        job("working_old", days_ago=69),
        job("failing_old", days_ago=69, source="lever"),
        job("never_worked_old", days_ago=69, source="ashby"),
        job("retired_old", days_ago=69, source="oldboard"),
    ]
    health = {**HEALTHY, "lever": NOW - timedelta(days=10), "ashby": None}
    plan, _ = plan_deletions(rows, NOW, health)
    assert sorted(plan["too_old"]) == ["retired_old", "working_old"]


def test_naive_timestamps_and_empty_table():
    naive = job("naive", days_ago=0)
    naive["last_seen"] = naive["last_seen"].replace(tzinfo=None)
    health = {"greenhouse": (NOW - timedelta(days=1)).replace(tzinfo=None)}
    plan, scraper_recent = plan_deletions([naive], NOW, health)
    assert scraper_recent is True
    assert reason_for("naive", plan) is None

    assert plan_deletions([], NOW, {})[1] is False
