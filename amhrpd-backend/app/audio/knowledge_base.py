import json
import os
import difflib
import re

# Path to the data file
DATA_FILE = os.path.join("..", "docs", "RESPONCEDATAFILES", "data.json")

# In-memory cache of the data
_knowledge_data = None

def load_knowledge():
    global _knowledge_data
    try:
        # Get absolute path to the project root (amhrpd)
        # current file: amhrpd/amhrpd-backend/app/audio/knowledge_base.py
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
        data_path = os.path.join(project_root, "docs", "RESPONCEDATAFILES", "data.json")
        
        if os.path.exists(data_path):
            with open(data_path, "r") as f:
                _knowledge_data = json.load(f)
                return _knowledge_data
        else:
            print(f"Data file not found at: {data_path}")
        return None
    except Exception as e:
        print(f"Error loading knowledge base: {e}")
        return None

def get_answer(query: str) -> str | None:
    data = _knowledge_data or load_knowledge()
    if not data:
        return None

    query = query.lower()
    intent = data.get("intent", {})

    # 1. Principal queries
    if "principal" in query:
        p = intent.get("principal", {})
        if "name" in query or "who" in query:
            return f"The principal is {p.get('name')}. You can find him in room {p.get('room')}."
        if "contact" in query or "phone" in query:
            return f"The principal's contact number is {p.get('contact')}."
        if "room" in query or "where" in query:
            return f"The principal's room is number {p.get('room')}."
        return f"The principal is {p.get('name')}. His contact is {p.get('contact')} and he is in room {p.get('room')}."

    # 2. Course/Fees queries
    if "bca" in query or "course" in query or "fee" in query:
        bca = intent.get("courses", {}).get("bca", {})
        if "fee" in query:
            fees = bca.get("fees", {}).get("semester", {})
            if "1st" in query or "first" in query:
                return f"The fees for BCA 1st semester is {fees.get('1st semester')}."
            if "2nd" in query or "second" in query:
                return f"The fees for BCA 2nd semester is {fees.get('2nd semester')}."
            if "3rd" in query or "third" in query:
                return f"The fees for BCA 3rd semester is {fees.get('3rd semester')}."
            if "4th" in query or "fourth" in query:
                return f"The fees for BCA 4th semester is {fees.get('4th semester')}."
            if "5th" in query or "fifth" in query:
                return f"The fees for BCA 5th semester is {fees.get('5th semester')}."
            if "6th" in query or "sixth" in query:
                return f"The fees for BCA 6th semester is {fees.get('6th semester')}."
            
            # General fees summary
            return "The BCA fees are approximately 30,000 per semester. For example, 1st semester is 30,000 and 4th is 30,150."
        
        if "duration" in query or "long" in query:
            return f"The BCA course duration is {bca.get('duration')}."
        
        if "full name" in query or "what is bca" in query:
            return f"BCA stands for {bca.get('fullname')}."

    # 3. Department queries
    if "department" in query or "head" in query or "science" in query or "math" in query:
        dept = intent.get("department", {})
        if "computer" in query or "science" in query:
            cs = dept.get("Computer Science", {})
            return f"The Computer Science department is headed by {cs.get('head')} and is located in the {cs.get('blockname')}."
        if "math" in query:
            mt = dept.get("Mathematics", {})
            return f"The Mathematics department is headed by {mt.get('head')} and is located in the {mt.get('blockname')}."

    # 4. Counter queries
    if "counter" in query or "where" in query:
        counters = intent.get("counter", {})
        if "admission" in query:
            return f"The admission counter is {counters.get('admission')}."
        if "fee" in query:
            return f"The fees counter is {counters.get('fees')}."
        if "inquiry" in query:
            return f"The inquiry counter is {counters.get('inquiry')}."
        if "id card" in query or "card" in query:
            return f"The ID card counter is {counters.get('id card')}."
        
        # List all counters if generic
        if "counter" in query:
            all_c = ", ".join([f"{k}: {v}" for k, v in counters.items()])
            return f"The counters are: {all_c}."

    return None
