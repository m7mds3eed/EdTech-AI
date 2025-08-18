import openai
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import re

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_question(subject, topic, difficulty="medium", previous_correct=None):
    """Generate a single question using OpenAI."""
    instruction = "Generate a question of medium difficulty."
    if previous_correct is not None:
        if previous_correct:
            instruction = "Increase difficulty slightly as the previous answer was correct."
        else:
            instruction = "Focus on reinforcing the nano-skill as the previous answer was incorrect."

    prompt = f"""
    You are an educational assistant. Generate a single multiple-choice question for the subject '{subject}' on the topic '{topic}'.
    Difficulty: {difficulty}.
    {instruction}
    Format the response as JSON with fields: question (string), options (list of 4 strings), answer (string).
    Example:
    {{
        "question": "What is a scalar quantity?",
        "options": ["Has magnitude only", "Has direction only", "Has both magnitude and direction", "None of the above"],
        "answer": "Has magnitude only"
    }}
    """
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an educational assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        # Clean response (remove markdown code blocks)
        content = response.choices[0].message.content.strip()
        content = re.sub(r'^```json\n|\n```$', '', content)  # Remove ```json and ```
        return json.loads(content)
    except (json.JSONDecodeError, Exception) as e:
        return {"question": f"Error generating question: {str(e)}", "options": [], "answer": ""}

def generate_question_batch(subject, topic, difficulty="medium", previous_correct=None, batch_size=10):
    """Generate a batch of questions using OpenAI."""
    instruction = "Generate a question of medium difficulty."
    if previous_correct is not None:
        if previous_correct:
            instruction = "Increase difficulty slightly as the previous answer was correct."
        else:
            instruction = "Focus on reinforcing the nano-skill as the previous answer was incorrect."

    prompt = f"""
    You are an educational assistant. Generate {batch_size} multiple-choice questions for the subject '{subject}' on the topic '{topic}'.
    Difficulty: {difficulty}.
    {instruction}
    Format the response as a JSON list, each with fields: question (string), options (list of 4 strings), answer (string).
    Example:
    [
        {{
            "question": "What is a scalar quantity?",
            "options": ["Has magnitude only", "Has direction only", "Has both magnitude and direction", "None of the above"],
            "answer": "Has magnitude only"
        }}
    ]
    """
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an educational assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        # Clean response (remove markdown code blocks)
        content = response.choices[0].message.content.strip()
        content = re.sub(r'^```json\n|\n```$', '', content)
        questions = json.loads(content)
        if not isinstance(questions, list):
            raise ValueError("Expected a JSON list of questions")
        return questions
    except (json.JSONDecodeError, Exception) as e:
        return [{"question": f"Error generating question: {str(e)}", "options": [], "answer": ""}] * batch_size

def generate_explanation(question, student_answer, correct_answer):
    """Generate explanation for incorrect answer using OpenAI."""
    if not all([question, student_answer, correct_answer]):
        return "Invalid input provided."
    
    prompt = f"""
    You are an educational assistant. Provide a concise explanation for why the student's answer is incorrect and suggest a next step.
    Question: {question}
    Student's answer: {student_answer}
    Correct answer: {correct_answer}
    """
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an educational assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating explanation: {str(e)}"

def generate_hint(question, options, answer, nano_topic):
    """Generate a helpful hint for a question without giving away the answer."""
    prompt = f"""
    You are an educational assistant helping IGCSE Mathematics students. Generate a helpful hint for this question without revealing the answer directly.
    
    Nano-topic: {nano_topic}
    Question: {question}
    Options: {', '.join(options) if options else 'Short answer question'}
    
    The hint should:
    1. Guide the student's thinking process
    2. Remind them of relevant concepts or formulas
    3. Suggest a problem-solving approach
    4. NOT reveal the answer directly
    
    Keep the hint concise (2-3 sentences max).
    """
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an educational assistant specializing in IGCSE Mathematics."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating hint: {str(e)}"

def generate_mini_lesson(nano_topic, question, correct_answer):
    """Generate a mini-lesson for the nano-topic based on the current question."""
    prompt = f"""
    You are an educational assistant for IGCSE Mathematics students. Create a brief mini-lesson on the nano-topic '{nano_topic}'.
    
    Context question: {question}
    Correct answer: {correct_answer}
    
    The mini-lesson should include:
    1. Core concept explanation (2-3 sentences)
    2. Key formula or rule if applicable
    3. A simple worked example
    4. Common mistakes to avoid
    
    Keep it concise but comprehensive (under 200 words). Use clear formatting with bullet points where appropriate.
    """
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an educational assistant specializing in IGCSE Mathematics."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating lesson: {str(e)}"

def generate_parent_report(strengths, weaknesses, points, badge):
    """Generate a weekly parent report using OpenAI."""
    weaknesses_text = ", ".join([f"{w['question']} (Explanation: {w['explanation']})" for w in weaknesses])
    prompt = f"""
    Generate a concise weekly report for a parent based on the following student quiz results:
    Strengths: {', '.join(strengths)}
    Weaknesses: {weaknesses_text}
    Points: {points}
    Badge: {badge or 'None'}
    Provide specific topics and actionable next steps in English.
    """
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an educational assistant generating parent reports."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating report: {str(e)}"
    
def generate_actionable_steps(nano_topic, p_learned):
    """Generate actionable steps for parents to help improve a student's nano-topic."""
    prompt = f"""
    You are an educational assistant. Generate 2-3 actionable steps for parents to help a grade 10-12 student improve in the IGCSE Mathematics nano-topic '{nano_topic}' (current mastery: {p_learned*100:.1f}%).
    Focus on simple, home-based activities that reinforce the concept without requiring advanced tools.
    Example for 'Factoring Quadratics':
    - Practice factoring with household items: e.g., split 12 candies into two groups to represent factors of 12.
    - Watch a 5-minute YouTube video on factoring trinomials and discuss one example together.
    - Solve 3 simple factoring problems (e.g., x^2 + 5x + 6) on paper with parental guidance.
    """
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an educational assistant generating actionable steps."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating actionable steps: {str(e)}"