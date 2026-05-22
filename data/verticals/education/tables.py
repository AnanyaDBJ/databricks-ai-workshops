"""EduPath Academy — synthetic tables for workshop demo."""
import json
import random
from datetime import datetime, timedelta

from lib.demo_names import CITIES_STATES, FIRST_NAMES, LAST_NAMES, STREETS

TABLES = ["customers", "products", "stores", "transactions", "transaction_items", "payment_history"]

MEMBERSHIP_TIERS = ["Freshman", "Sophomore", "Junior", "Senior"]
LEARNING_STYLES = ["visual", "auditory", "reading", "kinesthetic", "hybrid", "self-paced", "collaborative", "none"]
FAVORITE_DEPARTMENTS = ["Computer Science", "Mathematics", "Business", "Engineering", "Arts", "Sciences", "Humanities", "Health Sciences", "Education"]
PAYMENT_METHODS = ["credit_card", "debit_card", "financial_aid", "scholarship", "wire_transfer"]

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




def random_phone():
    return f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}"


def random_email(first, last):
    domains = ["gmail.com", "yahoo.com", "outlook.com", "university.edu", "student.edu"]
    sep = random.choice([".", "_", ""])
    num = random.choice(["", str(random.randint(1, 99))])
    return f"{first.lower()}{sep}{last.lower()}{num}@{random.choice(domains)}"


