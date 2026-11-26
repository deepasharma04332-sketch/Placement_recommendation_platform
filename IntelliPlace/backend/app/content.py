"""Static content: skill dictionary, resume keywords, mock test questions, interview questions."""

SKILL_DICTIONARY = [
    "Python", "Java", "JavaScript", "TypeScript", "C++", "SQL", "MySQL", "PostgreSQL", "MongoDB",
    "NoSQL", "Pandas", "NumPy", "Matplotlib", "Seaborn", "Excel", "Power BI", "Tableau",
    "Data Visualization", "Data Analysis", "Statistics", "Machine Learning", "Deep Learning",
    "Scikit-learn", "TensorFlow", "PyTorch", "NLP", "Computer Vision", "HTML", "CSS", "React",
    "Node.js", "Express", "Flask", "Django", "FastAPI", "REST API", "Git", "GitHub", "Docker",
    "Kubernetes", "AWS", "Azure", "Linux", "Cloud Computing", "Selenium", "Data Structures",
    "Algorithms", "Operating Systems", "DBMS", "Computer Networks", "Object Oriented Programming",
    "Communication", "Problem Solving", "Teamwork",
]

ACTION_VERBS = [
    "developed", "built", "designed", "implemented", "led", "managed", "improved", "created",
    "analyzed", "optimized", "automated", "launched", "reduced", "increased", "achieved",
    "delivered", "collaborated", "researched", "deployed", "integrated", "tested", "coordinated",
    "trained", "published", "organized",
]

# Each question: (question text, [4 options], index of correct option)
MOCK_TESTS = {
    "python": ("Python", [
        ("What is the output of print(type([]))?", ["<class 'list'>", "<class 'tuple'>", "<class 'dict'>", "<class 'set'>"], 0),
        ("Which keyword is used to define a function in Python?", ["func", "def", "define", "lambda"], 1),
        ("What does len('Hello') return?", ["4", "5", "6", "Error"], 1),
        ("Which data type is immutable?", ["list", "dict", "set", "tuple"], 3),
        ("What is the output of 2 ** 3?", ["6", "8", "9", "5"], 1),
        ("Which list method adds an item at the end?", ["append()", "add()", "insert_end()", "push()"], 0),
        ("What is the main use of the 'with' statement?", ["Loops", "Resource management, such as files", "Defining classes", "Importing modules"], 1),
        ("What is the output of bool(0)?", ["True", "False", "0", "None"], 1),
    ]),
    "sql": ("SQL", [
        ("Which clause filters rows after grouping?", ["WHERE", "HAVING", "GROUP BY", "ORDER BY"], 1),
        ("Which command removes all rows but keeps the table structure?", ["DROP", "DELETE", "TRUNCATE", "REMOVE"], 2),
        ("Which join returns all rows from both tables?", ["INNER JOIN", "LEFT JOIN", "FULL OUTER JOIN", "CROSS JOIN"], 2),
        ("Which function counts only non-NULL values in a column?", ["COUNT(column)", "SUM()", "AVG()", "MAX()"], 0),
        ("Which keyword removes duplicate rows from a result?", ["UNIQUE", "DISTINCT", "SINGLE", "DIFFERENT"], 1),
        ("Can a primary key contain NULL values?", ["Yes", "No", "Only in MySQL", "Only with indexes"], 1),
        ("Which statement changes the structure of an existing table?", ["MODIFY", "UPDATE", "ALTER", "CHANGE"], 2),
        ("What is the default order of ORDER BY?", ["Descending", "Ascending", "Random", "Alphabetical only"], 1),
    ]),
    "aptitude": ("Aptitude", [
        ("If 20% of x is 40, what is x?", ["100", "200", "80", "150"], 1),
        ("What comes next: 2, 4, 8, 16, ?", ["24", "32", "20", "18"], 1),
        ("A train travels 120 km in 2 hours. What is its speed?", ["50 km/h", "60 km/h", "80 km/h", "240 km/h"], 1),
        ("Which is the odd one out?", ["3", "5", "9", "11"], 2),
        ("An item costs 80 and is sold for 100. What is the profit percentage?", ["20%", "25%", "80%", "125%"], 1),
        ("A is taller than B, and B is taller than C. Who is the shortest?", ["A", "B", "C", "Cannot say"], 2),
        ("What is the average of 10, 20 and 30?", ["15", "20", "25", "30"], 1),
        ("What is the simple interest on 1000 at 10% per year for 2 years?", ["100", "200", "300", "2000"], 1),
    ]),
}

# Each question: (question text, keywords a good answer should mention, short tip)
INTERVIEW_QUESTIONS = [
    ("Tell me about yourself.", ["education", "skill", "project", "interest", "goal"],
     "Cover your education, key skills, one project, and your goal."),
    ("What is the difference between a list and a tuple in Python?", ["mutable", "immutable", "tuple", "list"],
     "Mention that lists are mutable and tuples are immutable."),
    ("What is a primary key in a database?", ["unique", "null", "identify", "row"],
     "Explain that it uniquely identifies each row and cannot be NULL."),
    ("What is overfitting in machine learning?", ["training", "generalize", "noise", "test", "overfit"],
     "Explain that the model memorizes training data and performs poorly on new data."),
    ("Describe a project you are proud of.", ["built", "problem", "result", "team", "technology"],
     "Use the problem, what you built, the technology, and the result."),
    ("Why should we hire you?", ["skill", "learn", "contribute", "team", "value"],
     "Connect your skills to the role and mention how you will contribute."),
    ("What is a REST API?", ["http", "endpoint", "stateless", "resource", "get", "post"],
     "Mention HTTP methods, resources, endpoints, and statelessness."),
    ("Where do you see yourself in five years?", ["learn", "grow", "role", "skill", "lead"],
     "Show growth: skills you want to build and the role you aim for."),
]
