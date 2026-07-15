import re
from collections import defaultdict

# --- Format A: date + amount tagged DR/CR on the same line -----------------
# 12/06/2026  ATM WITHDRAWAL   2,500.00 DR   45,000.00
DR_CR_PATTERN = re.compile(
    r"(?P<date>\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})"
    r".{0,60}?"
    r"(?P<amount>[\d,]+\.\d{2})\s*(?P<type>DR|CR|Dr|Cr|debit|credit)",
    re.IGNORECASE,
)
DR_CR_MONTH = re.compile(r"\d{1,2}[\/\-](?P<month>\d{1,2})[\/\-]\d{2,4}")

# --- Format B: "01 Jun 2026" style dates, running balance per row ----------
# Table columns get flattened into separate lines by OCR/PDF text extraction,
# so instead of trying to tell debit/credit apart from position, we track
# the running balance: if it goes up -> credit, if it goes down -> debit.
DATE_PATTERN = re.compile(r"\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}")
AMOUNT_PATTERN = re.compile(r"[\d,]+\.\d{2}")

OPENING_BALANCE_PATTERN = re.compile(r"Opening Balance\D{0,15}([\d,]+\.\d{2})", re.IGNORECASE)
CLOSING_BALANCE_PATTERN = re.compile(r"Closing Balance\D{0,15}([\d,]+\.\d{2})", re.IGNORECASE)
TOTAL_CREDIT_PATTERN = re.compile(r"Total Credits?\D{0,15}([\d,]+\.\d{2})", re.IGNORECASE)
TOTAL_DEBIT_PATTERN = re.compile(r"Total Debits?\D{0,15}([\d,]+\.\d{2})", re.IGNORECASE)

CATEGORY_SECTION_PATTERN = re.compile(
    r"Category-wise Expense Summary(.*?)(?:This is a computer|$)",
    re.IGNORECASE | re.DOTALL,
)
CATEGORY_ROW_PATTERN = re.compile(r"([A-Za-z][A-Za-z /&]{1,25}?)\s*\n\s*([\d,]+\.\d{2})")
IGNORE_CATEGORY_NAMES = {"category", "amount", "amount (rs.)", "amount(rs.)"}


def _clean_amount(raw):
    try:
        return float(raw.replace(",", ""))
    except (ValueError, AttributeError):
        return 0.0


def _search_amount(pattern, text):
    match = pattern.search(text)
    return _clean_amount(match.group(1)) if match else None


def _parse_dr_cr_format(text):
    transactions = []
    for match in DR_CR_PATTERN.finditer(text):
        amount = _clean_amount(match.group("amount"))
        txn_type = match.group("type").upper()[0]
        transactions.append({
            "date": match.group("date"),
            "description": "",
            "amount": amount,
            "type": "Credit" if txn_type == "C" else "Debit",
        })
    return transactions


def _parse_running_balance_format(text, opening_balance):
    date_matches = list(DATE_PATTERN.finditer(text))
    transactions = []
    running_balance = opening_balance

    for i, m in enumerate(date_matches):
        start = m.end()
        end = date_matches[i + 1].start() if i + 1 < len(date_matches) else len(text)
        block = text[start:end].split("Category-wise")[0]

        amounts = AMOUNT_PATTERN.findall(block)
        if len(amounts) < 2:
            continue

        amount = _clean_amount(amounts[-2])
        balance = _clean_amount(amounts[-1])

        if running_balance is not None:
            txn_type = "Credit" if balance >= running_balance else "Debit"
        else:
            txn_type = "Credit"
        running_balance = balance

        desc_match = re.match(r"^(.*?)(?=[\d,]+\.\d{2})", block, re.DOTALL)
        description = desc_match.group(1).strip().replace("\n", " ") if desc_match else ""
        description = re.sub(r"\s+", " ", description)[:40]

        transactions.append({
            "date": m.group(0),
            "description": description,
            "amount": amount,
            "type": txn_type,
        })

    return transactions


def _extract_category_summary(text):
    section_match = CATEGORY_SECTION_PATTERN.search(text)
    if not section_match:
        return {}

    section = section_match.group(1)
    categories = {}
    for name, amt in CATEGORY_ROW_PATTERN.findall(section):
        name = name.strip()
        if name.lower() in IGNORE_CATEGORY_NAMES or "total" in name.lower():
            continue
        categories[name] = _clean_amount(amt)
    return categories


def parse_bank_statement(text):
    opening_balance = _search_amount(OPENING_BALANCE_PATTERN, text)
    closing_balance = _search_amount(CLOSING_BALANCE_PATTERN, text)
    stated_total_credit = _search_amount(TOTAL_CREDIT_PATTERN, text)
    stated_total_debit = _search_amount(TOTAL_DEBIT_PATTERN, text)

    # Try the DR/CR inline format first, fall back to date + running balance
    transactions = _parse_dr_cr_format(text)
    if not transactions:
        # Only scan the actual transaction table, so dates that appear
        # elsewhere (statement date, period, etc.) aren't mistaken for rows
        table_match = re.search(
            r"Transaction History(.*?)(?:Category-wise Expense Summary|This is a computer|$)",
            text, re.IGNORECASE | re.DOTALL,
        )
        table_text = table_match.group(1) if table_match else text
        transactions = _parse_running_balance_format(table_text, opening_balance)

    categories = _extract_category_summary(text)

    total_credit = stated_total_credit if stated_total_credit is not None else \
        sum(t["amount"] for t in transactions if t["type"] == "Credit")
    total_debit = stated_total_debit if stated_total_debit is not None else \
        sum(t["amount"] for t in transactions if t["type"] == "Debit")

    if categories:
        # Best case: the statement itself gives a clean category breakdown
        chart_data = {
            "mode": "category",
            "title": "Spending by Category",
            "labels": list(categories.keys()),
            "debit": list(categories.values()),
            "credit": [0] * len(categories),
        }
    else:
        # Fallback: aggregate credit/debit by month from parsed transactions
        monthly = defaultdict(lambda: {"Credit": 0.0, "Debit": 0.0})
        for txn in transactions:
            month_match = DR_CR_MONTH.search(txn["date"])
            if month_match:
                month_key = f"Month {month_match.group('month')}"
            else:
                month_key = txn["date"].split()[1] if " " in txn["date"] else "Unknown"
            monthly[month_key][txn["type"]] += txn["amount"]

        labels = sorted(monthly.keys()) if monthly else ["Total"]
        chart_data = {
            "mode": "monthly",
            "title": "Credit vs Debit by Month",
            "labels": labels,
            "credit": [monthly[m]["Credit"] for m in labels] if monthly else [total_credit],
            "debit": [monthly[m]["Debit"] for m in labels] if monthly else [total_debit],
        }

    return {
        "transactions": transactions,
        "categories": categories,
        "total_credit": total_credit,
        "total_debit": total_debit,
        "closing_balance": closing_balance,
        "closing_estimate": closing_balance if closing_balance is not None else (total_credit - total_debit),
        "chart_data": chart_data,
        "found_any": len(transactions) > 0 or len(categories) > 0,
    }
