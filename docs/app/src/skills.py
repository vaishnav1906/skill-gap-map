"""The skills dictionary: canonical skills, the tag spellings that map to them, and a resume-text extractor.

Job portals tag the same skill many ways ("power bi", "microsoft power bi", "dax"). Each canonical skill lists
the spellings that count as it. Tags that are not skills (role names, soft skills, industries, filler words such
as "data" or "coding") map to nothing, so they never count for or against anyone.

`weeks` is a rough guess at the time to job-ready basics for someone with a technical degree. It is only used
when the plan is ranked by effort, and the app lets you edit it.
"""
import re

# name, category, weeks, aliases (lower-case tag spellings; the name itself always counts)
SKILLS = [
    # Programming
    ("Python", "Programming", 8, ["python development", "python programming", "python3", "core python", "python scripting"]),
    ("SQL", "Programming", 4, ["sql queries", "sql development", "sql database", "sql programming", "t-sql", "tsql",
                                "sql coding", "advanced sql", "rdbms", "dbms", "relational databases"]),
    ("R", "Programming", 6, ["r programming", "r language", "r studio", "rstudio"]),
    ("Scala", "Programming", 8, []),
    ("Java", "Programming", 10, ["core java", "java development", "java programming", "j2ee", "java 8"]),
    ("C++", "Programming", 10, ["cpp"]),
    ("C#", "Programming", 8, [".net", "asp.net", "dotnet"]),
    ("JavaScript", "Programming", 8, ["javascript", "js", "jquery", "node.js", "nodejs", "node js", "typescript"]),
    ("Go", "Programming", 8, ["golang"]),
    ("SAS", "Programming", 6, ["base sas", "sas programming", "sas macros"]),
    ("MATLAB", "Programming", 4, []),
    ("Shell scripting", "Programming", 3, ["unix shell scripting", "bash", "shell", "bash scripting", "powershell"]),
    ("HTML & CSS", "Programming", 3, ["html", "css", "html5", "css3"]),
    # Analytics & BI
    ("Data analysis", "Analytics & BI", 4, ["data analytics", "data analyst", "business analytics", "advanced analytics",
                                            "analytics reporting", "data interpretation"]),
    ("Statistics", "Analytics & BI", 8, ["statistical analysis", "statistical modeling", "statistical modelling",
                                         "statistical", "probability", "statistical techniques", "applied statistics"]),
    ("A/B testing", "Analytics & BI", 3, ["ab testing", "a/b test", "hypothesis testing", "experimentation",
                                         "experiment design", "experimental design"]),
    ("Forecasting", "Analytics & BI", 4, ["time series", "time series analysis", "demand forecasting", "sales forecasting",
                                         "time series forecasting"]),
    ("Predictive modeling", "Analytics & BI", 6, ["predictive modelling", "predictive analytics", "predictive analysis",
                                                  "predictive models"]),
    ("Regression", "Analytics & BI", 3, ["linear regression", "logistic regression", "regression analysis"]),
    ("Data visualization", "Analytics & BI", 3, ["data visualisation", "visualization", "visualisation", "dashboards",
                                                 "dashboarding", "dashboard", "dashboard development", "data visualization tools"]),
    ("Excel", "Analytics & BI", 2, ["ms excel", "advanced excel", "microsoft excel", "excel macros", "vba", "macros",
                                    "pivot tables", "vlookup"]),
    ("Power BI", "Analytics & BI", 3, ["powerbi", "microsoft power bi", "dax", "power query", "power bi desktop"]),
    ("Tableau", "Analytics & BI", 3, ["tableau desktop"]),
    ("Qlik", "Analytics & BI", 3, ["qlikview", "qlik sense", "qliksense"]),
    ("Looker", "Analytics & BI", 2, ["looker studio", "google data studio", "data studio"]),
    ("Google Analytics", "Analytics & BI", 2, ["ga4", "web analytics", "google tag manager", "adobe analytics"]),
    ("SPSS", "Analytics & BI", 2, []),
    ("Data cleaning", "Analytics & BI", 2, ["data cleansing", "data munging", "data manipulation", "data wrangling",
                                           "data preparation", "data preprocessing"]),
    ("Data mining", "Analytics & BI", 4, ["text mining"]),
    ("Business intelligence", "Analytics & BI", 4, ["bi", "bi tools", "bi reporting"]),
    ("MIS reporting", "Analytics & BI", 2, ["mis", "reporting", "mis reporting", "reporting tools", "report generation"]),
    ("SSIS / SSRS", "Analytics & BI", 4, ["ssis", "ssrs", "ssas", "msbi"]),
    ("MicroStrategy", "Analytics & BI", 3, []),
    # Machine learning & AI
    ("Machine learning", "Machine learning & AI", 12, ["ml", "machine learning algorithms", "aiml", "ai/ml", "ai ml",
                                                       "ml algorithms", "machine learning models", "machine learning engineering"]),
    ("Deep learning", "Machine learning & AI", 10, ["neural networks", "neural network", "cnn", "rnn", "lstm", "transformers"]),
    ("NLP", "Machine learning & AI", 8, ["natural language processing", "text analytics", "nlu"]),
    ("Computer vision", "Machine learning & AI", 8, ["image processing", "opencv", "object detection"]),
    ("Generative AI", "Machine learning & AI", 6, ["gen ai", "genai", "llm", "llms", "large language models",
                                                  "prompt engineering", "rag", "langchain", "generative ai models", "gpt"]),
    ("TensorFlow", "Machine learning & AI", 4, ["keras"]),
    ("PyTorch", "Machine learning & AI", 4, []),
    ("scikit-learn", "Machine learning & AI", 3, ["sklearn", "scikit learn"]),
    ("Pandas", "Machine learning & AI", 3, []),
    ("NumPy", "Machine learning & AI", 2, []),
    ("MLOps", "Machine learning & AI", 6, ["ml ops", "mlflow", "model deployment", "sagemaker", "kubeflow", "vertex ai"]),
    ("Artificial intelligence", "Machine learning & AI", 8, ["ai", "artificial intelligence"]),
    ("Optimization", "Machine learning & AI", 8, ["operations research", "linear programming", "mathematical optimization"]),
    # Data engineering
    ("Spark", "Data engineering", 6, ["apache spark", "spark sql", "spark streaming"]),
    ("PySpark", "Data engineering", 4, []),
    ("Hadoop & big data", "Data engineering", 6, ["hadoop", "big data", "hdfs", "cloudera", "mapreduce", "big data technologies",
                                                  "big data analytics", "hbase", "sqoop"]),
    ("Hive", "Data engineering", 3, ["hiveql", "apache hive"]),
    ("Kafka", "Data engineering", 4, ["apache kafka"]),
    ("Airflow", "Data engineering", 3, ["apache airflow"]),
    ("ETL", "Data engineering", 4, ["etl process", "etl pipelines", "etl tools", "etl development", "data pipeline",
                                    "data pipelines", "data integration", "data ingestion", "elt", "etl testing"]),
    ("Data warehousing", "Data engineering", 6, ["data warehouse", "dwh", "olap", "data lake", "data lakes", "azure data lake",
                                                 "delta lake", "data lakehouse", "lakehouse"]),
    ("Data modeling", "Data engineering", 5, ["data modelling", "database design", "dimensional modeling",
                                              "dimensional modelling", "data architecture", "star schema"]),
    ("Snowflake", "Data engineering", 3, []),
    ("Databricks", "Data engineering", 4, ["azure databricks", "data bricks"]),
    ("dbt", "Data engineering", 2, []),
    ("Informatica", "Data engineering", 5, ["informatica powercenter", "iics", "informatica cloud"]),
    ("Azure Data Factory", "Data engineering", 4, ["adf", "datafactory", "data factory"]),
    ("Talend", "Data engineering", 4, []),
    ("Data quality & governance", "Data engineering", 4, ["data quality", "data governance", "data lineage",
                                                          "master data management", "mdm", "data stewardship",
                                                          "data validation", "data integrity"]),
    # Cloud
    ("AWS", "Cloud", 8, ["amazon web services", "aws cloud", "aws glue", "glue", "s3", "emr", "redshift", "amazon redshift",
                         "lambda", "ec2", "aws lambda", "athena"]),
    ("Azure", "Cloud", 8, ["microsoft azure", "azure cloud", "azure synapse", "synapse", "sql azure", "azure sql",
                           "azure functions"]),
    ("GCP", "Cloud", 8, ["google cloud", "google cloud platform", "bigquery", "big query", "dataflow", "dataproc"]),
    # Databases
    ("MySQL", "Databases", 2, []),
    ("PostgreSQL", "Databases", 2, ["postgres"]),
    ("Oracle", "Databases", 4, ["oracle database", "oracle sql", "oracle db"]),
    ("PL/SQL", "Databases", 4, ["plsql", "pl sql", "stored procedures"]),
    ("SQL Server", "Databases", 3, ["ms sql", "mssql", "ms sql server", "microsoft sql server", "ssms"]),
    ("MongoDB", "Databases", 3, ["mongo db"]),
    ("NoSQL", "Databases", 4, ["cassandra", "dynamodb", "cosmos", "cosmos db", "cosmosdb", "redis", "elasticsearch"]),
    ("Teradata", "Databases", 3, []),
    # Engineering practices
    ("Git", "Engineering practices", 1, ["github", "gitlab", "version control", "bitbucket"]),
    ("Docker", "Engineering practices", 2, ["containerization"]),
    ("Kubernetes", "Engineering practices", 5, ["k8s", "aks", "eks"]),
    ("DevOps & CI/CD", "Engineering practices", 5, ["devops", "ci/cd", "ci cd", "continuous integration", "jenkins",
                                                     "azure devops", "continuous delivery", "cicd"]),
    ("Linux", "Engineering practices", 3, ["unix"]),
    ("APIs", "Engineering practices", 3, ["api", "rest", "rest api", "restful", "web services", "microservices",
                                          "rest apis", "api development"]),
    ("Python web frameworks", "Engineering practices", 5, ["django", "flask", "fastapi"]),
    ("React", "Engineering practices", 8, ["react.js", "reactjs", "react js"]),
    ("Spring", "Engineering practices", 8, ["spring boot", "hibernate", "springboot"]),
    ("Software testing", "Engineering practices", 4, ["unit testing", "automation testing", "selenium", "test cases",
                                                      "tdd", "integration testing", "performance testing", "manual testing"]),
    ("System design", "Engineering practices", 10, ["software design", "system architecture", "solution architecture",
                                                    "architectural design", "solution design"]),
    ("Data structures & algorithms", "Engineering practices", 12, ["data structures", "dsa", "data structures and algorithms"]),
    ("Terraform", "Engineering practices", 3, []),
    ("Agile", "Engineering practices", 1, ["scrum", "agile methodology", "agile development", "kanban", "sdlc",
                                           "software development life cycle", "agile scrum"]),
    ("JIRA", "Engineering practices", 1, ["confluence"]),
    # Business & product
    ("Business analysis", "Business & product", 6, ["gap analysis", "business process", "process mapping",
                                                    "business process mapping", "visio", "uml", "business process analysis"]),
    ("Requirements gathering", "Business & product", 3, ["requirement gathering", "requirements analysis",
                                                         "requirement analysis", "business requirement analysis",
                                                         "business requirements", "brd", "frd", "user stories", "use cases",
                                                         "functional specifications"]),
    ("UAT", "Business & product", 2, ["user acceptance testing"]),
    ("Stakeholder management", "Business & product", 4, ["client management", "stakeholder engagement"]),
    ("Project management", "Business & product", 6, ["project planning", "project delivery", "pmp", "program management",
                                                     "project coordination", "prince2"]),
    ("Product management", "Business & product", 8, ["product strategy", "product roadmap", "product owner"]),
    ("Process improvement", "Business & product", 4, ["continuous improvement", "six sigma", "lean", "operational excellence",
                                                      "lean six sigma", "process optimization"]),
    ("Financial analysis", "Business & product", 8, ["financial modeling", "financial modelling", "financial planning", "fp&a",
                                                     "budgeting", "financial reporting", "variance analysis"]),
    ("Market research", "Business & product", 4, ["competitive analysis", "industry research", "competitor analysis",
                                                  "consumer research"]),
    ("Digital marketing", "Business & product", 6, ["social media", "social media marketing", "performance marketing",
                                                    "email marketing", "content marketing", "marketing analytics",
                                                    "campaign management"]),
    ("SEO / SEM", "Business & product", 4, ["seo", "sem", "google ads", "search engine optimization", "ppc"]),
    ("CRM", "Business & product", 3, ["salesforce", "microsoft dynamics", "hubspot", "crm tools"]),
    ("SAP / ERP", "Business & product", 8, ["sap", "erp", "sap hana", "sap bw", "oracle erp"]),
    ("Consulting", "Business & product", 8, ["management consulting", "presales"]),
    ("Risk management", "Business & product", 6, ["risk assessment", "credit risk", "risk analytics", "risk analysis",
                                                  "market risk"]),
    ("Supply chain", "Business & product", 6, ["supply chain management", "logistics", "procurement", "inventory management",
                                               "demand planning"]),
    ("MS Office", "Business & product", 1, ["powerpoint", "ms powerpoint", "ms word", "microsoft office", "ms office suite"]),
]

