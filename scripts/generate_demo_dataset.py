"""Deterministic generator for synthetic 1,000-row customer demo dataset and companion ground truth."""

import json
from pathlib import Path
import random
import pandas as pd

# Set fixed seed for 100% deterministic reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda",
    "David", "Elizabeth", "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Nancy", "Daniel", "Lisa",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
]

STATES = ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]


def generate_demo_dataset(output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "demo_customers_1000.csv"
    ground_truth_path = output_dir / "demo_ground_truth.json"

    rows = []
    total_target_rows = 1000

    ground_truth = {
        "dataset_name": "demo_customers_1000.csv",
        "random_seed": RANDOM_SEED,
        "total_rows": total_target_rows,
        "categories": {
            "missing_values": {"expected_count": 0, "rows": [], "description": "Planted nulls, empty strings, and 'N/A' tokens"},
            "duplicates": {"expected_count": 0, "rows": [], "description": "Planted exact duplicate customer rows"},
            "standardization": {"expected_count": 0, "rows": [], "description": "Planted lowercase state codes and extra whitespace"},
            "type_validation": {"expected_count": 0, "rows": [], "description": "Planted currency string salaries and text booleans"},
            "outliers": {"expected_count": 0, "rows": [], "description": "Planted negative and extreme human ages"},
            "inconsistencies": {"expected_count": 0, "rows": [], "description": "Planted signup_date > renewal_date and arithmetic discrepancies"},
            "validation_rules": {"expected_count": 0, "rows": [], "description": "Planted syntactically invalid email addresses and ZIP codes"},
            "formatting": {"expected_count": 0, "rows": [], "description": "Planted invisible zero-width spaces and mojibake characters"},
        },
        "legitimate_preservations": {
            "zero_balances": {"count": 0, "rows": [], "description": "Legitimate $0.00 balances that must NOT be treated as missing"},
            "false_flags": {"count": 0, "rows": [], "description": "Legitimate False boolean flags that must NOT be treated as missing"},
        },
    }

    # Generate 1,000 base customer records
    for i in range(total_target_rows):
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last = LAST_NAMES[(i * 3) % len(LAST_NAMES)]
        full_name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{i}@example.com"
        state = STATES[i % len(STATES)]
        age = 22 + (i % 55)  # Ages 22 to 76
        income = f"${50000 + (i * 75):,}.00"  # Currency formatted strings
        
        # Legitimate 0.0 balance for every 20th row
        if i % 20 == 0:
            balance = 0.0
            ground_truth["legitimate_preservations"]["zero_balances"]["rows"].append(i)
        else:
            balance = round(100.0 + (i * 12.35), 2)

        # Legitimate False boolean flag for every 7th row
        if i % 7 == 0:
            is_active = False
            ground_truth["legitimate_preservations"]["false_flags"]["rows"].append(i)
        else:
            is_active = True

        phone = f"+1-555-{1000 + (i % 9000)}"
        signup_date = f"2023-{(i % 12) + 1:02d}-{(i % 25) + 1:02d}"
        renewal_date = f"2024-{(i % 12) + 1:02d}-{(i % 25) + 1:02d}"
        subtotal = round(50.0 + (i * 2.5), 2)
        tax = round(subtotal * 0.10, 2)
        total_spent = round(subtotal + tax, 2)
        zip_code = f"{94000 + (i % 900):05d}"

        rows.append({
            "customer_id": f"CUST-{1000 + i}",
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "state": state,
            "age": age,
            "annual_income": income,
            "account_balance": balance,
            "is_active": is_active,
            "signup_date": signup_date,
            "renewal_date": renewal_date,
            "subtotal": subtotal,
            "tax": tax,
            "total_spent": total_spent,
            "zip_code": zip_code,
        })

    # Plant 1. Missing Values: Plant 40 missing phones (mix of "N/A", "", None, "-")
    for idx in range(10, 50):
        val = random.choice(["N/A", "", None, "-", "NULL"])
        rows[idx]["phone"] = val
        ground_truth["categories"]["missing_values"]["rows"].append(idx)

    # Plant 2. Exact Duplicates: Overwrite rows 60..74 with exact copies of row 59 (15 duplicate rows)
    for idx in range(60, 75):
        rows[idx] = dict(rows[59])
        ground_truth["categories"]["duplicates"]["rows"].append(idx)

    # Plant 3. Standardization: Inconsistent lowercase state codes and leading/trailing whitespace
    for idx in range(80, 110):
        rows[idx]["state"] = rows[idx]["state"].lower()  # "ca", "ny"
        ground_truth["categories"]["standardization"]["rows"].append(idx)
    for idx in range(110, 125):
        rows[idx]["full_name"] = f"   {rows[idx]['full_name']}  "
        ground_truth["categories"]["standardization"]["rows"].append(idx)

    # Plant 4. Type Validation: String booleans ("yes", "no", "TRUE", "FALSE")
    for idx in range(130, 155):
        rows[idx]["is_active"] = "yes" if idx % 2 == 0 else "no"
        ground_truth["categories"]["type_validation"]["rows"].append(idx)

    # Plant 5. Outliers: Physically impossible ages (-5, -14, 142, 165)
    bad_ages = [-5, -14, -8, 142, 165, 180, -2, -19]
    for i, idx in enumerate(range(160, 168)):
        rows[idx]["age"] = bad_ages[i]
        ground_truth["categories"]["outliers"]["rows"].append(idx)

    # Plant 6. Inconsistencies: signup_date > renewal_date (reversed dates)
    for idx in range(180, 195):
        rows[idx]["signup_date"] = "2024-11-20"
        rows[idx]["renewal_date"] = "2023-02-10"
        ground_truth["categories"]["inconsistencies"]["rows"].append(idx)

    # Inconsistencies: Arithmetic mismatch (total_spent != subtotal + tax)
    for idx in range(195, 205):
        rows[idx]["total_spent"] = round(rows[idx]["subtotal"] + rows[idx]["tax"] + 250.0, 2)
        ground_truth["categories"]["inconsistencies"]["rows"].append(idx)

    # Plant 7. Validation Rules: Invalid email syntax
    bad_emails = [
        "john@@example..com", "missing_domain@", "spaces in email@domain.com",
        "no-at-sign.net", "@missing_user.org", "bad_dot@.com",
    ]
    for i, idx in enumerate(range(210, 240)):
        rows[idx]["email"] = bad_emails[i % len(bad_emails)]
        ground_truth["categories"]["validation_rules"]["rows"].append(idx)

    # Plant 8. Formatting: Zero-width spaces and mojibake in names
    for idx in range(250, 265):
        rows[idx]["full_name"] = f"{rows[idx]['full_name']}\u200b"
        ground_truth["categories"]["formatting"]["rows"].append(idx)
    for idx in range(265, 275):
        rows[idx]["full_name"] = f"RenÃ©e Dupont"
        ground_truth["categories"]["formatting"]["rows"].append(idx)

    # Finalize ground truth counts
    for cat, info in ground_truth["categories"].items():
        info["rows"] = sorted(list(set(info["rows"])))
        info["expected_count"] = len(info["rows"])

    ground_truth["legitimate_preservations"]["zero_balances"]["count"] = len(
        ground_truth["legitimate_preservations"]["zero_balances"]["rows"]
    )
    ground_truth["legitimate_preservations"]["false_flags"]["count"] = len(
        ground_truth["legitimate_preservations"]["false_flags"]["rows"]
    )

    # Write CSV
    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False)

    # Write Ground Truth JSON
    with open(ground_truth_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    return csv_path, ground_truth_path


if __name__ == "__main__":
    out_dir = Path("storage/demo")
    csv_p, gt_p = generate_demo_dataset(out_dir)
    print(f"Generated demo dataset: {csv_p}")
    print(f"Generated ground truth: {gt_p}")
