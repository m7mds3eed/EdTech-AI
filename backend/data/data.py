import sqlite3
import json
from openai import OpenAI
from dotenv import load_dotenv
import os, sys
import re
import ast
import random
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.quiz.data import load_nano_topics
import time

# Load environment variables
load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Define the IGCSE curriculum structure (manually extracted and structured)
curriculum = {
    "subject": "mathematics",
    "topics": [
        {
            "name": "Numbers and the Number System",
            "description": "Concepts related to numerical operations and properties",
            "subtopics": [
                {
                    "name": "Integers",
                    "description": "Operations and properties of positive, negative, and zero integers",
                    "micro_topics": [
                        {
                            "name": "Integer Operations",
                            "description": "Performing arithmetic with integers",
                            "nano_topics": [
                                {"name": "Addition and Subtraction", "keywords": ["integers", "addition", "subtraction"]},
                                {"name": "Multiplication and Division", "keywords": ["integers", "multiplication", "division"]},
                                {"name": "Order of Operations", "keywords": ["integers", "brackets", "hierarchy"]},
                                {"name": "Prime Factors", "keywords": ["prime numbers", "factors", "decomposition"]},
                                {"name": "Common Factors and Multiples", "keywords": ["HCF", "LCM", "factors"]}
                            ]
                        },
                        {
                            "name": "Ordering and Place Value",
                            "description": "Understanding integer ordering and place value",
                            "nano_topics": [
                                {"name": "Ordering Integers", "keywords": ["integers", "ordering", "comparison"]},
                                {"name": "Place Value", "keywords": ["place value", "integers", "digits"]}
                            ]
                        },
                        {
                            "name": "Directed Numbers",
                            "description": "Using directed numbers in practical contexts",
                            "nano_topics": [
                                {"name": "Directed Numbers in Context", "keywords": ["directed numbers", "temperature", "practical"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Fractions",
                    "description": "Operations and properties of fractions",
                    "micro_topics": [
                        {
                            "name": "Fraction Operations",
                            "description": "Performing arithmetic with fractions",
                            "nano_topics": [
                                {"name": "Equivalent Fractions", "keywords": ["fractions", "equivalent", "simplifying"]},
                                {"name": "Adding and Subtracting Fractions", "keywords": ["fractions", "common denominators", "addition"]},
                                {"name": "Multiplying Fractions", "keywords": ["fractions", "multiplication", "mixed numbers"]},
                                {"name": "Dividing Fractions", "keywords": ["fractions", "division", "multiplicative inverse"]}
                            ]
                        },
                        {
                            "name": "Fraction Conversions",
                            "description": "Converting fractions to decimals or percentages",
                            "nano_topics": [
                                {"name": "Fraction to Decimal", "keywords": ["fractions", "decimal", "conversion"]},
                                {"name": "Fraction to Percentage", "keywords": ["fractions", "percentage", "conversion"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Decimals",
                    "description": "Operations and properties of decimal numbers",
                    "micro_topics": [
                        {
                            "name": "Decimal Operations",
                            "description": "Performing arithmetic with decimals",
                            "nano_topics": [
                                {"name": "Decimal Notation", "keywords": ["decimals", "notation", "place value"]},
                                {"name": "Ordering Decimals", "keywords": ["decimals", "ordering", "comparison"]}
                            ]
                        },
                        {
                            "name": "Decimal Conversions",
                            "description": "Converting decimals to fractions or percentages",
                            "nano_topics": [
                                {"name": "Decimal to Fraction", "keywords": ["decimals", "fraction", "conversion"]},
                                {"name": "Decimal to Percentage", "keywords": ["decimals", "percentage", "conversion"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Powers and Roots",
                    "description": "Operations with powers and roots",
                    "micro_topics": [
                        {
                            "name": "Power Operations",
                            "description": "Calculating squares, cubes, and index laws",
                            "nano_topics": [
                                {"name": "Square Numbers", "keywords": ["squares", "powers", "exponents"]},
                                {"name": "Cube Numbers", "keywords": ["cubes", "powers", "exponents"]},
                                {"name": "Index Laws", "keywords": ["index notation", "exponents", "laws"]}
                            ]
                        },
                        {
                            "name": "Prime Factorization",
                            "description": "Expressing numbers as products of prime factors",
                            "nano_topics": [
                                {"name": "Prime Factor Decomposition", "keywords": ["prime factors", "decomposition"]},
                                {"name": "HCF and LCM", "keywords": ["HCF", "LCM", "prime factors"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Set Language and Notation",
                    "description": "Understanding and using set theory",
                    "micro_topics": [
                        {
                            "name": "Set Operations",
                            "description": "Using set notation and operations",
                            "nano_topics": [
                                {"name": "Set Notation", "keywords": ["sets", "union", "intersection"]},
                                {"name": "Venn Diagrams", "keywords": ["sets", "Venn diagrams", "representation"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Percentages",
                    "description": "Operations with percentages",
                    "micro_topics": [
                        {
                            "name": "Percentage Operations",
                            "description": "Calculating and applying percentages",
                            "nano_topics": [
                                {"name": "Percentage of a Number", "keywords": ["percentage", "proportion", "calculation"]},
                                {"name": "Percentage Increase and Decrease", "keywords": ["percentage", "increase", "decrease"]},
                                {"name": "Reverse Percentages", "keywords": ["percentage", "reverse", "original value"]},
                                {"name": "Compound Interest", "keywords": ["percentage", "compound interest", "growth"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Ratio and Proportion",
                    "description": "Using ratios and proportions",
                    "micro_topics": [
                        {
                            "name": "Ratio Operations",
                            "description": "Applying ratio and proportion",
                            "nano_topics": [
                                {"name": "Simplifying Ratios", "keywords": ["ratio", "simplification", "proportion"]},
                                {"name": "Dividing in Ratios", "keywords": ["ratio", "division", "sharing"]},
                                {"name": "Direct Proportion", "keywords": ["proportion", "direct", "calculation"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Degree of Accuracy",
                    "description": "Rounding and estimating numbers",
                    "micro_topics": [
                        {
                            "name": "Rounding and Estimation",
                            "description": "Rounding to significant figures or decimal places",
                            "nano_topics": [
                                {"name": "Rounding to Significant Figures", "keywords": ["rounding", "significant figures"]},
                                {"name": "Upper and Lower Bounds", "keywords": ["bounds", "accuracy", "estimation"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Standard Form",
                    "description": "Working with numbers in standard form",
                    "micro_topics": [
                        {
                            "name": "Standard Form Operations",
                            "description": "Calculating with a × 10^n",
                            "nano_topics": [
                                {"name": "Standard Form Conversion", "keywords": ["standard form", "scientific notation"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Applying Number",
                    "description": "Applying numbers in real-life contexts",
                    "micro_topics": [
                        {
                            "name": "Real-Life Calculations",
                            "description": "Using numbers in practical scenarios",
                            "nano_topics": [
                                {"name": "Unit Conversions", "keywords": ["units", "conversion", "metric"]},
                                {"name": "Money Calculations", "keywords": ["money", "currency", "calculation"]}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "Equations, Formulae and Identities",
            "description": "Manipulating and solving algebraic expressions",
            "subtopics": [
                {
                    "name": "Use of Symbols",
                    "description": "Using symbols in equations and expressions",
                    "micro_topics": [
                        {
                            "name": "Index Notation",
                            "description": "Using index notation for powers",
                            "nano_topics": [
                                {"name": "Positive Index Laws", "keywords": ["index notation", "positive powers"]},
                                {"name": "Negative Index Laws", "keywords": ["index notation", "negative powers"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Algebraic Manipulation",
                    "description": "Simplifying and expanding expressions",
                    "micro_topics": [
                        {
                            "name": "Expression Manipulation",
                            "description": "Manipulating algebraic expressions",
                            "nano_topics": [
                                {"name": "Collecting Like Terms", "keywords": ["like terms", "simplification"]},
                                {"name": "Expanding Brackets", "keywords": ["brackets", "expansion", "linear"]},
                                {"name": "Factoring Quadratics", "keywords": ["factoring", "quadratics", "trinomials"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Expressions and Formulae",
                    "description": "Working with algebraic expressions and formulae",
                    "micro_topics": [
                        {
                            "name": "Formula Operations",
                            "description": "Substituting and deriving formulae",
                            "nano_topics": [
                                {"name": "Substitution in Expressions", "keywords": ["substitution", "expressions"]},
                                {"name": "Deriving Formulae", "keywords": ["formulae", "derivation"]},
                                {"name": "Changing the Subject", "keywords": ["formulae", "rearrangement"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Linear Equations",
                    "description": "Solving linear equations",
                    "micro_topics": [
                        {
                            "name": "Solving Linear Equations",
                            "description": "Solving equations with one unknown",
                            "nano_topics": [
                                {"name": "One-Step Equations", "keywords": ["linear equation", "single variable"]},
                                {"name": "Two-Step Equations", "keywords": ["linear equation", "two operations"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Simultaneous Linear Equations",
                    "description": "Solving two equations with two unknowns",
                    "micro_topics": [
                        {
                            "name": "Simultaneous Equations",
                            "description": "Solving simultaneous linear equations",
                            "nano_topics": [
                                {"name": "Substitution Method", "keywords": ["simultaneous equations", "substitution"]},
                                {"name": "Elimination Method", "keywords": ["simultaneous equations", "elimination"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Quadratic Equations",
                    "description": "Solving quadratic equations",
                    "micro_topics": [
                        {
                            "name": "Solving Quadratics",
                            "description": "Methods to solve quadratic equations",
                            "nano_topics": [
                                {"name": "Factoring Quadratics", "keywords": ["factoring", "quadratics"]},
                                {"name": "Quadratic Formula", "keywords": ["quadratic formula", "roots"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Inequalities",
                    "description": "Solving and representing inequalities",
                    "micro_topics": [
                        {
                            "name": "Linear Inequalities",
                            "description": "Solving inequalities in one variable",
                            "nano_topics": [
                                {"name": "Solving Linear Inequalities", "keywords": ["inequalities", "linear", "number line"]},
                                {"name": "Graphing Inequalities", "keywords": ["inequalities", "graphing", "Cartesian"]}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "Sequences, Functions and Graphs",
            "description": "Working with sequences and graphing functions",
            "subtopics": [
                {
                    "name": "Sequences",
                    "description": "Generating and analyzing sequences",
                    "micro_topics": [
                        {
                            "name": "Sequence Generation",
                            "description": "Generating sequence terms",
                            "nano_topics": [
                                {"name": "Term-to-Term Rules", "keywords": ["sequences", "term-to-term"]},
                                {"name": "Position-to-Term Rules", "keywords": ["sequences", "nth term"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Graphs",
                    "description": "Plotting and interpreting graphs",
                    "micro_topics": [
                        {
                            "name": "Graphing Functions",
                            "description": "Plotting linear and quadratic graphs",
                            "nano_topics": [
                                {"name": "Linear Graphs", "keywords": ["linear graphs", "gradient", "intercept"]},
                                {"name": "Quadratic Graphs", "keywords": ["quadratic graphs", "parabola"]}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "Geometry",
            "description": "Properties of shapes and spatial relationships",
            "subtopics": [
                {
                    "name": "Angles, Lines and Triangles",
                    "description": "Angle properties and triangle theorems",
                    "micro_topics": [
                        {
                            "name": "Angle Properties",
                            "description": "Properties of angles in lines and triangles",
                            "nano_topics": [
                                {"name": "Angle Types", "keywords": ["acute", "obtuse", "reflex"]},
                                {"name": "Triangle Angle Sum", "keywords": ["triangle", "angle sum"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Polygons",
                    "description": "Properties of polygons",
                    "micro_topics": [
                        {
                            "name": "Polygon Properties",
                            "description": "Angle sums and properties of polygons",
                            "nano_topics": [
                                {"name": "Quadrilateral Angle Sum", "keywords": ["quadrilateral", "angle sum"]},
                                {"name": "Regular Polygon Angles", "keywords": ["regular polygon", "interior angles"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Trigonometry and Pythagoras’ Theorem",
                    "description": "Applying trigonometry and Pythagoras’ theorem",
                    "micro_topics": [
                        {
                            "name": "Trigonometric Ratios",
                            "description": "Using sine, cosine, and tangent",
                            "nano_topics": [
                                {"name": "Sine Rule", "keywords": ["sine rule", "trigonometry"]},
                                {"name": "Cosine Rule", "keywords": ["cosine rule", "trigonometry"]},
                                {"name": "Pythagorean Theorem", "keywords": ["Pythagorean theorem", "right triangle"]}
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "name": "Statistics and Probability",
            "description": "Analyzing data and calculating probabilities",
            "subtopics": [
                {
                    "name": "Statistical Measures",
                    "description": "Calculating statistical measures",
                    "micro_topics": [
                        {
                            "name": "Measures of Central Tendency",
                            "description": "Calculating mean, median, mode",
                            "nano_topics": [
                                {"name": "Mean", "keywords": ["mean", "average"]},
                                {"name": "Median", "keywords": ["median", "central tendency"]}
                            ]
                        }
                    ]
                },
                {
                    "name": "Probability",
                    "description": "Calculating probabilities of events",
                    "micro_topics": [
                        {
                            "name": "Basic Probability",
                            "description": "Understanding probability concepts",
                            "nano_topics": [
                                {"name": "Independent Events", "keywords": ["probability", "independent events"]},
                                {"name": "Mutually Exclusive Events", "keywords": ["probability", "mutually exclusive"]}
                            ]
                        }
                    ]
                }
            ]
        }
    ]
}


def generate_questions(nano_topic, keywords, num_questions=3, difficulty=None, style=None, max_retries=2):
    """Generate sample questions for a nano-topic using OpenAI with specified or diverse difficulty levels and styles."""
    for attempt in range(max_retries + 1):
        if difficulty:
            prompt = rf"""
            You are an expert educational assistant specializing in IGCSE Mathematics (grades 5-12). Generate up to {num_questions} questions for the nano-topic '{nano_topic}' using keywords: {', '.join(keywords)}.
            Return a complete, valid JSON array with fields: id (unique integer), question (string), options (list of exactly 4 strings if mcq or true_false, empty list otherwise), answer (string), difficulty (string, set to '{difficulty}' for all questions), and style (string, set to '{style}' if specified, otherwise a mix of 'mcq', 'short_answer', 'exam_style', 'true_false').
            Ensure all questions are consistent with the specified difficulty level and style, appropriate for IGCSE standards, with clear, concise options. If fewer than {num_questions} questions can be generated, return a complete JSON array with the maximum possible. Example for mcq:
            [
                {{
                    "id": 1,
                    "question": "Solve x + 5 = 10",
                    "options": ["x=5", "x=10", "x=15", "x=0"],
                    "answer": "x=5",
                    "difficulty": "{difficulty}",
                    "style": "mcq"
                }}
            ]
            Example for short_answer:
            [
                {{
                    "id": 1,
                    "question": "Solve x + 5 = 10",
                    "options": [],
                    "answer": "x=5",
                    "difficulty": "{difficulty}",
                    "style": "short_answer"
                }}
            ]
            If the request cannot be fulfilled or JSON is invalid, return {{"error": "Invalid response or unable to fulfill request"}}.
            """
        else:
            prompt = rf"""
            You are an expert educational assistant specializing in IGCSE Mathematics (grades 5-12). Generate up to {num_questions} questions for the nano-topic '{nano_topic}' using keywords: {', '.join(keywords)}.
            Return a complete, valid JSON array with fields: id (unique integer), question (string), options (list of exactly 4 strings if mcq or true_false, empty list otherwise), answer (string), difficulty (string, one of 'beginner', 'intermediate', 'advanced'), and style (string, one of 'mcq', 'short_answer', 'exam_style', 'true_false').
            Ensure a diverse mix of 'beginner', 'intermediate', and 'advanced' difficulties, and a mix of styles (40% mcq, 30% short_answer, 20% exam_style, 10% true_false), appropriate for IGCSE standards, with clear, concise options. If fewer than {num_questions} questions can be generated, return a complete JSON array with the maximum possible. Example for mcq:
            [
                {{
                    "id": 1,
                    "question": "What is 2 + 3?",
                    "options": ["5", "6", "4", "7"],
                    "answer": "5",
                    "difficulty": "beginner",
                    "style": "mcq"
                }},
                {{
                    "id": 2,
                    "question": "Solve 2x + 3 = 7",
                    "options": [],
                    "answer": "x=2",
                    "difficulty": "intermediate",
                    "style": "short_answer"
                }}
            ]
            If the request cannot be fulfilled or JSON is invalid, return {{"error": "Invalid response or unable to fulfill request"}}.
            """
        try:
            response = openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert educational assistant with deep knowledge of IGCSE Mathematics curriculum."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500
            )
            content = response.choices[0].message.content.strip()
            print(f"Raw response for {nano_topic}: {content}")  # Debug raw output
            content = re.sub(r'^```json\n|\n```$', '', content)  # Strip markdown
            content = content.encode().decode('unicode_escape').encode('utf-8').decode('utf-8')  # Handle invalid escape sequences

            try:
                questions = json.loads(content)
                if isinstance(questions, dict) and questions.get("error"):
                    print(f"OpenAI returned error for {nano_topic}: {questions['error']}")
                    return []
                elif isinstance(questions, list):
                    for q in questions:
                        if not all(k in q for k in ["id", "question", "options", "answer", "difficulty", "style"]):
                            raise ValueError("Invalid question format")
                    if difficulty and any(q["difficulty"] != difficulty for q in questions):
                        print(f"Warning: Some questions for {nano_topic} do not match specified difficulty {difficulty}")
                    elif not difficulty and len(questions) > 1:
                        unique_difficulties = set(q["difficulty"] for q in questions)
                        if len(unique_difficulties) < min(3, len(questions)):
                            print(f"Warning: Limited diversity in difficulties for {nano_topic}: {unique_difficulties}")
                    if style and any(q["style"] != style for q in questions):
                        print(f"Warning: Some questions for {nano_topic} do not match specified style {style}")
                    elif not style and len(questions) > 1:
                        unique_styles = set(q["style"] for q in questions)
                        expected_styles = {'mcq', 'short_answer', 'exam_style', 'true_false'}
                        if not all(s in expected_styles for s in unique_styles) or len(unique_styles) < min(4, len(questions)):
                            print(f"Warning: Limited diversity in styles for {nano_topic}: {unique_styles}")
                    return questions
                else:
                    raise ValueError("Unexpected response format")
            except (json.JSONDecodeError, ValueError) as e:
                print(f"JSON parsing error for {nano_topic}: {str(e)} - Raw content: {content}")
                return []
        except Exception as e:
            print(f"Error generating questions for {nano_topic}: {str(e)}")
            return []
    print(f"Max retries exceeded for {nano_topic}. Returning empty list.")
    return []

def create_database():
    """Create SQLite database and tables."""
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS subtopics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (topic_id) REFERENCES topics(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS micro_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subtopic_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            FOREIGN KEY (subtopic_id) REFERENCES subtopics(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS nano_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            micro_topic_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            keywords TEXT,
            FOREIGN KEY (micro_topic_id) REFERENCES micro_topics(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nano_topic_id INTEGER,
            question TEXT NOT NULL,
            options TEXT NOT NULL,
            answer TEXT NOT NULL,
            difficulty TEXT,
            style TEXT, 
            FOREIGN KEY (nano_topic_id) REFERENCES nano_topics(id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_nano_topic_id ON questions(nano_topic_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_nano_name ON nano_topics(name)")
    conn.commit()
    conn.close()

def populate_database():
    """Populate SQLite database with curriculum data and generated questions with diverse styles."""
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    
    # Insert topics
    for topic in curriculum["topics"]:
        c.execute("INSERT INTO topics (subject, name, description) VALUES (?, ?, ?)",
                 (curriculum["subject"], topic["name"], topic["description"]))
        topic_id = c.lastrowid
        print(f"Inserted topic: {topic['name']} with ID: {topic_id}")
        
        # Insert subtopics
        for subtopic in topic["subtopics"]:
            c.execute("INSERT INTO subtopics (topic_id, name, description) VALUES (?, ?, ?)",
                     (topic_id, subtopic["name"], subtopic["description"]))
            subtopic_id = c.lastrowid
            print(f"Inserted subtopic: {subtopic['name']} with ID: {subtopic_id}")
            
            # Insert micro-topics
            for micro in subtopic["micro_topics"]:
                c.execute("INSERT INTO micro_topics (subtopic_id, name, description) VALUES (?, ?, ?)",
                         (subtopic_id, micro["name"], micro["description"]))
                micro_id = c.lastrowid
                print(f"Inserted micro-topic: {micro['name']} with ID: {micro_id}")
                
                # Insert nano-topics and questions
                for nano in micro["nano_topics"]:
                    c.execute("INSERT INTO nano_topics (micro_topic_id, name, keywords) VALUES (?, ?, ?)",
                             (micro_id, nano["name"], ",".join(nano["keywords"])))
                    nano_id = c.lastrowid
                    print(f"Inserted nano-topic: {nano['name']} with ID: {nano_id}")
                    
                    # Generate initial set with diverse styles
                    base_questions = generate_questions(nano["name"], nano["keywords"], num_questions=10)
                    for q in base_questions:
                        c.execute("INSERT INTO questions (nano_topic_id, question, options, answer, difficulty, style) VALUES (?, ?, ?, ?, ?, ?)",
                                 (nano_id, q["question"], json.dumps(q["options"]), q["answer"], q["difficulty"], q["style"]))
                    
                    # Add targeted styles for balance (40% mcq, 30% short_answer, 20% exam_style, 10% true_false)
                    total_questions = 10  # Initial set
                    styles = ['mcq', 'short_answer', 'exam_style', 'true_false']
                    weights = [0.4, 0.3, 0.2, 0.1]  # Target distribution
                    current_counts = {s: sum(1 for q in base_questions if q["style"] == s) for s in styles}
                    for style, weight in zip(styles, weights):
                        target_count = int((total_questions * weight) / sum(weights))
                        if current_counts[style] < target_count:
                            additional = generate_questions(nano["name"], nano["keywords"], num_questions=target_count - current_counts[style], style=style)
                            for q in additional:
                                c.execute("INSERT INTO questions (nano_topic_id, question, options, answer, difficulty, style) VALUES (?, ?, ?, ?, ?, ?)",
                                         (nano_id, q["question"], json.dumps(q["options"]), q["answer"], q["difficulty"], q["style"]))

    conn.commit()
    conn.close()

def add_questions_to_nano_skills(nano_skills=None, num_questions=6, difficulty=None, style=None):
    """Add questions to specified nano-skills or all if none specified."""
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    
    # Fetch existing nano-topics to determine which to add questions for
    c.execute("SELECT name FROM nano_topics")
    all_nano_topics = [row[0] for row in c.fetchall()]
    if not all_nano_topics:
        print("No nano-topics found in the database. Please run populate_database first.")
        return
    target_nano_topics = all_nano_topics if nano_skills is None else [n for n in nano_skills if n in all_nano_topics]
    
    for nano_topic in target_nano_topics:
        # Fetch topic and micro-topic for context
        c.execute("""
            SELECT t.name, m.name FROM nano_topics n
            JOIN micro_topics m ON n.micro_topic_id = m.id
            JOIN subtopics s ON m.subtopic_id = s.id
            JOIN topics t ON s.topic_id = t.id
            WHERE n.name = ?
        """, (nano_topic,))
        topic, micro_topic = c.fetchone()
        
        # Generate questions with specified or diverse difficulties and styles
        try:
            keywords = load_nano_topics(topic)[all_nano_topics.index(nano_topic)]["keywords"]
        except IndexError:
            print(f"Error: Nano-topic {nano_topic} not found in loaded nano-topics. Skipping.")
            continue
        questions = generate_questions(nano_topic, keywords, num_questions, difficulty, style)
        for q in questions:
            c.execute("""
                INSERT INTO questions (nano_topic_id, question, options, answer, difficulty, style)
                VALUES ((SELECT id FROM nano_topics WHERE name = ?), ?, ?, ?, ?, ?)
            """, (nano_topic, q["question"], json.dumps(q["options"]), q["answer"], q["difficulty"], q["style"]))

    conn.commit()
    conn.close()
    print(f"Added {num_questions} questions per specified nano-topic to the database.")


if __name__ == "__main__":
    create_database()
    populate_database()
    print("Database populated successfully.")