import sqlite3
import json
import os
import time
from datetime import datetime
from openai import OpenAI

# Import configuration from supervisor_config.py
from .supervisor_config import DATABASE_PATH, OPENAI_API_KEY, VALIDATION_MODEL, BATCH_SIZE

def get_all_questions_for_validation():
    """Fetches all questions from the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT q.id, q.question, q.options, q.answer, q.difficulty, q.style, n.name as nano_topic
        FROM questions q
        JOIN nano_topics n ON q.nano_topic_id = n.id
    """)
    questions = c.fetchall()
    conn.close()
    return questions

# --- NEW: Function to fix legacy missing rejection reasons ---
def fix_missing_rejection_reasons():
    """Updates existing questions where is_approved=0 but rejection_reason is missing."""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE questions
        SET rejection_reason = 'Legacy rejection: reason not recorded. Re-validate for details.'
        WHERE is_approved = 0 AND (rejection_reason IS NULL OR rejection_reason = '')
    """)
    affected = c.rowcount
    conn.commit()
    conn.close()
    print(f"[{datetime.now().isoformat()}] Fixed {affected} questions with missing rejection reasons.")

def validate_question_batch_with_openai(question_batch, max_retries=3):
    """Uses the OpenAI API to validate a batch of questions, with retries for network errors."""
    client = OpenAI(api_key=OPENAI_API_KEY)

    # If batch is too large and we're getting errors, try smaller batches
    if len(question_batch) > 5:
        print(f"  -> Large batch of {len(question_batch)} questions, using careful validation mode...")

    formatted_questions = []
    for q in question_batch:
        question_id, question_text, options_json, correct_answer, difficulty, style, nano_topic = q
        try:
            options = json.loads(options_json) if options_json else []
        except (json.JSONDecodeError, TypeError):
            options = []

        formatted_questions.append({
            "question_id": question_id,
            "topic": nano_topic,
            "question": question_text,
            "style": style,
            "difficulty": difficulty,
            "options": options,
            "provided_answer": correct_answer
        })

    # --- IMPROVED: Much more careful and accurate validation prompt ---
    prompt = """
    You are a highly skilled IGCSE Mathematics examiner with expertise in mathematical problem-solving. Your primary responsibility is to accurately validate mathematical questions and their answers.

    **CRITICAL INSTRUCTIONS:**
    1. Be EXTREMELY careful with your mathematical calculations
    2. Double-check every step of your work
    3. Only reject questions with genuine mathematical errors
    4. When in doubt about a calculation, verify it multiple ways
    5. Accept equivalent answer formats (decimals, fractions, different units, etc.)

    Here are {} questions to validate:
    {}

    **VALIDATION PROCESS (Follow this exact sequence):**

    For EACH question:
    
    **STEP 1: UNDERSTAND THE QUESTION**
    - Read the question carefully, identifying what is being asked
    - Note any given values, formulas, or constraints
    - Identify the mathematical concept being tested
    
    **STEP 2: SOLVE INDEPENDENTLY** 
    - Work through the problem step-by-step using proper mathematical methods
    - Show your working clearly in your reasoning
    - Be extra careful with arithmetic, algebra, and unit conversions
    - If it's a complex problem, break it into smaller steps
    
    **STEP 3: COMPARE WITH PROVIDED ANSWER**
    - Check if your solution matches the provided answer
    - Consider equivalent forms: 0.5 = 1/2 = 50%, x=4 = 4, etc.
    - For word problems, check if units are correctly included/excluded
    - For equations, accept both "x=4" and "4" if x=4 is the solution
    
    **STEP 4: STRUCTURAL VALIDATION**
    - Multiple choice questions (style: "mcq") MUST have options listed
    - Question text should be clear and complete
    
    **STEP 5: DOUBLE-CHECK BEFORE DECIDING**
    - If you're about to reject, re-solve the problem using a different method
    - Ask: "Could there be a valid interpretation I'm missing?"
    - Ask: "Is my arithmetic definitely correct?"
    - Only reject if you're absolutely certain there's an error

    **COMMON MISTAKES TO AVOID:**
    - Don't reject for minor formatting differences (e.g., "4" vs "x = 4" when both are correct)
    - Don't reject decimal approximations of exact answers (e.g., 0.33 for 1/3)
    - Don't reject for missing/extra units if the numerical value is correct
    - Don't reject based on alternative solution methods
    - Don't make arithmetic errors in your own calculations
    
    **EXAMPLES OF EQUIVALENT ACCEPTABLE ANSWERS:**
    - Question asks for x in "2x = 8": Accept both "4" and "x = 4"
    - Question asks for area: Accept "12", "12 cm²", "12 square cm"  
    - Question asks for fraction: Accept "1/2", "0.5", "50%" if all are equivalent
    - Question asks for speed: Accept "5", "5 m/s" depending on context

    **RESPONSE FORMAT:**
    {{
      "results": [
        {{"question_id": 1, "is_valid": true, "rejection_reason": null}},
        {{"question_id": 2, "is_valid": false, "rejection_reason": "Mathematical error: Calculated area as 15 cm², but correct area is 12 cm² (length 4 × width 3 = 12)"}}
      ]
    }}
    
    Validate exactly {} questions and return results for all of them.
    """.format(len(formatted_questions), json.dumps(formatted_questions, indent=2), len(formatted_questions))

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=VALIDATION_MODEL,
                messages=[
                    {"role": "system", "content": "You are a highly skilled IGCSE Mathematics examiner. You must be extremely careful with mathematical calculations and only reject questions with genuine errors. Always double-check your arithmetic before making decisions. Respond only in the specified JSON format."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1  # Lower temperature for more consistent mathematical reasoning
            )

            validation_results = json.loads(response.choices[0].message.content)

            # Handle the expected response format
            if isinstance(validation_results, dict):
                # Check if it has the expected "results" key
                if "results" in validation_results and isinstance(validation_results["results"], list):
                    results_list = validation_results["results"]
                    # Verify we got results for all questions in the batch
                    if len(results_list) == len(question_batch):
                        return results_list
                    else:
                        print(f"  -! BATCH FAILED: Expected {len(question_batch)} results, got {len(results_list)}")
                        print("  -! RAW RESPONSE:", validation_results)
                        return [{"question_id": q[0], "is_valid": False, "rejection_reason": "Incomplete batch response from supervisor API."} for q in question_batch]
                
                # Handle case where API returns a single result instead of batch
                elif "question_id" in validation_results:
                    print("  -! WARNING: API returned single result instead of batch. This may indicate incomplete processing.")
                    print("  -! RAW RESPONSE:", validation_results)
                    # Try to find which question this result belongs to
                    question_id = validation_results.get("question_id")
                    matching_questions = [q for q in question_batch if q[0] == question_id]
                    if matching_questions:
                        # Return this single result and mark others as failed
                        results = []
                        for q in question_batch:
                            if q[0] == question_id:
                                results.append(validation_results)
                            else:
                                results.append({"question_id": q[0], "is_valid": False, "rejection_reason": "API failed to process this question in batch."})
                        return results
                    else:
                        return [{"question_id": q[0], "is_valid": False, "rejection_reason": "API returned result for wrong question ID."} for q in question_batch]
                
                # Check for other possible formats
                else:
                    for key in validation_results:
                        if isinstance(validation_results[key], list):
                            return validation_results[key]
                    print("  -! BATCH FAILED: API returned a JSON object but no valid results array found.")
                    print("  -! RAW RESPONSE:", validation_results)
                    return [{"question_id": q[0], "is_valid": False, "rejection_reason": "Supervisor API returned an invalid object format."} for q in question_batch]
            
            elif isinstance(validation_results, list):
                # Direct array response - check if it has the right number of results
                if len(validation_results) == len(question_batch):
                    return validation_results
                else:
                    print(f"  -! BATCH FAILED: Expected {len(question_batch)} results, got {len(validation_results)}")
                    print("  -! RAW RESPONSE:", validation_results)
                    return [{"question_id": q[0], "is_valid": False, "rejection_reason": "Incomplete batch response from supervisor API."} for q in question_batch]

            else:
                print("  -! BATCH FAILED: API returned an unexpected format.")
                print("  -! RAW RESPONSE:", validation_results)
                return [{"question_id": q[0], "is_valid": False, "rejection_reason": "Supervisor API returned a non-JSON format."} for q in question_batch]

        except Exception as e:
            print(f"  -! BATCH FAILED (Attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))
            else:
                return [{"question_id": q[0], "is_valid": False, "rejection_reason": f"API failed after {max_retries} attempts."} for q in question_batch]

def update_question_batch_status(validation_results):
    """Updates the status of a batch of questions in the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()

    update_data = []
    for result in validation_results:
        if result.get('question_id') is not None:
            is_valid = result.get('is_valid', False)
            rejection_reason = result.get('rejection_reason')

            # Enforce rejection reason if invalid
            if not is_valid and not rejection_reason:
                rejection_reason = "Rejected by supervisor for an unspecified critical error."
            # If valid, ensure reason is null
            if is_valid:
                rejection_reason = None
            
            update_data.append((1 if is_valid else 0, rejection_reason, result['question_id']))
    
    if not update_data:
        print("  -> No valid data to update in this batch.")
        return

    c.executemany("""
        UPDATE questions
        SET is_approved = ?, rejection_reason = ?
        WHERE id = ?
    """, update_data)
    
    conn.commit()
    conn.close()

