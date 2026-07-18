"""
Chart generation. Renders matplotlib figures to base64 PNGs so they can be
dropped straight into an <img src="data:image/png;base64,..."> tag - no
extra static files to manage per-request.
"""

import io
import base64
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# palette matched to the app's design tokens (see static/style.css)
PALETTE = ["#2E7D5B", "#C99A3B", "#5B6572", "#C0392B", "#3D5A80", "#8AA29E"]


def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150, transparent=True)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def salary_pie_chart(fields: dict) -> str:
    """Pie chart of salary components (Basic, HRA, DA, etc.)."""
    labels = [k for k, v in fields.items() if k != "Net Pay" and v > 0]
    values = [fields[k] for k in labels]

    if not values:
        labels, values = ["No data extracted"], [1]

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(
        values, labels=labels, autopct="%1.1f%%", startangle=90,
        colors=PALETTE, textprops={"fontsize": 10},
    )
    ax.set_title("Salary Slip Breakdown", fontsize=13, fontweight="bold")
    return _fig_to_base64(fig)


def bank_pie_chart(credit_total: float, debit_total: float) -> str:
    """Pie chart of total credits vs total debits."""
    values = [credit_total, debit_total]
    labels = [f"Credits ({credit_total:,.0f})", f"Debits ({debit_total:,.0f})"]

    if credit_total == 0 and debit_total == 0:
        labels, values = ["No data extracted"], [1]

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.pie(
        values, labels=labels, autopct="%1.1f%%", startangle=90,
        colors=[PALETTE[0], PALETTE[3]], textprops={"fontsize": 10},
    )
    ax.set_title("Credit vs Debit", fontsize=13, fontweight="bold")
    return _fig_to_base64(fig)


def bank_bar_chart(monthly_totals: dict) -> str:
    """Bar chart of monthly credit/debit totals."""
    if not monthly_totals:
        months, credits, debits = ["No data"], [0], [0]
    else:
        months = list(monthly_totals.keys())
        credits = [monthly_totals[m]["credit"] for m in months]
        debits = [monthly_totals[m]["debit"] for m in months]

    x = range(len(months))
    width = 0.35

    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.bar([i - width / 2 for i in x], credits, width, label="Credit", color=PALETTE[0])
    ax.bar([i + width / 2 for i in x], debits, width, label="Debit", color=PALETTE[3])
    ax.set_xticks(list(x))
    ax.set_xticklabels(months, rotation=45, ha="right", fontsize=9)
    ax.set_ylabel("Amount")
    ax.set_title("Monthly Transaction Totals", fontsize=13, fontweight="bold")
    ax.legend()
    fig.tight_layout()
    return _fig_to_base64(fig)
