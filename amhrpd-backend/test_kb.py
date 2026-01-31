from app.audio.knowledge_base import get_answer

test_queries = [
    "Who is the principal?",
    "What is the principal contact number?",
    "Where is the principal room?",
    "What is the full name of BCA?",
    "How long is the BCA course?",
    "What are the fees for BCA 1st semester?",
    "What are the fees for BCA 4th semester?",
    "Tell me about the Computer Science department",
    "Where is the Mathematics department?",
    "Where is the admission counter?",
    "Where is the ID card counter?",
    "Tell me about all the counters"
]

print("--- Knowledge Base Test ---")
for q in test_queries:
    ans = get_answer(q)
    print(f"Q: {q}")
    print(f"A: {ans}")
    print("-" * 20)