CATEGORY_ORDER = ["Programming", "Analytics & BI", "Machine learning & AI", "Data engineering", "Cloud", "Databases",
                  "Engineering practices", "Business & product"]

NAMES = [s[0] for s in SKILLS]
CATEGORY = {s[0]: s[1] for s in SKILLS}
WEEKS = {s[0]: s[2] for s in SKILLS}

TAG_TO_SKILL: dict[str, str] = {}
for _name, _cat, _w, _aliases in SKILLS:
    for _a in [_name.lower(), *_aliases]:
        if _a in TAG_TO_SKILL and TAG_TO_SKILL[_a] != _name:
            raise ValueError(f"alias {_a!r} maps to both {TAG_TO_SKILL[_a]} and {_name}")
        TAG_TO_SKILL[_a] = _name


def normalise_tag(tag: str) -> str:
    return re.sub(r"\s+", " ", tag.strip().lower())


def skills_from_tags(tags) -> set[str]:
    """Map a list of portal tags to canonical skills; unknown or generic tags are ignored."""
    out = set()
    for t in tags:
        s = TAG_TO_SKILL.get(normalise_tag(t))
        if s:
            out.add(s)
    return out


# ---------- free text (resumes, job descriptions) ----------
# Spellings that are ordinary words or letters in prose: they only count in these exact, case-sensitive forms.
_CASE_SENSITIVE = {
    "R": [r"(?<!\()\bR\b(?=\s*(?:,|/|\)|programming|language|studio|and Python|& Python|or Python))",
          r"(?<=Python, )R\b", r"(?<=Python/)R\b", r"(?<=Python and )R\b", r"(?<=Python & )R\b", r"(?<=Python or )R\b",
          r"\bRStudio\b", r"(?<=[,;:] )R\b(?=\s*(?:[,.;)]|$|and\b|or\b))", r"(?<=[,;:])R\b(?=\s*(?:[,.;)]|$))"],
    "Go": [r"\bGolang\b", r"\bGo\b(?=\s*(?:,|/|\)|programming|language|lang\b))"],
    # "Excel" in any case, except the verb: "excel at", "excel in", "excelled", "excellent"
    "Excel": [r"(?i:\bexcel\b)(?!\s+(?:at|in|as|with|when|under)\b)", r"\bVBA\b", r"\b[Pp]ivot [Tt]ables\b", r"\bVLOOKUP\b"],
    # bare "AI" is left out: in descriptions it is mostly company boilerplate ("leading capabilities in AI, cloud...")
    "Artificial intelligence": [r"\b[Aa]rtificial [Ii]ntelligence\b"],
    "Machine learning": [r"\b[Mm]achine [Ll]earning\b", r"\bML\b", r"\bAI\s*/\s*ML\b"],
    "Business intelligence": [r"\b[Bb]usiness [Ii]ntelligence\b", r"(?<!Power )(?<!Power-)\bBI\b"],
    "MIS reporting": [r"\bMIS\b"],
    "APIs": [r"\bAPIs?\b", r"\bREST(?:ful)?\b", r"\bmicroservices\b"],
    "Agile": [r"\bAgile\b", r"(?i:\bagile (?:methodolog(?:y|ies)|development|practices|ceremonies|environment|framework|teams?)\b)",
              r"(?i:\bscrum\b)", r"\bSDLC\b", r"(?i:\bkanban\b)"],
    "Linux": [r"\bLinux\b", r"\bUnix\b", r"\bUNIX\b"],
    "Optimization": [r"\b[Oo]perations [Rr]esearch\b", r"\b[Ll]inear [Pp]rogramming\b", r"\b[Mm]athematical [Oo]ptimi[sz]ation\b"],
    "Supply chain": [r"\b[Ss]upply [Cc]hain\b", r"\b[Ii]nventory [Mm]anagement\b", r"\b[Dd]emand [Pp]lanning\b"],
    "Process improvement": [r"\b[Pp]rocess [Ii]mprovement\b", r"(?i:\b(?:lean )?six sigma\b)", r"\b[Cc]ontinuous [Ii]mprovement\b"],
    "Consulting": [r"\b[Mm]anagement [Cc]onsulting\b"],
    "Data quality & governance": [r"\b[Dd]ata [Gg]overnance\b", r"\b[Dd]ata [Qq]uality\b", r"\b[Dd]ata [Ll]ineage\b", r"\b[Mm]aster [Dd]ata\b"],
    "Spring": [r"\bSpring(?: Boot)?\b(?=\s*(?:,|/|\)|framework|boot|Boot|MVC))", r"\bSpring Boot\b", r"\bHibernate\b"],
    "Hive": [r"\bHive(?:QL)?\b"],
    "React": [r"\bReact(?:\.js|JS)\b", r"\bReact\b(?=\s*(?:,|/|\)|and\b|Native|developer|framework|hooks|Redux))",
              r"(?<=, )React\b"],
    "AWS": [r"\bAWS\b", r"\bAmazon Web Services\b", r"\bRedshift\b", r"\bSageMaker\b", r"\bEC2\b", r"\bS3\b", r"\bAthena\b",
            r"\bAWS Glue\b", r"\bEMR\b"],
    "Shell scripting": [r"\b[Ss]hell [Ss]cripting\b", r"\b[Bb]ash\b", r"\bPowerShell\b", r"\b[Ss]hell scripts?\b"],
    "Data analysis": [r"\b[Dd]ata [Aa]naly(?:sis|tics|se|ze|zing|sing)\b", r"\b[Bb]usiness [Aa]nalytics\b"],
    "Statistics": [r"\b[Ss]tatistic(?:s|al)\b", r"\b[Pp]robability\b"],
    "Forecasting": [r"\b[Ff]orecasting\b", r"\b[Tt]ime[- ][Ss]eries\b", r"\b(?:[Dd]emand|[Ss]ales) [Ff]orecasts?\b"],
    "Regression": [r"\b(?:[Ll]inear|[Ll]ogistic) [Rr]egression\b", r"\b[Rr]egression (?:analysis|models?)\b"],
    "Data visualization": [r"\b[Dd]ata [Vv]isuali[sz]ation\b", r"\b[Dd]ashboards?\b", r"\b[Vv]isuali[sz]ations?\b"],
    "Data cleaning": [r"\b[Dd]ata (?:[Cc]leaning|[Cc]leansing|[Ww]rangling|[Mm]unging|[Pp]reparation|[Pp]reprocessing)\b"],
    "Business analysis": [r"\b[Bb]usiness [Aa]nalysis\b", r"\b[Gg]ap [Aa]nalysis\b", r"\b[Pp]rocess [Mm]apping\b",
                          r"\b[Bb]usiness [Pp]rocess (?:[Mm]apping|[Mm]odel(?:l)?ing|[Aa]nalysis)\b", r"\bVisio\b", r"\bUML\b"],
    "Requirements gathering": [r"\b[Rr]equirements? (?:[Gg]athering|[Aa]nalysis|[Ee]licitation)\b", r"\bBRDs?\b", r"\bFRDs?\b",
                               r"\b[Uu]ser [Ss]tories\b"],
    "UAT": [r"\bUAT\b", r"\b[Uu]ser [Aa]cceptance [Tt]esting\b"],
    "Stakeholder management": [r"\b[Ss]takeholder (?:[Mm]anagement|[Ee]ngagement)\b"],
    "Project management": [r"\b[Pp]roject [Mm]anagement\b", r"\bPMP\b", r"\b[Pp]rogram(?:me)? [Mm]anagement\b", r"\bPRINCE2\b"],
    "Product management": [r"\b[Pp]roduct [Mm]anagement\b", r"\b[Pp]roduct [Rr]oadmaps?\b", r"\b[Pp]roduct [Ss]trategy\b",
                           r"\b[Pp]roduct [Oo]wner\b"],
    "Financial analysis": [r"\b[Ff]inancial (?:[Aa]nalysis|[Mm]odel(?:l)?ing|[Pp]lanning|[Rr]eporting)\b", r"\bFP&A\b",
                           r"\b[Bb]udgeting\b", r"\b[Vv]ariance [Aa]nalysis\b"],
    "Market research": [r"\b[Mm]arket [Rr]esearch\b", r"\b[Cc]ompetit(?:ive|or) [Aa]nalysis\b", r"\b[Cc]onsumer [Rr]esearch\b"],
    "Digital marketing": [r"\b[Dd]igital [Mm]arketing\b", r"\b[Ss]ocial [Mm]edia (?:[Mm]arketing|[Cc]ampaigns?|[Aa]nalytics|[Ss]trategy)\b",
                          r"\b[Pp]erformance [Mm]arketing\b",
                          r"\b[Ee]mail [Mm]arketing\b", r"\b[Cc]ontent [Mm]arketing\b", r"\b[Mm]arketing [Aa]nalytics\b",
                          r"\b[Cc]ampaign [Mm]anagement\b"],
    "SEO / SEM": [r"\bSEO\b", r"\bSEM\b", r"\bGoogle Ads\b", r"\bPPC\b", r"\b[Ss]earch [Ee]ngine [Oo]ptimi[sz]ation\b"],
    "CRM": [r"\bCRM\b", r"\bSalesforce\b", r"\bHubSpot\b", r"\bMicrosoft Dynamics\b"],
    "SAP / ERP": [r"\bSAP\b", r"\bERP\b"],
    "Risk management": [r"\b[Rr]isk (?:[Mm]anagement|[Aa]ssessment|[Aa]nalytics|[Aa]nalysis)\b", r"\b[Cc]redit [Rr]isk\b",
                        r"\b[Mm]arket [Rr]isk\b"],
    "MS Office": [r"\bMS Office\b", r"\bMicrosoft Office\b", r"\bPowerPoint\b", r"\bMS Word\b", r"\bPPT\b"],
    "Data mining": [r"\b[Dd]ata [Mm]ining\b", r"\b[Tt]ext [Mm]ining\b"],
    "Predictive modeling": [r"\b[Pp]redictive (?:[Mm]odel(?:l)?ing|[Aa]nalytics|[Mm]odels?)\b"],
    "A/B testing": [r"\bA/B\b", r"\bAB [Tt]est(?:s|ing)?\b", r"\b[Hh]ypothesis [Tt]esting\b", r"\b[Ee]xperiment(?:ation| design)\b"],
    "Data modeling": [r"\b[Dd]ata [Mm]odel(?:l)?ing\b", r"\b[Dd]imensional [Mm]odel(?:l)?ing\b", r"\b[Dd]atabase [Dd]esign\b",
                      r"\b[Dd]ata [Aa]rchitecture\b", r"\b[Ss]tar [Ss]chema\b"],
    "Data warehousing": [r"\b[Dd]ata [Ww]arehous(?:e|es|ing)\b", r"\bDWH\b", r"\bOLAP\b", r"\b[Dd]ata [Ll]ake(?:s|house)?\b",
                         r"\b[Ll]akehouse\b", r"\bDelta Lake\b"],
    "ETL": [r"\bETL\b", r"\bELT\b", r"\b[Dd]ata [Pp]ipelines?\b", r"\b[Dd]ata [Ii]ntegration\b", r"\b[Dd]ata [Ii]ngestion\b"],
    "Software testing": [r"\b[Uu]nit [Tt]esting\b", r"\b[Aa]utomation [Tt]esting\b", r"\bSelenium\b", r"\bTDD\b",
                         r"\b[Ii]ntegration [Tt]esting\b", r"\b[Mm]anual [Tt]esting\b", r"\b[Tt]est [Cc]ases\b"],
    "System design": [r"\b[Ss]ystem [Dd]esign\b", r"\b[Ss]oftware [Dd]esign\b", r"\b[Ss]ystem [Aa]rchitecture\b",
                      r"\b[Ss]olution [Aa]rchitecture\b"],
    "Data structures & algorithms": [r"(?i:\bdata structures? (?:and|&) algorithms?\b)",
                                     r"(?i:\balgorithms?\s*(?:and|&|,)\s*data structures?\b)", r"\bDSA\b"],
    "DevOps & CI/CD": [r"\bDevOps\b", r"\bCI/CD\b", r"\bCI ?CD\b", r"\b[Cc]ontinuous [Ii]ntegration\b", r"\bJenkins\b"],
    "Hadoop & big data": [r"\bHadoop\b", r"\b[Bb]ig [Dd]ata\b", r"\bHDFS\b", r"\bCloudera\b", r"\bMapReduce\b", r"\bHBase\b"],
    "Generative AI": [r"\b[Gg]enerative AI\b", r"\bGen ?AI\b", r"\bLLMs?\b", r"\b[Ll]arge [Ll]anguage [Mm]odels?\b",
                      r"\b[Pp]rompt [Ee]ngineering\b", r"\bRAG\b", r"\bLangChain\b", r"\bGPT(?:-\d)?\b"],
    "NLP": [r"\bNLP\b", r"\b[Nn]atural [Ll]anguage [Pp]rocessing\b", r"\b[Tt]ext [Aa]nalytics\b"],
    "Computer vision": [r"\b[Cc]omputer [Vv]ision\b", r"\b[Ii]mage [Pp]rocessing\b", r"\bOpenCV\b", r"\b[Oo]bject [Dd]etection\b"],
    "Deep learning": [r"\b[Dd]eep [Ll]earning\b", r"\b[Nn]eural [Nn]etworks?\b", r"\bCNNs?\b", r"\bRNNs?\b", r"\bLSTMs?\b",
                      r"\b[Tt]ransformer (?:models?|architectures?)\b", r"\bHugging ?Face\b"],
    "Snowflake": [r"\bSnowflake\b(?! [Ss]chemas?)"],
    "Spark": [r"\b(?:Apache )?Spark\b", r"(?i:\bspark (?:sql|streaming|jobs?|applications?|clusters?)\b)", r"(?i:\bapache spark\b)"],
    "Pandas": [r"\bPandas\b(?! at\b)", r"\bpandas\b(?=\s*(?:,|/|\)|and NumPy|& NumPy|library|dataframes?))", r"(?<=\()pandas\b"],
    "MLOps": [r"\bMLOps\b", r"\bMLflow\b", r"\b[Mm]odel [Dd]eployment\b", r"\bSageMaker\b", r"\bKubeflow\b", r"\bVertex AI\b"],
    "Git": [r"\bGit(?:Hub|Lab)?\b", r"\b[Vv]ersion [Cc]ontrol\b", r"\bBitbucket\b"],
}
assert set(_CASE_SENSITIVE) <= set(CATEGORY), set(_CASE_SENSITIVE) - set(CATEGORY)