def run_full_database_check(use_small_batches=False):
    """Main function to run the supervisor AI on the entire database in batches."""
    print(f"[{datetime.now().isoformat()}] Starting full supervisor AI check...")
    
    # --- NEW: Fix legacy issues first ---
    fix_missing_rejection_reasons()
    
    all_questions = get_all_questions_for_validation()
    
    if not all_questions:
        print("No questions found in the database to validate.")
        return
        
    total_questions = len(all_questions)
    
    # Use smaller batch size for more accurate validation if requested
    batch_size = 3 if use_small_batches else BATCH_SIZE
    print(f"Found {total_questions} questions to validate. Processing in batches of {batch_size}...")
    if use_small_batches:
        print("  -> Using small batches for more accurate validation.")
    
    for i in range(0, total_questions, batch_size):
        batch = all_questions[i:i + batch_size]
        start_num = i + 1
        end_num = min(i + batch_size, total_questions)
        
        print(f"  - Processing batch {start_num}-{end_num} of {total_questions}...")
        
        validation_results = validate_question_batch_with_openai(batch)
        
        if validation_results and isinstance(validation_results, list):
            update_question_batch_status(validation_results)
            print(f"  -> Batch processed and database updated.")
        else:
            print(f"  -> Skipping update for a failed or empty batch.")
            
    print(f"[{datetime.now().isoformat()}] Supervisor check completed.")

if __name__ == "__main__":
    # Add command line option for high-accuracy mode
    import sys
    use_small_batches = "--accurate" in sys.argv or "--small-batches" in sys.argv
    if use_small_batches:
        print("Running in high-accuracy mode with smaller batches...")
    run_full_database_check(use_small_batches)