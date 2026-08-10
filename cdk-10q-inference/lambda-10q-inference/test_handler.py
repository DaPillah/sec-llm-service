from handler import http_handler
import json


def api_event(payload):
    return {"body": json.dumps(payload)}


# --- Case 1: invalid request (missing fields) — should short-circuit before any AWS calls ---
print("=== Test 1: missing fields ===")
bad_event_1 = api_event({"ticker": "AAPL", "year": 2026})
print(http_handler(bad_event_1, None))
print()

# --- Case 2: invalid request (bad period value) ---
print("=== Test 2: invalid period ===")
bad_event_2 = api_event({
    "question": "What was total net sales?",
    "ticker": "AAPL",
    "year": 2026,
    "period": "Q9"
})
print(http_handler(bad_event_2, None))
print()

# --- Case 3: invalid request (lowercase ticker) ---
print("=== Test 3: lowercase ticker ===")
bad_event_3 = api_event({
    "question": "What was total net sales?",
    "ticker": "aapl",
    "year": 2026,
    "period": "Q2"
})
print(http_handler(bad_event_3, None))
print()

# --- Case 4: valid request — full pipeline, real Bedrock call ---
print("=== Test 4: valid request (full pipeline) ===")
good_event = api_event({
    "question": "What was Apple's total net sales for the quarter?",
    "ticker": "AAPL",
    "year": 2026,
    "period": "Q2"
})
result = http_handler(good_event, None)
print(result)