# Case-insensitive patterns for every other skill: the name plus multi-character aliases, on word boundaries.
_SKIP_ALIASES = {"bi", "mis", "rest", "api", "ai", "ml", "sem", "seo", "lean", "glue", "shell", "lambda", "s3", "emr",
                 "cosmos", "adf", "js", "r", "go", "cpp", "reporting", "dashboard", "dashboards", "visualization",
                 "visualisation", "statistical", "probability", "algorithms", "uml", "visio", "logistics", "unix",
                 "sap", "erp", "crm", "uat", "pmp", "brd", "frd", "dsa", "rag", "gpt", "cnn", "rnn", "lstm", "nlu",
                 "mdm", "social media", "budgeting", "procurement", "macros", "vba",
                 "transformers", "redis", "rest api", "api development", "rest apis", "restful", "web services",
                 "microservices", "elt", "dwh", "olap", "k8s", "aks", "eks", "dataflow", "synapse", "athena", "ec2",
                 "presales", "excel macros", "pivot tables", "vlookup", "ppc", "lake", "visualization tools"}


def _pattern(alias: str) -> str:
    esc = re.escape(alias).replace(r"\ ", r"[\s\-]")
    left = r"(?<![\w+#.])" if alias[0].isalnum() else r"(?<!\w)"
    right = r"(?![\w+#])" if alias[-1].isalnum() else r"(?!\w)"
    return left + esc + right


