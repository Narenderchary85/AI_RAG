import os
import re
import json
from flask import Flask, request, jsonify
from flask_cors import CORS 
from app.config import DATA_DIR,PPLX_API_KEY
import requests
from app.qua import call_perplexity_api,analyze_answer_quality_simple,calculate_transparency_score,should_generate_more_questions

ALLOWED_EXT = {"pdf", "txt", "md", "docx", "doc"}
os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)
CORS(app)

def clean_question_text(question):
    """
    Clean question text from API response
    """
    if not question:
        return ""
    
    cleaned = question.strip()
    cleaned = re.sub(r'^[\"\[\]?]+|[\"\[\]?]+$', '', cleaned) 
    cleaned = re.sub(r'[\"\[\]]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)

    if not cleaned.endswith('?'):
        cleaned += '?'
    
    return cleaned.strip()

def analyze_answer_quality_simple(question, answer):
    """
    Simplified answer quality analysis
    """
    if not answer or len(answer.strip()) == 0:
        return 0
    
    answer = answer.strip()
    base_score = 25 
    
    length_bonus = min(len(answer) / 3, 40) 
    
    quality_bonus = 0

    transparency_indicators = [
        ('mg', 5), ('g', 5), ('%', 10), ('calories', 5), 
        ('certified', 10), ('sustainable', 8), ('local', 5),
        ('recyclable', 8), ('compostable', 8), ('organic', 8),
        ('audit', 8), ('verified', 8), ('traceability', 10),
        ('carbon', 8), ('emissions', 8), ('renewable', 8)
    ]
    
    for indicator, points in transparency_indicators:
        if indicator.lower() in answer.lower():
            quality_bonus += points
    
    if len(answer) > 150:
        quality_bonus += 15
    elif len(answer) > 80:
        quality_bonus += 10
    elif len(answer) > 40:
        quality_bonus += 5
    
    total_score = base_score + length_bonus + min(quality_bonus, 35)
    return min(total_score, 100)

def calculate_transparency_score(qa_history):
    """
    Calculate transparency score based on answered questions
    """
    if not qa_history:
        return 0
    
    total_questions = len(qa_history)
    
    base_score = min(total_questions * 12, 50)  
    
    quality_scores = []
    for qa in qa_history:
        if 'question' in qa and 'answer' in qa:
            score = analyze_answer_quality_simple(qa['question'], qa['answer'])
            quality_scores.append(score)
    
    if quality_scores:
        avg_quality = sum(quality_scores) / len(quality_scores)
        quality_score = avg_quality * 0.5  
    else:
        quality_score = 0

    comprehensive_bonus = 0
    if total_questions >= 8:
        comprehensive_bonus = 15
    elif total_questions >= 5:
        comprehensive_bonus = 10
    elif total_questions >= 3:
        comprehensive_bonus = 5
    
    total_score = base_score + quality_score + comprehensive_bonus
    return min(int(total_score), 100)

def should_generate_more_questions(qa_history, current_score):
    """
    Determine if we should generate more questions
    """
    if current_score >= 85:
        return False
    if len(qa_history) >= 15:  
        return False
    if current_score >= 75 and len(qa_history) >= 10: 
        return False
    return True

def call_perplexity_api(prompt):
    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {PPLX_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Generate SHORT, CLEAR product transparency questions. "
                    "Each question 5-10 words max. Focus on one specific aspect. "
                    "Return ONLY a valid JSON array of strings with no additional text, no code blocks, no explanations. "
                    "Example: [\"Question one?\", \"Question two?\"]"
                ),
            },
            {"role": "user", "content": prompt},
        ],
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        raw_text = result["choices"][0]["message"]["content"]
        
        print(f"Raw API response: {raw_text}")
        
        cleaned = raw_text.strip()
        cleaned = re.sub(r'^```json\s*|\s*```$', '', cleaned) 
        cleaned = re.sub(r'^\[|\]$', '', cleaned) 
        
        try:
            if cleaned.startswith('[') and cleaned.endswith(']'):
                questions = json.loads(cleaned)
            else:
                questions = []
                lines = cleaned.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and '?' in line:
                        question = clean_question_text(line)
                        if question and len(question) > 10:
                            questions.append(question)
            
            if isinstance(questions, list):
                questions = [clean_question_text(q) for q in questions if isinstance(q, str) and len(clean_question_text(q)) > 10]
            else:
                questions = []
                
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            questions = []
            lines = cleaned.split('\n')
            for line in lines:
                line = line.strip()
                if line and '?' in line:
                    question = clean_question_text(line)
                    if question and len(question) > 10:
                        questions.append(question)

        questions = questions[:4]
        questions = [q for q in questions if q and len(q) > 10]
        
        print(f"Cleaned questions: {questions}")
        return questions

    except Exception as e:
        print(f"Error calling Perplexity API: {e}")
        return [
            "What are the main ingredients used?",
            "Are there any allergens present?",
            "Where are ingredients sourced from?",
            "What nutritional information is available?"
        ]

@app.route("/generate-questions", methods=["POST"])
def generate_questions():
    data = request.get_json()
    product_info = data.get("product_info", {})
    qa_history = data.get("qa_history", [])
    current_score = data.get("current_score", 0)
    
    print(f"Received request - History: {len(qa_history)} questions")
    
    new_score = calculate_transparency_score(qa_history)

    print(f"Calculated new score: {new_score}% based on {len(qa_history)} questions")
    
    if not should_generate_more_questions(qa_history, new_score):
        return jsonify({
            "questions": [],
            "transparency_score": new_score,
            "is_complete": True,
            "message": f"Assessment complete! Final transparency score: {new_score}%",
            "answered_questions": len(qa_history)
        })

    prompt = f"""
    Product: {product_info.get('name', 'Unknown')}
    Category: {product_info.get('category', 'Unknown')}
    Current transparency: {new_score}%
    Questions answered: {len(qa_history)}
    
    Recent topics: {[qa['question'] for qa in qa_history[-3:]] if qa_history else 'None'}
    
    Generate 2-4 SHORT questions about aspects not yet covered.
    Focus on: {"sustainability and ethics" if new_score > 60 else 
               "manufacturing and supply chain" if new_score > 30 else 
               "basic ingredients and safety"}
    
    Return ONLY a JSON array of question strings.
    """

    questions = call_perplexity_api(prompt)
    
    if new_score > 70:
        questions = questions[:2]
    elif new_score > 50:
        questions = questions[:3]
    
    response_data = {
        "questions": questions,
        "transparency_score": new_score,
        "is_complete": False,
        "answered_questions": len(qa_history)
    }
    
    if new_score >= 80:
        response_data["message"] = "Excellent transparency! Almost complete."
    elif new_score >= 60:
        response_data["message"] = "Good progress! Your product is becoming more transparent."
    elif new_score >= 30:
        response_data["message"] = "Building transparency profile. Keep going!"
    else:
        response_data["message"] = "Let's start building your product transparency."
    
    print(f"Sending response: {len(questions)} questions, score: {new_score}%")
    return jsonify(response_data)


PORT = int(os.environ.get("PORT", 5000))

if __name__ == "__main__":
     app.run(host="0.0.0.0", port=PORT)
