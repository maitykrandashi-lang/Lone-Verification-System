import re

# Common payslip line items and the regex used to find "Label ... amount"
FIELD_PATTERNS = {
    "Basic Pay": r"basic\s*(pay|salary)?[:\-\s]*([\d,]+\.?\d*)",
    "HRA": r"h\.?r\.?a\.?[:\-\s]*([\d,]+\.?\d*)",
    "Allowances": r"(special|other|conveyance|medical)?\s*allowance[s]?[:\-\s]*([\d,]+\.?\d*)",
    "Bonus": r"bonus[:\-\s]*([\d,]+\.?\d*)",
    "Provident Fund": r"(p\.?f\.?|provident fund)[:\-\s]*([\d,]+\.?\d*)",
    "Tax (TDS)": r"(tds|tax|income tax)[:\-\s]*([\d,]+\.?\d*)",
    "Other Deductions": r"(deduction[s]?)[:\-\s]*([\d,]+\.?\d*)",
    "Net Pay": r"net\s*(pay|salary)[:\-\s]*([\d,]+\.?\d*)",
    "Gross Pay": r"gross\s*(pay|salary|earnings)[:\-\s]*([\d,]+\.?\d*)",
}


def _clean_amount(raw):
    try:
        return float(raw.replace(",", ""))
    except (ValueError, AttributeError):
        return 0.0


def parse_payslip(text):
    lowered = text.lower()
    found = {}

    for label, pattern in FIELD_PATTERNS.items():
        match = re.search(pattern, lowered, re.IGNORECASE)
        if match:
            amount_str = match.groups()[-1]
            amount = _clean_amount(amount_str)
            if amount > 0:
                found[label] = amount

    # Build pie chart: earnings components vs deductions vs net pay
    earnings_labels = ["Basic Pay", "HRA", "Allowances", "Bonus"]
    deduction_labels = ["Provident Fund", "Tax (TDS)", "Other Deductions"]

    pie_labels = []
    pie_values = []

    for label in earnings_labels + deduction_labels:
        if label in found:
            pie_labels.append(label)
            pie_values.append(found[label])

    if "Net Pay" in found and not pie_values:
        # Fallback: at least show net pay if nothing else was found
        pie_labels.append("Net Pay")
        pie_values.append(found["Net Pay"])

    return {
        "fields": found,
        "chart_data": {
            "labels": pie_labels,
            "values": pie_values,
        },
        "found_any": len(found) > 0,
    }
