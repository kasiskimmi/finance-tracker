#!/usr/bin/env python3
"""
Personal Finance Tracker & Expense Analyzer
============================================
A feature-rich CLI app to track income/expenses, analyze spending,
set budgets, and generate reports — all stored in a local JSON file.
"""

import json
import os
import sys
from datetime import datetime, date
from collections import defaultdict
from typing import Optional

# ── Optional rich-output libs (gracefully degrade if missing) ──────────────
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False

# ── Constants ──────────────────────────────────────────────────────────────
DATA_FILE = "finance_data.json"
DATE_FMT  = "%Y-%m-%d"

EXPENSE_CATEGORIES = [
    "Food & Dining", "Transport", "Housing", "Utilities",
    "Healthcare", "Entertainment", "Shopping", "Education",
    "Travel", "Personal Care", "Savings", "Other",
]
INCOME_CATEGORIES = ["Salary", "Freelance", "Investment", "Gift", "Other"]


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def c(text: str, color: str = "WHITE", bold: bool = False) -> str:
    """Wrap text in ANSI colour codes (no-op if colorama absent)."""
    if not HAS_COLOR:
        return text
    colour_map = {
        "RED": Fore.RED, "GREEN": Fore.GREEN, "YELLOW": Fore.YELLOW,
        "CYAN": Fore.CYAN, "MAGENTA": Fore.MAGENTA, "WHITE": Fore.WHITE,
        "BLUE": Fore.BLUE,
    }
    prefix = colour_map.get(color.upper(), "") + (Style.BRIGHT if bold else "")
    return f"{prefix}{text}{Style.RESET_ALL}"


def hr(char: str = "─", width: int = 60) -> str:
    return char * width


def fmt_money(amount: float) -> str:
    """Format a float as a currency string."""
    color = "GREEN" if amount >= 0 else "RED"
    return c(f"₹{amount:,.2f}", color, bold=True)


def today_str() -> str:
    return date.today().strftime(DATE_FMT)


def ask(prompt: str, default: str = "") -> str:
    val = input(f"  {prompt} [{default}]: ").strip()
    return val if val else default


def ask_float(prompt: str, default: float = 0.0) -> float:
    while True:
        raw = ask(prompt, str(default))
        try:
            return float(raw)
        except ValueError:
            print(c("  ✗ Please enter a valid number.", "RED"))


def ask_int(prompt: str, lo: int, hi: int) -> int:
    while True:
        raw = input(f"  {prompt} ({lo}–{hi}): ").strip()
        try:
            v = int(raw)
            if lo <= v <= hi:
                return v
        except ValueError:
            pass
        print(c(f"  ✗ Enter a number between {lo} and {hi}.", "RED"))


def ask_date(prompt: str) -> str:
    while True:
        raw = ask(prompt, today_str())
        try:
            datetime.strptime(raw, DATE_FMT)
            return raw
        except ValueError:
            print(c("  ✗ Use YYYY-MM-DD format.", "RED"))


def pick_from(options: list, title: str) -> str:
    print(f"\n  {c(title, 'CYAN', bold=True)}")
    for i, opt in enumerate(options, 1):
        print(f"    {c(str(i), 'YELLOW')}. {opt}")
    idx = ask_int("Pick number", 1, len(options))
    return options[idx - 1]


# ══════════════════════════════════════════════════════════════════════════════
# DATA LAYER
# ══════════════════════════════════════════════════════════════════════════════

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"transactions": [], "budgets": {}, "currency": "INR"}


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def next_id(transactions: list) -> int:
    return max((t["id"] for t in transactions), default=0) + 1


# ══════════════════════════════════════════════════════════════════════════════
# TRANSACTIONS
# ══════════════════════════════════════════════════════════════════════════════

def add_transaction(data: dict, ttype: str) -> None:
    cats   = EXPENSE_CATEGORIES if ttype == "expense" else INCOME_CATEGORIES
    cat    = pick_from(cats, "Select category")
    amount = ask_float("Amount (₹)", 0.0)
    if amount <= 0:
        print(c("  ✗ Amount must be positive.", "RED"))
        return
    date_str = ask_date("Date (YYYY-MM-DD)")
    desc     = ask("Description", "—")
    tags_raw = ask("Tags (comma-separated, optional)", "")
    tags     = [t.strip() for t in tags_raw.split(",") if t.strip()]

    txn = {
        "id":          next_id(data["transactions"]),
        "type":        ttype,
        "category":    cat,
        "amount":      amount,
        "date":        date_str,
        "description": desc,
        "tags":        tags,
        "created_at":  datetime.now().isoformat(),
    }
    data["transactions"].append(txn)
    save_data(data)
    print(c(f"\n  ✓ {ttype.capitalize()} of {fmt_money(amount)} added (ID #{txn['id']}).", "GREEN"))


