"""
Generate synthetic education data (EduPath Academy) via Databricks SQL API.
Runs locally — sends SQL statements to a Databricks SQL warehouse.

Usage:
    python run_sql_generation.py --profile DEFAULT --warehouse-id <id> --catalog <catalog> --schema <schema>
"""

import argparse
import json
import random
import subprocess
import sys
import time
from datetime import datetime, timedelta

random.seed(42)

FULL_SCHEMA = ""


def run_sql(statement: str, profile: str, warehouse_id: str) -> dict:
    """Execute a SQL statement via Databricks API."""
    payload = json.dumps({
        "warehouse_id": warehouse_id,
        "statement": statement,
        "wait_timeout": "60s",
    })
    result = subprocess.run(
        ["databricks", "api", "post", "/api/2.0/sql/statements", "--profile", profile, "--json", payload],
        capture_output=True, text=True,
    )
    try:
        data = json.loads(result.stdout)
        state = data.get("status", {}).get("state", "UNKNOWN")
        if state == "FAILED":
            err = data.get("status", {}).get("error", {}).get("message", "Unknown error")
            print(f"  SQL FAILED: {err}", file=sys.stderr)
            print(f"  Statement: {statement[:200]}...", file=sys.stderr)
        return data
    except json.JSONDecodeError:
        print(f"  Failed to parse response: {result.stdout[:500]}", file=sys.stderr)
        return {}


def run_sql_check(statement: str, profile: str, warehouse_id: str, label: str = ""):
    """Run SQL and print status."""
    data = run_sql(statement, profile, warehouse_id)
    state = data.get("status", {}).get("state", "UNKNOWN")
    if label:
        print(f"  {label}: {state}")
    return state


# ── Domain data (Education - EduPath Academy) ─────────────────────────────
FIRST_NAMES = [
    "James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda",
    "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica",
    "Thomas", "Sarah", "Charles", "Karen", "Christopher", "Lisa", "Daniel", "Nancy",
    "Matthew", "Betty", "Anthony", "Margaret", "Mark", "Sandra", "Donald", "Ashley",
    "Steven", "Kimberly", "Paul", "Emily", "Andrew", "Donna", "Joshua", "Michelle",
    "Kenneth", "Carol", "Kevin", "Amanda", "Brian", "Dorothy", "George", "Melissa",
    "Timothy", "Deborah", "Ronald", "Stephanie", "Edward", "Rebecca", "Jason", "Sharon",
    "Jeffrey", "Laura", "Ryan", "Cynthia", "Jacob", "Kathleen", "Gary", "Amy",
    "Nicholas", "Angela", "Eric", "Shirley", "Jonathan", "Anna", "Stephen", "Brenda",
    "Larry", "Pamela", "Justin", "Emma", "Scott", "Nicole", "Brandon", "Helen",
    "Benjamin", "Samantha", "Samuel", "Katherine", "Raymond", "Christine", "Gregory", "Debra",
    "Frank", "Rachel", "Alexander", "Carolyn", "Patrick", "Janet", "Jack", "Catherine",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts",
]

STREETS = [
    "Main St", "Oak Ave", "Elm St", "Park Blvd", "Cedar Ln", "Maple Dr", "Pine St",
    "Washington Ave", "Lake Rd", "Hill St", "Forest Dr", "River Rd", "Church St",
    "Spring St", "Meadow Ln", "Sunset Blvd", "Valley Rd", "Garden Way", "Market St",
    "Highland Ave",
]

CITIES_STATES = [
    ("Portland", "OR"), ("Seattle", "WA"), ("San Francisco", "CA"), ("Los Angeles", "CA"),
    ("Denver", "CO"), ("Austin", "TX"), ("Chicago", "IL"), ("Boston", "MA"),
    ("New York", "NY"), ("Atlanta", "GA"), ("Miami", "FL"), ("Phoenix", "AZ"),
    ("Minneapolis", "MN"), ("Nashville", "TN"), ("Salt Lake City", "UT"),
]

MEMBERSHIP_TIERS = ["Freshman", "Sophomore", "Junior", "Senior"]
LEARNING_STYLES = ["visual", "auditory", "reading", "kinesthetic", "hybrid", "self-paced", "collaborative", "none"]
FAVORITE_DEPARTMENTS = ["Computer Science", "Mathematics", "Business", "Engineering", "Arts", "Sciences", "Humanities", "Health Sciences", "Education"]
PAYMENT_METHODS = ["credit_card", "debit_card", "financial_aid", "scholarship", "wire_transfer"]