def generate(spark, full_schema: str, seed: int = 42) -> list[str]:
    random.seed(seed)
    # ── 1. Customers ───────────────────────────────────────────────────
    print("Generating customers...")
    customers = []
    for i in range(1, 201):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        city, state = random.choice(CITIES_STATES)
        prefs = {
            "dietary": random.sample(LEARNING_STYLES, k=random.randint(0, 2)),
            "favorite_departments": random.sample(FAVORITE_DEPARTMENTS, k=random.randint(1, 3)),
            "full_time": random.choice([True, False]),
        }
        customers.append({
            "customer_id": f"CUST-{i:04d}",
            "first_name": first,
            "last_name": last,
            "email": random_email(first, last),
            "phone": random_phone(),
            "address": f"{random.randint(100,9999)} {random.choice(STREETS)}",
            "city": city,
            "state": state,
            "zip_code": random_zip(),
            "membership_tier": random.choices(MEMBERSHIP_TIERS, weights=[40, 30, 20, 10])[0],
            "join_date": (datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1800))).strftime("%Y-%m-%d"),
            "preferences": json.dumps(prefs),
        })

    customers_df = spark.createDataFrame(customers)
    customers_df.write.mode("overwrite").saveAsTable(f"{full_schema}.customers")
    print(f"  Wrote {customers_df.count()} customers")

    # ── 2. Products ─────────────────────────────────────────────────────
    print("Generating products...")
    products = []
    pid = 1
    aisles = {}
    aisle_num = 1
    for cat in PRODUCTS_BY_CATEGORY:
        if cat not in aisles:
            aisles[cat] = aisle_num
            aisle_num += 1
        for name, brand, price, unit in PRODUCTS_BY_CATEGORY[cat]:
            products.append({
                "product_id": f"PROD-{pid:04d}",
                "name": name,
                "category": cat,
                "brand": brand,
                "price": round(price, 2),
                "stock_quantity": random.randint(15, 120),
                "aisle": aisles[cat],
                "unit": unit,
            })
            pid += 1

    # Pad to ~500 products with variations
    while len(products) < 500:
        cat = random.choice(list(PRODUCTS_BY_CATEGORY.keys()))
        base = random.choice(PRODUCTS_BY_CATEGORY[cat])
        variation = random.choice(["Advanced ", "Honors ", "Graduate ", "Intensive ", "Online "])
        products.append({
            "product_id": f"PROD-{pid:04d}",
            "name": f"{variation}{base[0]}",
            "category": cat,
            "brand": base[1],
            "price": round(base[2] * random.uniform(0.8, 1.5), 2),
            "stock_quantity": random.randint(15, 120),
            "aisle": aisles[cat],
            "unit": base[3],
        })
        pid += 1

    products_df = spark.createDataFrame(products)
    products_df.write.mode("overwrite").saveAsTable(f"{full_schema}.products")
    print(f"  Wrote {products_df.count()} products")

    # ── 3. Stores ───────────────────────────────────────────────────────
    print("Generating stores...")
    stores = []
    for i, name in enumerate(CAMPUS_NAMES, 1):
        city, state = CITIES_STATES[i % len(CITIES_STATES)]
        stores.append({
            "store_id": f"STORE-{i:02d}",
            "name": name,
            "address": f"{random.randint(100,9999)} {random.choice(STREETS)}",
            "city": city,
            "state": state,
            "zip_code": random_zip(),
            "hours": "7:00 AM - 10:00 PM",
            "phone": random_phone(),
        })

    stores_df = spark.createDataFrame(stores)
    stores_df.write.mode("overwrite").saveAsTable(f"{full_schema}.stores")
    print(f"  Wrote {stores_df.count()} stores")

    # ── 4. Transactions + Transaction Items ─────────────────────────────
    print("Generating transactions and transaction items...")
    transactions = []
    transaction_items = []
    item_id = 1

    for txn_id in range(1, 2001):
        customer = random.choice(customers)
        store = random.choice(stores)
        txn_date = datetime(2024, 1, 1) + timedelta(
            days=random.randint(0, 440),
            hours=random.randint(7, 21),
            minutes=random.randint(0, 59),
        )
        num_items = random.randint(2, 6)
        txn_products = random.sample(products, k=min(num_items, len(products)))

        total = 0.0
        for prod in txn_products:
            qty = 1
            discount = round(random.choice([0.0, 0.0, 0.0, 25.0, 50.0, 75.0, 100.0]), 2)
            unit_price = prod["price"]
            line_total = round(qty * unit_price - discount, 2)
            total += line_total

            transaction_items.append({
                "item_id": f"ITEM-{item_id:06d}",
                "transaction_id": f"TXN-{txn_id:05d}",
                "product_id": prod["product_id"],
                "quantity": float(qty),
                "unit_price": unit_price,
                "discount": discount,
            })
            item_id += 1

        transactions.append({
            "transaction_id": f"TXN-{txn_id:05d}",
            "customer_id": customer["customer_id"],
            "store_id": store["store_id"],
            "transaction_date": txn_date.strftime("%Y-%m-%d %H:%M:%S"),
            "total_amount": round(total, 2),
            "payment_method": random.choice(PAYMENT_METHODS),
            "status": random.choices(["completed", "refunded", "pending"], weights=[90, 7, 3])[0],
        })

    transactions_df = spark.createDataFrame(transactions)
    transactions_df.write.mode("overwrite").saveAsTable(f"{full_schema}.transactions")
    print(f"  Wrote {transactions_df.count()} transactions")

    transaction_items_df = spark.createDataFrame(transaction_items)
    transaction_items_df.write.mode("overwrite").saveAsTable(f"{full_schema}.transaction_items")
    print(f"  Wrote {transaction_items_df.count()} transaction items")

    # ── 5. Payment History ──────────────────────────────────────────────
    print("Generating payment history...")
    payment_history = []
    for pay_id in range(1, 401):
        customer = random.choice(customers)
        method = random.choice(PAYMENT_METHODS)
        card_last4 = str(random.randint(1000, 9999)) if method in ("credit_card", "debit_card") else None
        payment_history.append({
            "payment_id": f"PAY-{pay_id:04d}",
            "customer_id": customer["customer_id"],
            "payment_method": method,
            "card_last4": card_last4,
            "billing_address": f"{random.randint(100,9999)} {random.choice(STREETS)}, {customer['city']}, {customer['state']}",
            "created_date": (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 440))).strftime("%Y-%m-%d"),
        })

    payment_history_df = spark.createDataFrame(payment_history)
    payment_history_df.write.mode("overwrite").saveAsTable(f"{full_schema}.payment_history")
    print(f"  Wrote {payment_history_df.count()} payment records")

    print("\nAll tables created successfully in", full_schema)
    return TABLES