# Spellings that are safe in any case for skills that otherwise need exact case (people type "aws" or "nlp" in resumes).
_ANY_CASE = {
    "AWS": ["aws", "amazon web services"], "NLP": ["nlp", "natural language processing"], "MLOps": ["mlops", "mlflow"],
    "ETL": ["etl", "data pipelines", "data pipeline"], "Git": ["git", "github", "gitlab"], "Hive": ["hiveql", "apache hive"],
    "DevOps & CI/CD": ["devops", "ci/cd", "jenkins"], "Linux": ["linux"], "UAT": ["uat", "user acceptance testing"],
    "CRM": ["crm", "salesforce", "hubspot"], "SEO / SEM": ["seo", "google ads"], "SAP / ERP": ["sap", "erp"],
    "MS Office": ["ms office", "microsoft office", "powerpoint"], "APIs": ["api", "apis", "rest api", "rest apis"],
    "Generative AI": ["generative ai", "genai", "gen ai", "llm", "llms", "langchain", "prompt engineering"],
    "A/B testing": ["a/b testing", "a/b test", "ab testing", "hypothesis testing"], "MIS reporting": ["mis reporting"],
    "Software testing": ["software testing", "unit testing", "selenium", "automation testing", "manual testing"],
    "Regression": ["linear regression", "logistic regression", "regression analysis"],
    "Optimization": ["operations research", "linear programming"],
}
assert set(_ANY_CASE) <= set(CATEGORY), set(_ANY_CASE) - set(CATEGORY)

