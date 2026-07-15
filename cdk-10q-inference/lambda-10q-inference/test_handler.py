from handler import lambda_handler

# --- Case 1: invalid request (missing fields) — should short-circuit before any AWS calls ---
print("=== Test 1: missing fields ===")
bad_event_1 = {"ticker": "AAPL", "year": 2026}
print(lambda_handler(bad_event_1, None))
print()

# --- Case 2: invalid request (bad period value) ---
print("=== Test 2: invalid period ===")
bad_event_2 = {
    "question": "What was total net sales?",
    "ticker": "AAPL",
    "year": 2026,
    "period": "Q9"
}
print(lambda_handler(bad_event_2, None))
print()

# --- Case 3: invalid request (lowercase ticker) ---
print("=== Test 3: lowercase ticker ===")
bad_event_3 = {
    "question": "What was total net sales?",
    "ticker": "aapl",
    "year": 2026,
    "period": "Q2"
}
print(lambda_handler(bad_event_3, None))
print()

# --- Case 4: valid request — full pipeline, real Bedrock call ---
print("=== Test 4: valid request (full pipeline) ===")
good_event = {
    "question": "What was Apple's total net sales for the quarter?",
    "ticker": "AAPL",
    "year": 2026,
    "period": "Q2"
}
result = lambda_handler(good_event, None)
print(result)