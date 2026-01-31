import json
import re

course=['bca','msc','bsc cs','bsc','bcom','ba','bba','bcom hons','bvoc','bvoc software development']
course.sort(key=len, reverse=True)
# ================== LOAD JSON ==================
with open("data.json", "r") as f:
    DB = json.load(f)["intent"]
    #print(DB.keys())

# ================== UTIL ==================
def normalize(text: str) -> str:
    return text.lower().strip()

# ================== INTENT DETECTION ==================
def detect_intent(text):
    text = normalize(text)

    if "fees" in text:
        return "fees"
    if "counter" in text:
        return "counter"
    if "principal" in text:
        return "principal"
    if "hod" in text or "head of" in text:
        return "department"
    if any(c in text for c in course):
        return "course_info"
    if "yourself" in text:
        return "about_bot"

    return None

# ================== COURSE EXTRACTION ==================
def extract_course(text):
    text = normalize(text)
    match = re.search(r"\b(" + "|".join(course) + r")\b", text)
    return match.group(1) if match else None
# ================== SEMESTER EXTRACTION ==================
def extract_semester(text):
    text = normalize(text)

    match = re.search(r"(semester|sem)*(\d+)", text)
    if match:
        n = int(match.group(2))
        suffix = "th" if 11 <= n <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix} semester"

    word_map = {
        "first": "1st semester",
        "second": "2nd semester",
        "third": "3rd semester",
        "fourth": "4th semester",
        "fifth": "5th semester",
        "sixth": "6th semester"
    }

    for word, sem in word_map.items():
        if word in text:
            return sem

    return None

# ================== COUNTER EXTRACTION ==================
def extract_counter(text):
    text = normalize(text)
    for key in DB["counter"].keys():
        if key.lower() in text:
            return DB["counter"][key]
    return None      
# ================== DEPARTMENT EXTRACTION ==================
def extract_department(text):
    text = normalize(text)

    for dept in DB["department"].keys():
        if dept.lower() in text:
            return dept

    return None
# ================== SENTENCE BUILDER ==================
def build_sentence(intent, data):
    if intent == "fees":
        return f"Fees of {data['course']} for {data['semester']} is {data['fees']}"

    if intent == "counter":
        return f"Counter number is {data['number']}"

    if intent == "department":
        return f"Head of {data['department']} department is {data['head']}"

    if intent == "principal":
        return f"Principal of the college is {data['name']}"

    if intent == "course_info":
        return f"{data['fullname']} ({data['abbrev']}) is a {data['duration']} program"

    if intent == "about_bot":
        return (
            "I am an intelligent college assistant robot. "
            "I can answer questions related to courses, fees, "
            "departments, counters and administration."
        )

    return "Sorry, I could not understand your question"

# ================== QUESTION HANDLER ==================
def handle_question(question):
    intent = detect_intent(question)

    if intent == "fees":
        cou = extract_course(question)
        semesters = extract_semester(question)
        print(cou, semesters)
        if not cou or not semesters:
            return "Please specify course and semester clearly"
        c= DB["courses"][cou]["fees"]["semester"][semesters]
        print(c)
        if not c:
            return "Fees data not available for this semester"

        return build_sentence("fees", {
            "course": cou,
            "semester": semesters,
            "fees": c
        })

    if intent == "counter":
        number = extract_counter(question)
        return build_sentence("counter", {"number": number})

    if intent == "department":
        dept = extract_department(question)
        if not dept:
            return "Please specify department name"

        return build_sentence("department", {
            "department": dept,
            "head": DB["department"][dept]["head"]
        })

    if intent == "principal":
        return build_sentence("principal", {
            "name": DB["principal"]["name"]
        })

    if intent == "course_info":
        c = extract_course(question)
        if not c:
            return "Course information not found"

        return build_sentence("course_info", {
            "fullname": c["fullname"],
            "abbrev": c["courseabbrev"],
            "duration": c["duration"]
        })

    if intent == "about_bot":
        return build_sentence("about_bot", {})

    return "Sorry, I could not understand your question"

# ================== AUDIO MODULE ==================
def audio_module(text):
    text = text.upper()

    if "HEY ESP" not in text:
        return None

    text = text.replace("HEY ESP", "").strip()

    if not text.startswith("NPGC"):
        return "Please start your question with NPGC"

    question = text.replace("NPGC", "").strip()
    return handle_question(question)

# ================== TEST ==================
if __name__ == "__main__":
    #print(audio_module("HEY ESP NPGC which counter for admission"))
    #print(audio_module("HEY ESP NPGC what is the fees of bca 2nd semester"))
    #print(audio_module("HEY ESP NPGC hod of computer science department"))
    #print(audio_module("HEY ESP NPGC principal name"))
    #print(audio_module("HEY ESP NPGC tell me about bca course"))
    print(audio_module("HEY ESP NPGC tell me about yourself"))