_TEXT_PATTERNS: list[tuple[str, re.Pattern]] = []
for _name, _cat, _w, _aliases in SKILLS:
    pats = list(_CASE_SENSITIVE.get(_name, []))
    if _name in _ANY_CASE:
        _TEXT_PATTERNS.append((_name, re.compile("|".join(_pattern(a) for a in _ANY_CASE[_name]), re.IGNORECASE)))
    if _name not in _CASE_SENSITIVE:
        ci = [a for a in [_name.lower(), *_aliases] if a not in _SKIP_ALIASES and len(a) >= 3 or a in {"c#", "c++", "dbt"}]
        if ci:
            _TEXT_PATTERNS.append((_name, re.compile("|".join(_pattern(a) for a in ci), re.IGNORECASE)))
    if pats:
        _TEXT_PATTERNS.append((_name, re.compile("|".join(pats))))


def skills_from_text(text: str) -> set[str]:
    """Find canonical skills in free text (a resume or a job description).

    Words that are also ordinary English or single letters ("R", "Go", "excel at", "AI", "BI") only count in
    unambiguous forms, so "I excel at teamwork" or "Go-to-market" add nothing.
    """
    return set(skills_in_order(text))


def skills_in_order(text: str) -> list[str]:
    """Like skills_from_text, ordered by where each skill is first mentioned (earlier usually means more central)."""
    if not text:
        return []
    text = re.sub(r"<[^>]+>", " ", text)
    first: dict[str, int] = {}
    for name, pat in _TEXT_PATTERNS:
        m = pat.search(text)
        if m and (name not in first or m.start() < first[name]):
            first[name] = m.start()
    return sorted(first, key=lambda n: (first[n], n))


