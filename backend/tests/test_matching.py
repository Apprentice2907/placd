from datetime import datetime, timedelta, timezone

from utils.job_details import clean_skills, parse_posted_at
from utils.matching import describe_chance

NOW = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)


def chance(**job):
    return describe_chance(job, job.pop("interest", None), NOW)


def test_well_known_companies_are_a_stretch():
    result = chance(well_known=True, applicants=3, created_at=NOW)
    assert result["level"] == "stretch"
    assert "Well-known company, so many people apply" in result["reasons"]


def test_small_company_with_few_applicants_is_a_strong_chance():
    result = chance(well_known=False, applicants=12, created_at=NOW - timedelta(days=20))
    assert result["level"] == "strong"
    assert result["reasons"] == ["Smaller company or startup", "12 applicants so far", "Found by Placd 20 days ago"]


def test_new_post_is_a_strong_chance_even_without_applicant_count():
    result = chance(well_known=False, posted_at=NOW - timedelta(days=2))
    assert result["level"] == "strong"
    assert "Posted 2 days ago" in result["reasons"]


def test_older_busy_post_is_a_good_fit():
    result = chance(well_known=False, applicants=400, posted_at=NOW - timedelta(days=10))
    assert result["level"] == "good"
    assert result["label"] == "Good fit"


def test_early_applicant_and_interest_reasons():
    result = chance(well_known=False, applicants=0, created_at=NOW, interest_level=2, interest="ai")
    assert result["reasons"][:3] == ["Matches AI & ML", "Smaller company or startup", "Be an early applicant"]
    assert "Found by Placd today" in result["reasons"]
    assert chance(well_known=False, interest_level=1, interest="data")["reasons"][0] == "Related to Data"


def test_missing_dates_do_not_break_labels():
    result = chance(well_known=False)
    assert result["level"] == "good"
    assert chance(well_known=False, created_at="not a date")["level"] == "good"


def test_skills_are_cleaned_and_capped():
    assert clean_skills(["Python", " python ", "", "Machine Learning"]) == ["Python", "Machine Learning"]
    assert clean_skills("SQL, Excel ,SQL") == ["SQL", "Excel"]
    assert clean_skills(None) is None
    assert clean_skills([]) is None
    assert len(clean_skills([f"skill {i}" for i in range(40)])) == 15
    assert clean_skills(["x" * 80]) is None


def test_posting_dates_are_only_trusted_from_sources_that_give_real_ones():
    job = {"posted_date": (NOW - timedelta(days=2)).isoformat()}
    assert parse_posted_at(job, "internshala", NOW) == NOW - timedelta(days=2)
    # These scrapers fill in the time they ran, which would make old jobs look new
    assert parse_posted_at(job, "google", NOW) is None
    assert parse_posted_at(job, "greenhouse", NOW) is None


def test_posting_dates_that_cannot_be_real_are_ignored():
    assert parse_posted_at({"posted_date": "2031-01-01"}, "lever", NOW) is None
    assert parse_posted_at({"posted_date": "2019-01-01"}, "lever", NOW) is None
    assert parse_posted_at({"posted_date": "soon"}, "lever", NOW) is None
    assert parse_posted_at({}, "lever", NOW) is None
    naive = parse_posted_at({"date_posted": "2026-11-15T10:00:00"}, "ashby", NOW)
    assert naive.tzinfo is not None