def list_transactions(data: dict, ttype: Optional[str] = None,
                      month: Optional[str] = None, category: Optional[str] = None) -> list:
    txns = data["transactions"]
    if ttype:
        txns = [t for t in txns if t["type"] == ttype]
    if month:
        txns = [t for t in txns if t["date"].startswith(month)]
    if category:
        txns = [t for t in txns if t["category"] == category]
    return sorted(txns, key=lambda x: x["date"], reverse=True)


def view_transactions(data: dict) -> None:
    print(f"\n  {c('Filter Options', 'CYAN', bold=True)}")
    ttype    = pick_from(["All", "expense", "income"], "Transaction type")
    ttype    = None if ttype == "All" else ttype
    month_in = ask("Filter by month (YYYY-MM) or leave blank", "")
    month    = month_in if month_in else None

    txns = list_transactions(data, ttype, month)
    if not txns:
        print(c("\n  No transactions found.", "YELLOW"))
        return

    print(f"\n  {hr()}")
    print(f"  {'ID':<5} {'Date':<12} {'Type':<10} {'Category':<18} {'Amount':>12}  {'Description'}")
    print(f"  {hr()}")
    for t in txns:
        sign  = -1 if t["type"] == "expense" else 1
        amt   = fmt_money(sign * t["amount"])
        ttype_label = c(t["type"].capitalize(), "RED" if t["type"] == "expense" else "GREEN")
        print(f"  {t['id']:<5} {t['date']:<12} {ttype_label:<20} {t['category']:<18} {amt:>20}  {t['description'][:30]}")
    print(f"  {hr()}")
    print(f"  Total rows: {c(str(len(txns)), 'CYAN', bold=True)}")


def delete_transaction(data: dict) -> None:
    tid = ask("Enter Transaction ID to delete", "")
    try:
        tid = int(tid)
    except ValueError:
        print(c("  ✗ Invalid ID.", "RED"))
        return
    before = len(data["transactions"])
    data["transactions"] = [t for t in data["transactions"] if t["id"] != tid]
    if len(data["transactions"]) < before:
        save_data(data)
        print(c(f"  ✓ Transaction #{tid} deleted.", "GREEN"))
    else:
        print(c(f"  ✗ Transaction #{tid} not found.", "RED"))


# ══════════════════════════════════════════════════════════════════════════════
# BUDGETS
# ══════════════════════════════════════════════════════════════════════════════

def set_budget(data: dict) -> None:
    cat    = pick_from(EXPENSE_CATEGORIES, "Category to budget")
    amount = ask_float("Monthly budget (₹)", 0.0)
    if amount <= 0:
        print(c("  ✗ Budget must be positive.", "RED"))
        return
    data["budgets"][cat] = amount
    save_data(data)
    print(c(f"  ✓ Budget for '{cat}' set to {fmt_money(amount)}/month.", "GREEN"))


def view_budgets(data: dict) -> None:
    budgets = data.get("budgets", {})
    if not budgets:
        print(c("\n  No budgets set yet.", "YELLOW"))
        return

    month = today_str()[:7]
    txns  = list_transactions(data, ttype="expense", month=month)
    spent = defaultdict(float)
    for t in txns:
        spent[t["category"]] += t["amount"]

    print(f"\n  {c('Budget Status — ' + month, 'CYAN', bold=True)}")
    print(f"  {hr()}")
    print(f"  {'Category':<22} {'Budget':>12} {'Spent':>12} {'Remaining':>12}  {'Usage'}")
    print(f"  {hr()}")
    for cat, budget in sorted(budgets.items()):
        s         = spent.get(cat, 0.0)
        remaining = budget - s
        pct       = (s / budget * 100) if budget > 0 else 0
        bar_fill  = int(pct / 5)
        bar       = "█" * bar_fill + "░" * (20 - bar_fill)
        bar_color = "GREEN" if pct < 75 else ("YELLOW" if pct < 100 else "RED")
        print(f"  {cat:<22} {fmt_money(budget):>20} {fmt_money(s):>20} "
              f"{fmt_money(remaining):>20}  {c(bar, bar_color)} {pct:.0f}%")
    print(f"  {hr()}")


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

def _bar(value: float, max_val: float, width: int = 30) -> str:
    if max_val == 0:
        return "░" * width
    filled = int((value / max_val) * width)
    return "█" * filled + "░" * (width - filled)


