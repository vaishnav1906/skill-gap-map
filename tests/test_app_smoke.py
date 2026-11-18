"""Run the whole app headlessly with a few profiles and settings: nothing may raise."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def run(**changes):
    at = AppTest.from_file(APP, default_timeout=180).run()
    for key, value in changes.items():
        if key in ("skills", "weeks"):
            at.session_state[key] = value
        elif key == "role":
            at.selectbox(key="role_pick").set_value(value)
        elif key == "cities":
            at.multiselect(key="city_pick").set_value(value)
        elif key == "years":
            at.slider(key="years_pick").set_value(value)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_default_profile_runs_all_tabs():
    at = run()
    assert len(at.tabs) == 5
    text = " ".join(m.value for m in at.markdown)
    assert "postings" in text and "Checked:" in text


@pytest.mark.parametrize("role", ["Business Analyst", "Data Engineer", "Product / Marketing", "BI / Reporting"])
def test_other_roles(role):
    run(role=role)


def test_empty_profile_and_tiny_market():
    run(skills=[], role="BI / Reporting", years=0)            # no postings: the app explains and stops cleanly


def test_everything_known_and_one_city():
    run(skills=["SQL", "Excel", "Power BI", "Tableau", "Python", "Statistics", "Data analysis", "Data visualization"],
        cities=["Pune"])


def test_cleared_learning_time_does_not_crash():
    """Review finding: an emptied cell in the learning-time editor used to drop skills from the weeks dict -> KeyError."""
    run(weeks={"Python": 3.0})


def test_experience_filter_off_hides_pay_comparison():
    at = AppTest.from_file(APP, default_timeout=180).run()
    at.toggle[0].set_value(False).run()
    assert not at.exception
    assert "Pay comparison" in " ".join(m.value for m in at.markdown)
