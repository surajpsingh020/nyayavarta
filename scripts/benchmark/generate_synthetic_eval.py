import os
import json
import random

PROCESSED_DIR = "data/processed/aws_sc"
EVAL_DIR = "evaluation"
random.seed(42)

def generate_queries():
    files = [f for f in os.listdir(PROCESSED_DIR) if f.endswith('.json')]
    random.shuffle(files)
    
    queries = []
    gold_mapping = []
    
    query_id = 1
    for file in files:
        if query_id > 25:
            break
            
        with open(os.path.join(PROCESSED_DIR, file), "r", encoding="utf-8") as f:
            doc = json.load(f)
            
        text = doc.get("full_text", "")
        if not text:
            continue
            
        # Try to find a sentence with "Section" or "Act" or "Constitution"
        sentences = text.split(". ")
        chosen_sentence = None
        for s in sentences:
            if "Section" in s or "Act" in s or "Constitution" in s or "appeal" in s.lower():
                # Avoid too short or too long sentences
                if 50 < len(s) < 200:
                    chosen_sentence = s.replace("\n", " ").strip()
                    break
                    
        if not chosen_sentence:
            # Fallback
            words = text.split()
            if len(words) > 100:
                chosen_sentence = " ".join(words[50:70])
            else:
                continue
                
        # Clean up
        query_text = chosen_sentence + "?" if not chosen_sentence.endswith("?") else chosen_sentence
        
        q_obj = {
            "query_id": f"Q{query_id:03d}",
            "query_text": query_text,
            "legal_domain": "General"
        }
        queries.append(q_obj)
        
        g_obj = {
            "query_id": f"Q{query_id:03d}",
            "relevant_document_ids": [doc["document_id"]],
            "relevance_grades": {doc["document_id"]: 1}
        }
        gold_mapping.append(g_obj)
        
        query_id += 1

    with open(os.path.join(EVAL_DIR, "queries", "queries.json"), "w", encoding="utf-8") as f:
        json.dump(queries, f, indent=4)
        
    with open(os.path.join(EVAL_DIR, "gold", "gold.json"), "w", encoding="utf-8") as f:
        json.dump(gold_mapping, f, indent=4)
        
    print(f"Generated {len(queries)} queries.")

if __name__ == "__main__":
    generate_queries()