def monthly_summary(data: dict) -> None:
    month = ask("Month (YYYY-MM)", today_str()[:7])
    txns  = list_transactions(data, month=month)
    if not txns:
        print(c(f"\n  No data for {month}.", "YELLOW"))
        return

    income  = sum(t["amount"] for t in txns if t["type"] == "income")
    expense = sum(t["amount"] for t in txns if t["type"] == "expense")
    net     = income - expense
    savings_rate = (net / income * 100) if income > 0 else 0

    print(f"\n  {c('Monthly Summary — ' + month, 'CYAN', bold=True)}")
    print(f"  {hr()}")
    print(f"  {'Total Income':<20}: {fmt_money(income)}")
    print(f"  {'Total Expenses':<20}: {fmt_money(-expense)}")
    print(f"  {'Net Balance':<20}: {fmt_money(net)}")
    print(f"  {'Savings Rate':<20}: {c(f'{savings_rate:.1f}%', 'GREEN' if savings_rate >= 20 else 'YELLOW')}")
    print(f"  {hr()}")

    # Category breakdown (expenses)
    cat_totals: dict = defaultdict(float)
    for t in txns:
        if t["type"] == "expense":
            cat_totals[t["category"]] += t["amount"]

    if cat_totals:
        print(f"\n  {c('Expense Breakdown by Category', 'MAGENTA', bold=True)}")
        print(f"  {hr()}")
        max_val = max(cat_totals.values())
        for cat, total in sorted(cat_totals.items(), key=lambda x: -x[1]):
            pct = total / expense * 100 if expense > 0 else 0
            bar = _bar(total, max_val)
            print(f"  {cat:<20} {c(bar, 'CYAN')} {fmt_money(total):>18}  ({pct:.1f}%)")
        print(f"  {hr()}")


def yearly_overview(data: dict) -> None:
    year = ask("Year (YYYY)", str(date.today().year))
    months_data: dict = {}
    for m in range(1, 13):
        month_str = f"{year}-{m:02d}"
        txns      = list_transactions(data, month=month_str)
        income    = sum(t["amount"] for t in txns if t["type"] == "income")
        expense   = sum(t["amount"] for t in txns if t["type"] == "expense")
        months_data[month_str] = (income, expense)

    print(f"\n  {c('Yearly Overview — ' + year, 'CYAN', bold=True)}")
    print(f"  {hr()}")
    print(f"  {'Month':<12} {'Income':>12} {'Expenses':>12} {'Net':>12}  Chart")
    print(f"  {hr()}")

    all_vals = [max(inc, exp) for inc, exp in months_data.values()]
    max_val  = max(all_vals) if all_vals else 1

    total_income = total_expense = 0.0
    for month_str, (income, expense) in months_data.items():
        net          = income - expense
        total_income  += income
        total_expense += expense
        net_color    = "GREEN" if net >= 0 else "RED"
        bar_i        = _bar(income,  max_val, 12)
        bar_e        = _bar(expense, max_val, 12)
        print(f"  {month_str:<12} {fmt_money(income):>20} {fmt_money(-expense):>20} "
              f"{c(f'₹{net:,.0f}', net_color):>20}  "
              f"{c(bar_i, 'GREEN')}{c(bar_e, 'RED')}")

    print(f"  {hr()}")
    print(f"  {'TOTAL':<12} {fmt_money(total_income):>20} {fmt_money(-total_expense):>20} "
          f"{fmt_money(total_income - total_expense):>20}")


def top_expenses(data: dict) -> None:
    n    = ask_int("Show top N expenses", 1, 50)
    txns = sorted(
        [t for t in data["transactions"] if t["type"] == "expense"],
        key=lambda x: -x["amount"]
    )[:n]

    if not txns:
        print(c("\n  No expenses found.", "YELLOW"))
        return

    print(f"\n  {c(f'Top {n} Expenses', 'CYAN', bold=True)}")
    print(f"  {hr()}")
    print(f"  {'#':<4} {'Date':<12} {'Category':<18} {'Amount':>12}  {'Description'}")
    print(f"  {hr()}")
    for i, t in enumerate(txns, 1):
        print(f"  {i:<4} {t['date']:<12} {t['category']:<18} {fmt_money(-t['amount']):>20}  {t['description'][:35]}")
    print(f"  {hr()}")


def spending_trend(data: dict) -> None:
    """Show month-over-month spending change."""
    months: set = {t["date"][:7] for t in data["transactions"]}
    if len(months) < 2:
        print(c("\n  Need at least 2 months of data.", "YELLOW"))
        return

    sorted_months = sorted(months)
    print(f"\n  {c('Spending Trend (MoM)', 'CYAN', bold=True)}")
    print(f"  {hr()}")
    prev_expense = None
    for month_str in sorted_months:
        txns    = list_transactions(data, ttype="expense", month=month_str)
        expense = sum(t["amount"] for t in txns)
        if prev_expense is not None and prev_expense > 0:
            change = (expense - prev_expense) / prev_expense * 100
            arrow  = c("▲", "RED") if change > 0 else c("▼", "GREEN")
            delta  = c(f"{abs(change):.1f}%", "RED" if change > 0 else "GREEN")
            print(f"  {month_str}  {fmt_money(-expense):>20}  {arrow} {delta}")
        else:
            print(f"  {month_str}  {fmt_money(-expense):>20}  {'(baseline)'}")
        prev_expense = expense
    print(f"  {hr()}")


