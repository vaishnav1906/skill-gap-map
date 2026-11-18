"""The skills dictionary and the resume/description reader."""
import pytest

from skills import CATEGORY, CATEGORY_ORDER, NAMES, SKILLS, TAG_TO_SKILL, WEEKS, skills_from_tags, skills_from_text


def test_every_skill_is_complete_and_unique():
    assert len(NAMES) == len(set(NAMES))
    for name, cat, weeks, aliases in SKILLS:
        assert cat in CATEGORY_ORDER, name
        assert 0 < weeks <= 52, name
        assert all(a == a.lower().strip() for a in aliases), name


def test_each_alias_maps_to_exactly_one_skill():
    # building TAG_TO_SKILL raises on a clash, so it is enough that every alias is present and points home
    for name, _, _, aliases in SKILLS:
        for a in [name.lower(), *aliases]:
            assert TAG_TO_SKILL[a] == name


def test_generic_tags_map_to_nothing():
    generic = ["analytical", "data", "coding", "computer science", "communication skills", "healthcare", "data science",
               "data scientist", "business analyst", "analytics", "development", "algorithms", "data management"]
    assert skills_from_tags(generic) == set()


def test_tags_are_normalised():
    assert skills_from_tags(["  Power BI ", "MICROSOFT POWER BI", "Py Spark"]) == {"Power BI"}
    assert skills_from_tags(["PySpark", "pyspark"]) == {"PySpark"}


@pytest.mark.parametrize("text, expected", [
    ("Skills: Python, R, SQL, Tableau, MS Excel", {"Python", "R", "SQL", "Tableau", "Excel"}),
    ("Java and JavaScript", {"Java", "JavaScript"}),
    ("C++ and C#, .NET", {"C++", "C#"}),
    ("ReactJS, Node.js, Golang", {"React", "JavaScript", "Go"}),
    ("Built dashboards in Power BI", {"Power BI", "Data visualization"}),
    ("Experience with AI/ML, Gen AI and LLMs", {"Machine learning", "Generative AI"}),
    ("Pandas, NumPy and scikit-learn", {"Pandas", "NumPy", "scikit-learn"}),
    ("Python / R / SQL", {"Python", "R", "SQL"}),
    ("Advanced Excel (pivot tables, VLOOKUP)", {"Excel"}),
    ("market research and digital marketing campaigns", {"Market research", "Digital marketing"}),
    # review findings: plain mentions that were missed
    ("Excel", {"Excel"}),
    ("Proficient in Excel.", {"Excel"}),
    ("Skills: SQL; Excel; Tableau", {"SQL", "Excel", "Tableau"}),
    ("basic understanding of Word and excel", {"Excel"}),
    ("Tools: SQL, R", {"SQL", "R"}),
    ("agile methodology and scrum", {"Agile"}),
    ("lean six sigma", {"Process improvement"}),
    ("Apache Spark and PySpark", {"Spark", "PySpark"}),
    ("Snowflake, dbt", {"Snowflake", "dbt"}),
    ("strong in data structures and algorithms", {"Data structures & algorithms"}),
    ("algorithms, data structures and Java", {"Data structures & algorithms", "Java"}),
])
def test_finds_skills_in_text(text, expected):
    assert skills_from_text(text) == expected


@pytest.mark.parametrize("text", [
    "I excel at teamwork",
    "Go-to-market strategy and go-getter attitude",
    "React quickly to customer feedback",
    "Microsoft(R) Windows",
    "Reporting to the head of sales",
    "We work with stakeholders across the business",
    "A leader in AI, cloud and data",            # company boilerplate, not a requirement
    "Strong knowledge of machine learning algorithms and frameworks",
    "Scalable systems and R&D culture",
    "We spark curiosity in your team",   # capitalised "Spark" is kept: in job text it nearly always means Apache Spark
    # review findings: false positives
    "I spark curiosity and love pandas at the zoo",
    "Follow us on social media",
    "Worked on power transformers",
    "Weather forecast app",
    "Snowflake schema design",
    "secure data structures and pipelines",
])
def test_ordinary_words_do_not_count(text):
    found = skills_from_text(text)
    assert not (found & {"Excel", "Go", "React", "R", "MIS reporting", "Stakeholder management", "Artificial intelligence",
                         "Data structures & algorithms", "Scala", "Spark", "Pandas", "Digital marketing", "Deep learning",
                         "Forecasting", "Snowflake"}), found


def test_html_is_ignored():
    assert skills_from_text("<b>Python</b><br>SQL") == {"Python", "SQL"}
    assert skills_from_text("") == set()


def test_every_skill_can_be_found_from_its_own_name():
    """Typing a skill's name in a resume finds it (the names people see in the app)."""
    hard = {"R": "Python, R", "Go": "Golang", "Excel": "MS Excel", "MS Office": "MS Office", "React": "ReactJS",
            "Spring": "Spring Boot", "Artificial intelligence": "artificial intelligence",
            "Business intelligence": "business intelligence", "MIS reporting": "MIS", "APIs": "REST APIs",
            "Consulting": "management consulting", "Hive": "Hive", "Agile": "Agile", "Linux": "Linux",
            "Regression": "linear regression", "Optimization": "operations research"}
    for name in NAMES:
        assert name in skills_from_text(hard.get(name, name)), name


@pytest.mark.parametrize("text, skill", [("aws", "AWS"), ("nlp", "NLP"), ("git", "Git"), ("devops", "DevOps & CI/CD"),
                                         ("powerpoint", "MS Office"), ("genai", "Generative AI"), ("sap", "SAP / ERP"),
                                         ("rest api", "APIs"), ("a/b testing", "A/B testing"), ("sql", "SQL")])
def test_lower_case_acronyms_in_resumes(text, skill):
    assert skill in skills_from_text(f"skills: {text}, teamwork")


def test_weeks_and_categories_cover_every_skill():
    assert set(WEEKS) == set(NAMES) == set(CATEGORY)


def test_skills_in_order_follows_first_mention():
    from skills import skills_in_order
    assert skills_in_order("Tableau dashboards, then SQL and Python") == ["Tableau", "Data visualization", "SQL", "Python"]


def test_implied_skills_follow_chains():
    from skills import with_implied
    assert with_implied(["scikit-learn"]) >= {"Python", "Machine learning", "Artificial intelligence"}
    assert with_implied(["Excel"]) == {"Excel"}