# Course catalog by department
PRODUCTS_BY_CATEGORY = {
    "Computer Science": [
        ("Introduction to Python", "Dr. Chen", 299.99, "3 credits"), ("Data Structures & Algorithms", "Dr. Kumar", 349.99, "4 credits"),
        ("Machine Learning Fundamentals", "Dr. Zhang", 399.99, "3 credits"), ("Web Development", "Prof. Miller", 279.99, "3 credits"),
        ("Database Systems", "Dr. Patel", 329.99, "3 credits"), ("Computer Networks", "Dr. Wilson", 349.99, "3 credits"),
        ("Operating Systems", "Dr. Brown", 349.99, "4 credits"), ("Software Engineering", "Prof. Davis", 329.99, "3 credits"),
        ("Cybersecurity Basics", "Dr. Thompson", 379.99, "3 credits"), ("Cloud Computing", "Dr. Garcia", 399.99, "3 credits"),
        ("Artificial Intelligence", "Dr. Lee", 449.99, "4 credits"), ("Mobile App Development", "Prof. Taylor", 299.99, "3 credits"),
        ("DevOps & CI/CD", "Dr. Martinez", 349.99, "3 credits"), ("Natural Language Processing", "Dr. Wang", 399.99, "3 credits"),
        ("Computer Vision", "Dr. Singh", 399.99, "3 credits"), ("Blockchain Technology", "Prof. Anderson", 349.99, "3 credits"),
    ],
    "Mathematics": [
        ("Calculus I", "Dr. Roberts", 249.99, "4 credits"), ("Linear Algebra", "Dr. Johnson", 279.99, "3 credits"),
        ("Statistics & Probability", "Dr. Williams", 279.99, "3 credits"), ("Discrete Mathematics", "Dr. Jones", 249.99, "3 credits"),
        ("Differential Equations", "Dr. Moore", 299.99, "3 credits"), ("Number Theory", "Prof. Clark", 279.99, "3 credits"),
        ("Abstract Algebra", "Dr. Hall", 299.99, "3 credits"), ("Real Analysis", "Dr. Young", 329.99, "4 credits"),
        ("Numerical Methods", "Prof. Wright", 299.99, "3 credits"), ("Combinatorics", "Dr. Allen", 279.99, "3 credits"),
        ("Calculus II", "Dr. Roberts", 249.99, "4 credits"), ("Calculus III", "Dr. Hill", 279.99, "4 credits"),
        ("Mathematical Modeling", "Prof. Green", 329.99, "3 credits"), ("Topology", "Dr. Baker", 349.99, "3 credits"),
    ],
    "Business": [
        ("Principles of Management", "Prof. Adams", 299.99, "3 credits"), ("Financial Accounting", "Dr. Nelson", 329.99, "3 credits"),
        ("Marketing Fundamentals", "Prof. Carter", 279.99, "3 credits"), ("Business Analytics", "Dr. Mitchell", 349.99, "3 credits"),
        ("Entrepreneurship", "Prof. Rivera", 299.99, "3 credits"), ("Corporate Finance", "Dr. Campbell", 349.99, "3 credits"),
        ("Operations Management", "Prof. Torres", 299.99, "3 credits"), ("Strategic Management", "Dr. Lewis", 329.99, "3 credits"),
        ("Business Ethics", "Prof. Robinson", 249.99, "3 credits"), ("International Business", "Dr. Walker", 299.99, "3 credits"),
        ("Supply Chain Management", "Prof. Perez", 329.99, "3 credits"), ("Human Resource Management", "Dr. Sanchez", 279.99, "3 credits"),
    ],
    "Engineering": [
        ("Statics & Dynamics", "Dr. Thompson", 349.99, "4 credits"), ("Thermodynamics", "Dr. White", 349.99, "3 credits"),
        ("Circuit Analysis", "Prof. Harris", 329.99, "3 credits"), ("Fluid Mechanics", "Dr. Martin", 349.99, "3 credits"),
        ("Materials Science", "Dr. Jackson", 299.99, "3 credits"), ("Control Systems", "Prof. Taylor", 349.99, "3 credits"),
        ("Engineering Design", "Dr. Anderson", 279.99, "4 credits"), ("Signal Processing", "Dr. Thomas", 379.99, "3 credits"),
        ("Robotics Fundamentals", "Prof. Garcia", 399.99, "3 credits"), ("Structural Analysis", "Dr. Martinez", 349.99, "4 credits"),
        ("Heat Transfer", "Dr. Robinson", 329.99, "3 credits"), ("Engineering Ethics", "Prof. Clark", 199.99, "2 credits"),
    ],
    "Arts & Humanities": [
        ("Introduction to Philosophy", "Dr. King", 229.99, "3 credits"), ("World History I", "Prof. Wright", 249.99, "3 credits"),
        ("Creative Writing", "Prof. Scott", 229.99, "3 credits"), ("Art History", "Dr. Flores", 249.99, "3 credits"),
        ("Music Theory", "Prof. Green", 249.99, "3 credits"), ("Introduction to Sociology", "Dr. Adams", 229.99, "3 credits"),
        ("Cultural Anthropology", "Dr. Nelson", 249.99, "3 credits"), ("Film Studies", "Prof. Baker", 229.99, "3 credits"),
        ("Ethics & Society", "Dr. Hall", 229.99, "3 credits"), ("Comparative Literature", "Prof. Young", 249.99, "3 credits"),
    ],
    "Natural Sciences": [
        ("General Chemistry I", "Dr. Nguyen", 299.99, "4 credits"), ("General Physics I", "Dr. Hill", 299.99, "4 credits"),
        ("Biology I", "Dr. Flores", 279.99, "4 credits"), ("Organic Chemistry", "Dr. Rivera", 349.99, "4 credits"),
        ("Environmental Science", "Prof. Torres", 249.99, "3 credits"), ("Astronomy", "Dr. Campbell", 229.99, "3 credits"),
        ("Genetics", "Dr. Mitchell", 299.99, "3 credits"), ("Biochemistry", "Dr. Carter", 349.99, "4 credits"),
        ("Ecology", "Prof. Sanchez", 249.99, "3 credits"), ("Geology", "Dr. Perez", 249.99, "3 credits"),
        ("General Physics II", "Dr. Hill", 299.99, "4 credits"), ("General Chemistry II", "Dr. Nguyen", 299.99, "4 credits"),
    ],
    "Health Sciences": [
        ("Human Anatomy", "Dr. Lewis", 329.99, "4 credits"), ("Physiology", "Dr. Walker", 329.99, "4 credits"),
        ("Nutrition Science", "Prof. Robinson", 249.99, "3 credits"), ("Public Health", "Dr. Allen", 279.99, "3 credits"),
        ("Pharmacology", "Dr. Young", 349.99, "3 credits"), ("Epidemiology", "Prof. King", 299.99, "3 credits"),
        ("Health Informatics", "Dr. Wright", 329.99, "3 credits"), ("Clinical Psychology", "Dr. Scott", 299.99, "3 credits"),
        ("Biostatistics", "Prof. Green", 299.99, "3 credits"), ("Healthcare Management", "Dr. Baker", 279.99, "3 credits"),
    ],
    "Education": [
        ("Educational Psychology", "Dr. Hall", 249.99, "3 credits"), ("Curriculum Design", "Prof. Adams", 279.99, "3 credits"),
        ("Classroom Management", "Dr. Nelson", 249.99, "3 credits"), ("Assessment & Evaluation", "Prof. Carter", 249.99, "3 credits"),
        ("Special Education", "Dr. Mitchell", 279.99, "3 credits"), ("Educational Technology", "Prof. Rivera", 299.99, "3 credits"),
        ("Early Childhood Education", "Dr. Torres", 249.99, "3 credits"), ("Adult Learning Theory", "Prof. Campbell", 249.99, "3 credits"),
        ("Multicultural Education", "Dr. Sanchez", 249.99, "3 credits"), ("Instructional Design", "Prof. Perez", 279.99, "3 credits"),
    ],
    "Communications": [
        ("Public Speaking", "Prof. Lewis", 229.99, "3 credits"), ("Mass Media & Society", "Dr. Walker", 249.99, "3 credits"),
        ("Digital Marketing", "Prof. Robinson", 299.99, "3 credits"), ("Journalism Fundamentals", "Dr. Allen", 249.99, "3 credits"),
        ("Visual Communication", "Prof. King", 279.99, "3 credits"), ("Social Media Strategy", "Dr. Wright", 279.99, "3 credits"),
        ("Technical Writing", "Prof. Scott", 229.99, "3 credits"), ("Intercultural Communication", "Dr. Flores", 249.99, "3 credits"),
        ("Media Production", "Prof. Green", 329.99, "3 credits"), ("Communication Research", "Dr. Baker", 249.99, "3 credits"),
    ],
    "Languages": [
        ("Spanish I", "Prof. Garcia", 229.99, "3 credits"), ("French I", "Prof. Martin", 229.99, "3 credits"),
        ("Mandarin Chinese I", "Dr. Wang", 249.99, "3 credits"), ("Japanese I", "Prof. Tanaka", 249.99, "3 credits"),
        ("German I", "Prof. Fischer", 229.99, "3 credits"), ("Arabic I", "Dr. Hassan", 249.99, "3 credits"),
        ("English Composition", "Prof. Roberts", 199.99, "3 credits"), ("Advanced Academic Writing", "Dr. Johnson", 229.99, "3 credits"),
        ("Spanish II", "Prof. Garcia", 249.99, "3 credits"), ("French II", "Prof. Martin", 249.99, "3 credits"),
    ],
}

