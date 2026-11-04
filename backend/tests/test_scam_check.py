from datetime import datetime, timedelta, timezone

from scrapers.internshala.adapter import parse_duration_months
from utils.job_tagger import is_internship, is_student_eligible
from utils.scam_check import check_job, describe_trust
from utils.spam_filter import is_spam

NOW = datetime(2026, 11, 3, tzinfo=timezone.utc)
LONG_TEXT = "Build and test web applications with our engineering team every day. "


def job(description=LONG_TEXT, title="Software Intern", company="Acme", url="https://acme.com/jobs/1"):
    return {"title": title, "description": description, "company": company, "apply_url": url}


def test_fee_requests_are_rejected():
    for text in (
        "Pay a registration fee of Rs 500 to start.",
        "A refundable deposit is needed before joining.",
        "Interns must pay the security deposit on day one.",
        "Training fees apply for selected students.",
    ):
        assert check_job(job(text))[0] == "asks_for_money", text


def test_saying_there_is_no_fee_is_not_a_scam():
    for text in (
        "There is no registration fee for this program.",
        "We never charge a security deposit.",
        "Do not pay any training fee to anyone.",
    ):
        assert check_job(job(text))[0] is None, text


def test_hiring_over_messenger_is_rejected():
    assert check_job(job("Send your CV on WhatsApp to get started."))[0] == "hires_over_messenger"
    assert check_job(job("Join our Telegram channel for tasks."))[0] == "hires_over_messenger"
    assert check_job(job("We are building a WhatsApp integration for banks."))[0] is None
    assert check_job(job("Contact clients on WhatsApp and follow up on leads."))[0] is None
    assert check_job(job("Contact us on WhatsApp to apply."))[0] == "hires_over_messenger"


def test_unrealistic_pay_is_rejected():
    assert check_job(job("Earn up to Rs 5,000 per day from home."))[0] == "unrealistic_pay_promise"
    assert check_job(job("Guaranteed placement after the course."))[0] == "unrealistic_pay_promise"
    assert check_job(job("Stipend of 15,000 per month."))[0] is None


def test_disguised_apply_links_are_rejected():
    assert check_job(job(url="https://bit.ly/abc"))[0] == "apply_link_is_disguised"
    assert check_job(job(url="https://wa.me/919999999999"))[0] == "apply_link_is_messenger"


def test_softer_signals_only_warn():
    assert check_job(job("Mail your resume to hr.acme@gmail.com"))[1] == ["personal_email"]
    assert check_job(job("Call HR on 9876543210 to apply"))[1] == ["phone_contact"]
    assert check_job(job(url="https://forms.gle/abc"))[1] == ["google_form"]
    assert check_job(job(company="Acme Staffing Services"))[1] == ["recruiting_agency"]


def test_apply_link_must_match_the_company_or_a_known_hiring_site():
    assert check_job(job(url="https://acme.com/jobs/1"))[1] == []
    assert check_job(job(url="https://careers.acme.in/1"))[1] == []
    assert check_job(job(url="https://boards.greenhouse.io/acme/1"))[1] == []
    assert check_job(job(url="https://internshala.com/internship/detail/x"))[1] == []
    assert check_job(job(url="https://free-jobs-now.xyz/1"))[1] == ["apply_link_mismatch"]


def test_real_companies_are_not_treated_as_spam():
    for company in ("Lyft Inc", "Tata Consultancy Services Ltd", "Zoho Ltd", "Infosys Solutions Pvt Ltd"):
        spam, reason = is_spam(job(company=company))
        assert spam is False, (company, reason)

    spam, _ = is_spam(job("Comes with immediate joining for the right person in our team."))
    assert spam is False


def test_spam_signals_match_whole_words():
    assert is_spam(job(LONG_TEXT + " We use xmlmapper daily."))[0] is False
    assert is_spam(job(LONG_TEXT + " This is an MLM business."))[0] is True


def test_internal_and_international_are_not_internships():
    for title in ("Assistant Manager - Internal Audit", "Director, US International Tax Planning",
                  "Software Engineer, Internal Identity", "AI Engineer, Internal Tools"):
        assert not is_internship({"title": title, "job_type": "Full Time"}), title


def test_real_internships_are_still_found():
    for title in ("Data Analyst, Intern", "Software Engineering Interns", "Summer Internship 2027",
                  "Graduate Trainee", "Apprentice Engineer", "Summer Analyst"):
        assert is_internship({"title": title}), title
    assert is_internship({"title": "Marketing", "job_type": "Internship"})
    assert not is_internship({"title": "Marketing", "job_type": "International"})


def test_student_mode_keeps_real_student_roles():
    assert is_student_eligible({"title": "Software Engineering Intern"})
    assert is_student_eligible({"title": "Graduate Trainee"})
    assert is_student_eligible({"title": "Product Manager Intern"})
    assert is_student_eligible({"title": "Backend Developer", "description": "Open to freshers, 2026 batch."})
    assert is_student_eligible({"title": "Marketing", "job_type": "Internship"})


def test_student_mode_drops_experienced_roles():
    for title in ("Senior Software Engineer", "Sr. Analyst", "Audit Operations Lead",
                  "Partner Development Manager", "Account Executive, Startups", "Head of Growth"):
        assert not is_student_eligible({"title": title, "description": "Open to freshers."}), title


def test_student_mode_ignores_wording_common_in_senior_jobs():
    for description in ("Undergraduate degree required.", "We are pursuing growth.",
                        "Take products from 0 to 1 at scale.", "Entry level sales experience is a plus."):
        assert not is_student_eligible({"title": "Account Specialist", "description": description}), description
    assert not is_student_eligible({"title": "Senior Internal Auditor"})
    assert not is_student_eligible({"title": "Internal Auditor"})


def trust(source="greenhouse", days_ago=1, flags=None):
    row = {"source": source, "last_verified_at": NOW - timedelta(days=days_ago), "scam_flags": flags or []}
    return describe_trust(row, NOW)


def test_verified_needs_a_direct_link_a_recent_check_and_no_warnings():
    result = trust()
    assert result["verified"] is True
    assert result["warnings"] == []
    assert result["reasons"] == [
        "Apply link goes to the company's own hiring page",
        "Last confirmed live on 2 Nov 2026",
    ]
    assert trust(days_ago=30)["verified"] is False
    assert trust(flags=["google_form"])["verified"] is False


def test_marketplace_jobs_are_never_called_verified():
    result = trust(source="internshala")
    assert result["verified"] is False
    assert result["warnings"] == ["Posted on a public job site. We have not checked the employer"]


def test_trust_handles_missing_and_text_dates():
    assert describe_trust({"source": "lever"}, NOW)["verified"] is False
    assert describe_trust({"source": "lever", "last_verified_at": "2026-11-02T10:00:00+00:00"}, NOW)["verified"] is True
    assert describe_trust({"source": "lever", "last_verified_at": "bad"}, NOW)["verified"] is False


def test_duration_parsing():
    assert parse_duration_months("Mumbai 6 Months") == 6
    assert parse_duration_months("8 Weeks") == 2
    assert parse_duration_months("Mumbai") is None
    assert parse_duration_months(None) is None
