from handler import core_handler

# --- Case 1: missing fields ---
print("=== Test 1: missing fields ===")
print(core_handler({"ticker": "AAPL", "year": 2026}, None))
print()

# --- Case 2: invalid period ---
print("=== Test 2: invalid period ===")
print(core_handler({
    "question": "What was total net sales?",
    "ticker": "AAPL",
    "year": 2026,
    "period": "Q9"
}, None))
print()

# --- Case 3: lowercase ticker ---
print("=== Test 3: lowercase ticker ===")
print(core_handler({
    "question": "What was total net sales?",
    "ticker": "aapl",
    "year": 2026,
    "period": "Q2"
}, None))
print()

# --- Case 4: valid request ---
print("=== Test 4: valid request (full pipeline) ===")
print(core_handler({
    "question": "What was Apple's total net sales for the quarter?",
    "ticker": "AAPL",
    "year": 2026,
    "period": "Q2"
}, None))

print("=== Test 5: broad/multi-part question ===")
print(core_handler({
    "question": "What were the main risk factors and any legal proceedings disclosed in this filing?",
    "ticker": "AAPL",
    "year": 2026,
    "period": "Q2"
}, None))

print("=== Test 6: unrelated multi-part question ===")
print(core_handler({
    "question": "What was cash and cash equivalents on the balance sheet, and what did the filing say about the company's AI investments?",
    "ticker": "AAPL",
    "year": 2026,
    "period": "Q2"
}, None))