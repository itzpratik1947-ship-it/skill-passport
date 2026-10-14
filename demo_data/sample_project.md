# Demo Expense Tracker

This synthetic project demonstrates a small Python program that stores expense records and summarizes totals.

```python
def total_expenses(expenses):
    return sum(item["amount"] for item in expenses)

expenses = [{"category": "food", "amount": 120.0}, {"category": "travel", "amount": 50.0}]
print(total_expenses(expenses))
```

## Validation
- Test the function with an empty list.
- Test the function with multiple expense records.
- Confirm amounts are numeric before calculation.

## Limitations
This is a tiny teaching example, not a production finance application. The sample is synthetic and must not be presented as independently verified work.