# Holding a specific skill covers the broad tag that recruiters use for it: someone who knows Machine learning meets a
# posting's "Artificial intelligence" tag, and PySpark covers "Spark". Only clear umbrella terms are listed.
IMPLIES = {
    "Machine learning": ["Artificial intelligence"], "Deep learning": ["Artificial intelligence"],
    "Generative AI": ["Artificial intelligence"], "NLP": ["Artificial intelligence"],
    "Computer vision": ["Artificial intelligence"],
    "PySpark": ["Spark"], "Pandas": ["Python"], "NumPy": ["Python"], "scikit-learn": ["Python", "Machine learning"],
    "TensorFlow": ["Deep learning"], "PyTorch": ["Deep learning"],
    "Power BI": ["Data visualization", "Business intelligence"], "Tableau": ["Data visualization", "Business intelligence"],
    "Qlik": ["Data visualization", "Business intelligence"], "Looker": ["Data visualization"],
    "MySQL": ["SQL"], "PostgreSQL": ["SQL"], "SQL Server": ["SQL"], "PL/SQL": ["SQL"],
}
assert all(k in CATEGORY and all(v in CATEGORY for v in vs) for k, vs in IMPLIES.items())


def with_implied(have) -> set[str]:
    """Your skills plus every broad skill they imply (followed through chains: scikit-learn -> ML -> AI)."""
    out, todo = set(have), list(have)
    while todo:
        for t in IMPLIES.get(todo.pop(), ()):
            if t not in out:
                out.add(t)
                todo.append(t)
    return out