CAMPUS_NAMES = [
    "EduPath Main Campus", "EduPath Westside", "EduPath Downtown Center",
    "EduPath Technology Hub", "EduPath Lake Campus", "EduPath North Campus",
    "EduPath Arts Center", "EduPath Science Park", "EduPath Business School",
    "EduPath Health Sciences",
]


def esc(s):
    """Escape single quotes for SQL."""
    return s.replace("'", "''")


def random_phone():
    return f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}"


def random_email(first, last):
    domains = ["gmail.com", "yahoo.com", "outlook.com", "university.edu", "student.edu"]
    sep = random.choice([".", "_", ""])
    num = random.choice(["", str(random.randint(1, 99))])
    return f"{first.lower()}{sep}{last.lower()}{num}@{random.choice(domains)}"


def batch_insert(table, columns, rows, profile, warehouse_id, batch_size=50):
    """Insert rows in batches."""
    col_str = ", ".join(columns)
    total = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        values_str = ", ".join(batch)
        stmt = f"INSERT INTO {table} ({col_str}) VALUES {values_str}"
        state = run_sql_check(stmt, profile, warehouse_id, f"  Batch {i//batch_size + 1}")
        if state == "SUCCEEDED":
            total += len(batch)
    return total


def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic education data (EduPath Academy) via Databricks SQL API."
    )
    parser.add_argument("--profile", default="DEFAULT", help="Databricks CLI profile name")
    parser.add_argument("--warehouse-id", required=True, help="SQL warehouse ID")
    parser.add_argument("--catalog", required=True, help="Unity Catalog name (e.g. my_catalog)")
    parser.add_argument("--schema", required=True, help="Schema name (e.g. edupath_agent)")
    args = parser.parse_args()

    global FULL_SCHEMA
    FULL_SCHEMA = f"{args.catalog}.{args.schema}"

    profile = args.profile
    wid = args.warehouse_id
    print(f"Target schema: {FULL_SCHEMA}")

    # ── 1. Students (customers table) ────────────────────────────────────
    print("\n=== Creating customers table (200 students) ===")
    run_sql_check(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.customers (
            customer_id STRING, first_name STRING, last_name STRING, email STRING,
            phone STRING, address STRING, city STRING, state STRING, zip_code STRING,
            membership_tier STRING, join_date STRING, preferences STRING
        )
    """, profile, wid, "Create table")

    rows = []
    for i in range(1, 201):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        city, state = random.choice(CITIES_STATES)
        prefs = json.dumps({
            "learning_style": random.sample(LEARNING_STYLES, k=random.randint(0, 2)),
            "favorite_departments": random.sample(FAVORITE_DEPARTMENTS, k=random.randint(1, 3)),
            "full_time": random.choice([True, False]),
        }).replace("'", "''")
        addr = f"{random.randint(100,9999)} {random.choice(STREETS)}"
        zipcode = f"{random.randint(10000, 99999)}"
        tier = random.choices(MEMBERSHIP_TIERS, weights=[40, 30, 20, 10])[0]
        join_date = (datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1800))).strftime("%Y-%m-%d")
        email = random_email(first, last)

        rows.append(
            f"('CUST-{i:04d}', '{esc(first)}', '{esc(last)}', '{esc(email)}', "
            f"'{random_phone()}', '{esc(addr)}', '{esc(city)}', '{state}', '{zipcode}', "
            f"'{tier}', '{join_date}', '{prefs}')"
        )

    count = batch_insert(f"{FULL_SCHEMA}.customers",
        ["customer_id", "first_name", "last_name", "email", "phone", "address", "city", "state", "zip_code", "membership_tier", "join_date", "preferences"],
        rows, profile, wid)
    print(f"  Inserted {count} students")

    # ── 2. Courses (products table) ─────────────────────────────────────
    print("\n=== Creating products table (~500 courses) ===")
    run_sql_check(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.products (
            product_id STRING, name STRING, category STRING, brand STRING,
            price DOUBLE, stock_quantity INT, aisle INT, unit STRING
        )
    """, profile, wid, "Create table")

    products = []
    buildings = {}
    building_num = 1
    pid = 1
    for cat in PRODUCTS_BY_CATEGORY:
        if cat not in buildings:
            buildings[cat] = building_num
            building_num += 1
        for name, instructor, price, unit in PRODUCTS_BY_CATEGORY[cat]:
            products.append({
                "product_id": f"PROD-{pid:04d}", "name": name, "category": cat,
                "brand": instructor, "price": price, "stock_quantity": random.randint(15, 120),
                "aisle": buildings[cat], "unit": unit,
            })
            pid += 1

    # Pad to ~500 courses with level variations
    while len(products) < 500:
        cat = random.choice(list(PRODUCTS_BY_CATEGORY.keys()))
        base = random.choice(PRODUCTS_BY_CATEGORY[cat])
        variation = random.choice(["Advanced ", "Honors ", "Graduate ", "Intensive ", "Online "])
        products.append({
            "product_id": f"PROD-{pid:04d}", "name": f"{variation}{base[0]}",
            "category": cat, "brand": base[1],
            "price": round(base[2] * random.uniform(0.8, 1.5), 2),
            "stock_quantity": random.randint(15, 120),
            "aisle": buildings[cat], "unit": base[3],
        })
        pid += 1

    rows = []
    for p in products:
        rows.append(
            f"('{p['product_id']}', '{esc(p['name'])}', '{esc(p['category'])}', '{esc(p['brand'])}', "
            f"{p['price']}, {p['stock_quantity']}, {p['aisle']}, '{esc(p['unit'])}')"
        )

    count = batch_insert(f"{FULL_SCHEMA}.products",
        ["product_id", "name", "category", "brand", "price", "stock_quantity", "aisle", "unit"],
        rows, profile, wid, batch_size=100)
    print(f"  Inserted {count} courses")

    # ── 3. Campuses (stores table) ───────────────────────────────────────
    print("\n=== Creating stores table (10 campuses) ===")
    run_sql_check(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.stores (
            store_id STRING, name STRING, address STRING, city STRING, state STRING,
            zip_code STRING, hours STRING, phone STRING
        )
    """, profile, wid, "Create table")

    rows = []
    stores = []
    for i, name in enumerate(CAMPUS_NAMES, 1):
        city, state = CITIES_STATES[i % len(CITIES_STATES)]
        addr = f"{random.randint(100,9999)} {random.choice(STREETS)}"
        zipcode = f"{random.randint(10000, 99999)}"
        phone = random_phone()
        stores.append({"store_id": f"STORE-{i:02d}", "name": name, "city": city, "state": state})
        rows.append(
            f"('STORE-{i:02d}', '{esc(name)}', '{esc(addr)}', '{esc(city)}', '{state}', "
            f"'{zipcode}', '7:00 AM - 10:00 PM', '{phone}')"
        )

    count = batch_insert(f"{FULL_SCHEMA}.stores",
        ["store_id", "name", "address", "city", "state", "zip_code", "hours", "phone"],
        rows, profile, wid)
    print(f"  Inserted {count} campuses")

    # ── 4. Enrollments (transactions) + Course Items ─────────────────────
    print("\n=== Creating transactions table (2000 enrollments) ===")
    run_sql_check(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.transactions (
            transaction_id STRING, customer_id STRING, store_id STRING,
            transaction_date STRING, total_amount DOUBLE,
            payment_method STRING, status STRING
        )
    """, profile, wid, "Create table")

    print("=== Creating transaction_items table (~8000+ course enrollments) ===")
    run_sql_check(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.transaction_items (
            item_id STRING, transaction_id STRING, product_id STRING,
            quantity INT, unit_price DOUBLE, discount DOUBLE
        )
    """, profile, wid, "Create table")

    txn_rows = []
    item_rows = []
    item_id = 1
    customer_ids = [f"CUST-{i:04d}" for i in range(1, 201)]
    store_ids = [f"STORE-{i:02d}" for i in range(1, 11)]

    for txn_id in range(1, 2001):
        cust = random.choice(customer_ids)
        store = random.choice(store_ids)
        txn_date = datetime(2024, 1, 1) + timedelta(
            days=random.randint(0, 440), hours=random.randint(7, 21), minutes=random.randint(0, 59)
        )
        num_items = random.randint(2, 6)  # courses per enrollment
        txn_products = random.sample(products, k=min(num_items, len(products)))

        total = 0.0
        for prod in txn_products:
            qty = 1  # typically 1 section per course
            discount = round(random.choice([0.0, 0.0, 0.0, 25.0, 50.0, 75.0, 100.0]), 2)  # scholarship discounts
            unit_price = prod["price"]
            line_total = round(qty * unit_price - discount, 2)
            total += line_total

            item_rows.append(
                f"('ITEM-{item_id:06d}', 'TXN-{txn_id:05d}', '{prod['product_id']}', "
                f"{qty}, {unit_price}, {discount})"
            )
            item_id += 1

        status = random.choices(["completed", "withdrawn", "pending"], weights=[85, 10, 5])[0]
        txn_rows.append(
            f"('TXN-{txn_id:05d}', '{cust}', '{store}', "
            f"'{txn_date.strftime('%Y-%m-%d %H:%M:%S')}', {round(total, 2)}, "
            f"'{random.choice(PAYMENT_METHODS)}', '{status}')"
        )

    print(f"\n  Inserting {len(txn_rows)} enrollments...")
    count = batch_insert(f"{FULL_SCHEMA}.transactions",
        ["transaction_id", "customer_id", "store_id", "transaction_date", "total_amount", "payment_method", "status"],
        txn_rows, profile, wid, batch_size=100)
    print(f"  Inserted {count} enrollments")

    print(f"\n  Inserting {len(item_rows)} course enrollments...")
    count = batch_insert(f"{FULL_SCHEMA}.transaction_items",
        ["item_id", "transaction_id", "product_id", "quantity", "unit_price", "discount"],
        item_rows, profile, wid, batch_size=100)
    print(f"  Inserted {count} course enrollments")

    # ── 5. Tuition Payment History ──────────────────────────────────────
    print("\n=== Creating payment_history table (400 tuition payments) ===")
    run_sql_check(f"""
        CREATE OR REPLACE TABLE {FULL_SCHEMA}.payment_history (
            payment_id STRING, customer_id STRING, payment_method STRING,
            card_last4 STRING, billing_address STRING, created_date STRING
        )
    """, profile, wid, "Create table")

    rows = []
    for pay_id in range(1, 401):
        cust_idx = random.randint(0, 199)
        cust = f"CUST-{cust_idx+1:04d}"
        method = random.choice(PAYMENT_METHODS)
        card_last4 = str(random.randint(1000, 9999)) if method in ("credit_card", "debit_card") else "NULL"
        city, state = random.choice(CITIES_STATES)
        billing = f"{random.randint(100,9999)} {random.choice(STREETS)}, {city}, {state}"
        created = (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 440))).strftime("%Y-%m-%d")

        card_val = f"'{card_last4}'" if card_last4 != "NULL" else "NULL"
        rows.append(
            f"('PAY-{pay_id:04d}', '{cust}', '{method}', "
            f"{card_val}, '{esc(billing)}', '{created}')"
        )

    count = batch_insert(f"{FULL_SCHEMA}.payment_history",
        ["payment_id", "customer_id", "payment_method", "card_last4", "billing_address", "created_date"],
        rows, profile, wid)
    print(f"  Inserted {count} tuition payment records")

    print("\n=== All tables created successfully! ===")


if __name__ == "__main__":
    main()
