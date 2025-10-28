import os
import requests
import json
from app.config import PPLX_API_KEY, LLM_MODEL

def analyze_answer_quality_simple(question, answer):
    """
    Simplified answer quality analysis based on answer characteristics
    """
    base_score = 20

    length_score = min(len(answer) / 5, 30) 

    quality_indicators = 0
    
    if any(word in answer.lower() for word in ['mg', 'g', 'calories', 'percentage', '%']):
        quality_indicators += 15
    if any(word in answer.lower() for word in ['contains', 'includes', 'made with', 'sourced from']):
        quality_indicators += 10
    if any(word in answer.lower() for word in ['certified', 'organic', 'pure', 'natural']):
        quality_indicators += 10
    if any(word in answer.lower() for word in ['yes', 'no', 'not']) and len(answer) > 20:
        quality_indicators += 5
    if len(answer) > 100:
        quality_indicators += 15
    
    total_score = base_score + length_score + quality_indicators
    return min(total_score, 80) 

def calculate_transparency_score(qa_history, current_score):
    """
    Simplified transparency score calculation
    """
    if not qa_history:
        return 0

    total_questions = len(qa_history)
    
    base_points = min(total_questions * 15, 60) 

    quality_points = 0
    for qa in qa_history[-6:]:
        if 'question' in qa and 'answer' in qa:
            quality = analyze_answer_quality_simple(qa['question'], qa['answer'])
            quality_points += quality * 0.4  
    
    total_score = base_points + min(quality_points, 40)
    
    comprehensive_bonus = 0
    if total_questions >= 4:
        comprehensive_bonus = 10
    if total_questions >= 8:
        comprehensive_bonus = 20
    
    final_score = min(total_score + comprehensive_bonus, 100)
    return int(final_score)

def should_generate_more_questions(qa_history, current_score):
    """
    Determine if we should generate more questions
    """
    if current_score >= 100:
        return False
    if len(qa_history) >= 12:  
        return False
    if current_score >= 80 and len(qa_history) >= 8:  
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
                    "Prioritize questions that reveal product composition, safety, sustainability, manufacturing. "
                    "Output ONLY valid JSON list of strings."
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
        cleaned = raw_text.strip().replace("```json", "").replace("```", "")

        try:
            questions = json.loads(cleaned)
            if isinstance(questions, list):
                questions = [q.strip() for q in questions if isinstance(q, str)]
                questions = [q[:100] + '?' if len(q) > 100 and not q.endswith('?') else q for q in questions]
            else:
                questions = []
        except Exception:
            questions = [
                line.strip(" ,\"")
                for line in cleaned.splitlines()
                if "?" in line
            ]

        return questions[:4]

    except Exception as e:
        print("Error calling Perplexity API:", e)
        return [
            "Ingredients used?",
            "Environmental impact?",
            "Manufacturing location?",
            "Safety certifications?"
        ]