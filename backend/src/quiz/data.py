import sqlite3
import json

def load_nano_topics(subject, micro_topic=None):
    """Load nano-topics and their keywords from the SQLite database for a given subject and optional micro-topic."""
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    query = """
        SELECT n.name, n.keywords
        FROM nano_topics n
        JOIN micro_topics m ON n.micro_topic_id = m.id
        JOIN subtopics s ON m.subtopic_id = s.id
        JOIN topics t ON s.topic_id = t.id
        WHERE t.name = ? AND (m.name = ? OR ? IS NULL)
    """
    params = [subject, micro_topic, micro_topic]
    c.execute(query, params)
    nano_topics = [{"name": row[0], "keywords": row[1].split(",")} for row in c.fetchall()]
    conn.close()
    if not nano_topics:
        print(f"No nano-topics found for subject: {subject}, micro-topic: {micro_topic}")
    else:
        print(f"Loaded nano-topics for subject: {subject}, micro-topic: {micro_topic}: {nano_topics}")
    return nano_topics or []

def get_questions(nano_topic):
    """Retrieve APPROVED questions for a nano-topic from the SQLite database."""
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    # This query now filters for is_approved = 1
    c.execute("""
        SELECT question, options, answer, difficulty, style
        FROM questions
        WHERE nano_topic_id = (SELECT id FROM nano_topics WHERE name = ?)
        AND is_approved = 1
    """, (nano_topic,))
    questions = [{"question": row[0], "options": json.loads(row[1]), "answer": row[2], "difficulty": row[3], "style": row[4]} for row in c.fetchall()]
    conn.close()
    return questions

def get_unanswered_questions(user_id, nano_topic):
    """Get UNANSWERED and APPROVED questions for a given nano-topic and user."""
    conn = sqlite3.connect("data/math.db")
    c = conn.cursor()
    # This query now ALSO filters for is_approved = 1
    c.execute("""
        SELECT q.question, q.options, q.answer, q.difficulty, q.style
        FROM questions q
        LEFT JOIN student_results r ON r.question = q.question AND r.student_id = ?
        WHERE q.nano_topic_id = (SELECT id FROM nano_topics WHERE name = ?)
        AND q.is_approved = 1
        AND r.id IS NULL
    """, (user_id, nano_topic))
    questions = [{"question": row[0], "options": json.loads(row[1]), "answer": row[2], "difficulty": row[3], "style": row[4]} for row in c.fetchall()]
    conn.close()
    return questions