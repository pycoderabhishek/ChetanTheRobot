import json
import os
import difflib
import re

# Path to the new data file (relative to this file)
DATA_FILE = "npgc_information_pack.json"

# In-memory cache of the data
_knowledge_data = None

def load_knowledge():
    global _knowledge_data
    if _knowledge_data:
        return _knowledge_data

    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_path = os.path.join(current_dir, DATA_FILE)
        
        if os.path.exists(data_path):
            with open(data_path, "r", encoding="utf-8") as f:
                _knowledge_data = json.load(f)
                return _knowledge_data
        else:
            print(f"Data file not found at: {data_path}")
        return None
    except Exception as e:
        print(f"Error loading knowledge base: {e}")
        return None

def search_faculty(query, data):
    """Search for faculty members by name or department."""
    faculty_list = data.get("structured", {}).get("faculty_flat", [])
    query = query.lower()
    results = []

    # 1. Search by Name
    for f in faculty_list:
        if f.get("name", "").lower() in query:
            results.append(f)
    
    # 2. Search by Department (if no name match or specific department query)
    # Check if query contains a department name directly if "who", "teach", "faculty", "dept" is in query
    if not results and any(k in query for k in ["who", "teach", "faculty", "department", "dept"]):
        unique_depts = set(f.get("department", "") for f in faculty_list)
        for dept in unique_depts:
            if dept.lower() in query:
                # Found a department mentioned in query, get all faculty for it
                for f in faculty_list:
                    if f.get("department") == dept:
                        results.append(f)
                break # Stop after finding one matching department to avoid noise
                
    if results:
        # Format response
        responses = []
        for res in results[:3]: # Limit to top 3
            responses.append(f"{res['name']} ({res['designation']}, Dept of {res['department']})")
        return "Found faculty: " + "; ".join(responses)
    
    return None

def search_courses(query, data):
    """Search for course details."""
    catalog = data.get("structured", {}).get("academics_catalog", {}).get("courses_full_catalog", {}).get("courses", {})
    all_courses = []
    for cat in catalog.values(): # undergraduate, postgraduate, etc.
        all_courses.extend(cat)
        
    query = query.lower()
    
    # Normalize query for common abbreviations
    query = query.replace("bca", "b.c.a.").replace("bba", "b.b.a.").replace("bcom", "b.com").replace("bsc", "b.sc")

    target_course = None
    # Fuzzy match course name
    best_ratio = 0
    for course in all_courses:
        c_name = course.get("name", "").lower()
        # Direct check
        if c_name in query:
            target_course = course
            break
        # Similarity check
        ratio = difflib.SequenceMatcher(None, query, c_name).ratio()
        if ratio > 0.6 and ratio > best_ratio: # Threshold
            best_ratio = ratio
            target_course = course
            
    if target_course:
        info = f"{target_course['name']}: Duration {target_course['duration']}, Eligibility {target_course['entry_qualification']}."
        if "medium" in target_course:
            info += f" Medium: {', '.join(target_course['medium'])}."
        return info

    return None

def search_admissions(query, data):
    """Search admission related info."""
    adm = data.get("structured", {}).get("admissions", {})
    query = query.lower()
    
    if "date" in query or "schedule" in query:
        sched = adm.get("admission_schedule", {})
        last_dates = sched.get("online_application_last_dates", {})
        return f"Application Last Dates: UG - {last_dates.get('ug_courses')}, PG - {last_dates.get('pg_courses')}."
        
    if "eligibility" in query or "criteria" in query:
        # Try to find specific course eligibility if course name is in query
        criteria_list = adm.get("eligibility_criteria", [])
        for c in criteria_list:
            if c.get("course", "").lower() in query:
                return f"Eligibility for {c['course']}: {c['criteria']}"
        return "Please specify the course to check eligibility."

    return None

def search_institution(query, data):
    """General institution info."""
    inst = data.get("structured", {}).get("institution", {})
    query = query.lower()
    
    if "address" in query or "location" in query or "where" in query:
        return f"Address: {inst.get('location', {}).get('address')}."
        
    if "contact" in query or "phone" in query or "email" in query:
        contact = inst.get("location", {}) # In one place it's under location, in academics_catalog under contact. Let's use institution root.
        # Actually structure says institution -> location -> phone
        return f"Phone: {contact.get('phone')}, Email: {contact.get('email')}."
        
    if "vision" in query:
        return f"Vision: {data.get('structured', {}).get('vision_mission', {}).get('vision')}"
        
    if "mission" in query:
        return f"Mission: {data.get('structured', {}).get('vision_mission', {}).get('mission')}"

    return None

def get_answer(query: str) -> str | None:
    data = load_knowledge()
    if not data:
        return None

    query = query.lower()

    # Dispatcher
    if "faculty" in query or "professor" in query or "who is" in query or "teach" in query:
        res = search_faculty(query, data)
        if res: return res
        
    if "course" in query or "duration" in query or "degree" in query or "bca" in query or "b.sc" in query or "b.com" in query or "m.sc" in query:
        res = search_courses(query, data)
        if res: return res
        
    if "admission" in query or "apply" in query or "eligibility" in query or "date" in query:
        res = search_admissions(query, data)
        if res: return res
        
    if "college" in query or "address" in query or "contact" in query or "vision" in query or "mission" in query:
        res = search_institution(query, data)
        if res: return res

    # Fallback: check faculty again if it looks like a name (simple heuristic)
    # or just try all searches
    res = search_faculty(query, data)
    if res: return res
    
    return None