def search_transactions(data: dict) -> None:
    keyword = ask("Search keyword (description/tag/category)", "").lower()
    results = [
        t for t in data["transactions"]
        if keyword in t["description"].lower()
        or keyword in t["category"].lower()
        or any(keyword in tag.lower() for tag in t.get("tags", []))
    ]
    if not results:
        print(c(f"\n  No transactions matching '{keyword}'.", "YELLOW"))
        return

    print(f"\n  {c(f'Search Results for \"{keyword}\"', 'CYAN', bold=True)} — {len(results)} found")
    print(f"  {hr()}")
    for t in sorted(results, key=lambda x: x["date"], reverse=True):
        sign = -1 if t["type"] == "expense" else 1
        print(f"  #{t['id']:<5} {t['date']}  {t['category']:<18} {fmt_money(sign * t['amount']):>18}  {t['description']}")
    print(f"  {hr()}")


def export_csv(data: dict) -> None:
    filename = ask("Export filename", "transactions_export.csv")
    if not filename.endswith(".csv"):
        filename += ".csv"
    with open(filename, "w") as f:
        f.write("id,type,category,amount,date,description,tags\n")
        for t in sorted(data["transactions"], key=lambda x: x["date"]):
            tags = "|".join(t.get("tags", []))
            f.write(f"{t['id']},{t['type']},{t['category']},{t['amount']},"
                    f"{t['date']},\"{t['description']}\",{tags}\n")
    print(c(f"\n  ✓ Exported {len(data['transactions'])} transactions to '{filename}'.", "GREEN"))


# ══════════════════════════════════════════════════════════════════════════════
# MENUS
# ══════════════════════════════════════════════════════════════════════════════

MENU = {
    "1": ("Add Expense",          lambda d: add_transaction(d, "expense")),
    "2": ("Add Income",           lambda d: add_transaction(d, "income")),
    "3": ("View Transactions",    view_transactions),
    "4": ("Delete Transaction",   delete_transaction),
    "5": ("Set Budget",           set_budget),
    "6": ("View Budget Status",   view_budgets),
    "7": ("Monthly Summary",      monthly_summary),
    "8": ("Yearly Overview",      yearly_overview),
    "9": ("Top Expenses",         top_expenses),
    "10": ("Spending Trend",      spending_trend),
    "11": ("Search Transactions", search_transactions),
    "12": ("Export to CSV",       export_csv),
    "0": ("Quit",                 None),
}


def print_banner() -> None:
    banner = r"""
  ┌─────────────────────────────────────────────────────────┐
  │   💰  Personal Finance Tracker & Expense Analyzer  💰   │
  └─────────────────────────────────────────────────────────┘"""
    print(c(banner, "CYAN", bold=True))


def print_menu() -> None:
    print(f"\n  {c('Main Menu', 'YELLOW', bold=True)}")
    print(f"  {hr('─', 46)}")
    for key, (label, _) in MENU.items():
        color = "RED" if key == "0" else "WHITE"
        print(f"    {c(key.rjust(2), 'CYAN', bold=True)}.  {c(label, color)}")
    print(f"  {hr('─', 46)}")


def quick_stats(data: dict) -> None:
    """Show a mini dashboard at startup."""
    month = today_str()[:7]
    txns  = list_transactions(data, month=month)
    income  = sum(t["amount"] for t in txns if t["type"] == "income")
    expense = sum(t["amount"] for t in txns if t["type"] == "expense")
    net     = income - expense
    total   = len(data["transactions"])

    print(f"\n  {c('Quick Stats — ' + month, 'MAGENTA', bold=True)}")
    print(f"  {hr('─', 46)}")
    print(f"  {'Income  '}: {fmt_money(income)}")
    print(f"  {'Expenses'}: {fmt_money(-expense)}")
    print(f"  {'Net     '}: {fmt_money(net)}")
    print(f"  {'Records '}: {c(str(total), 'CYAN')} total transactions")
    print(f"  {hr('─', 46)}")


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    data = load_data()
    print_banner()
    quick_stats(data)

    while True:
        print_menu()
        choice = input(c("  ➤ Enter choice: ", "YELLOW")).strip()

        if choice not in MENU:
            print(c("  ✗ Invalid choice. Try again.", "RED"))
            continue

        label, action = MENU[choice]
        if action is None:           # Quit
            print(c("\n  Goodbye! Keep tracking those finances. 👋\n", "CYAN", bold=True))
            sys.exit(0)

        print(f"\n  {c('── ' + label + ' ──', 'CYAN', bold=True)}")
        try:
            action(data)
        except KeyboardInterrupt:
            print(c("\n  (Cancelled)", "YELLOW"))


if __name__ == "__main__":
    main()
