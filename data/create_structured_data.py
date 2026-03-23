""" 
Generate synthetic retail grocery data and write to Unity Catalog tables.

Usage:
    Run as a Databricks notebook or via `databricks` CLI:
        databricks jobs submit --json '{"notebook_task": {"notebook_path": "..."}}'

    Or locally with PySpark + Unity Catalog connectivity.

Target schema: <CATALOG>.<SCHEMA>
"""

import json
import random
from datetime import datetime, timedelta

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    ArrayType,
    DecimalType,
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# ── TO DO Change the ──────────────────────────────────────────────────────────
CATALOG = "qsic_workshop_prep_catalog"
SCHEMA = "retail_agent"
FULL_SCHEMA = f"{CATALOG}.{SCHEMA}"

spark = SparkSession.builder.getOrCreate()
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {FULL_SCHEMA}")

random.seed(42)

# ── Domain data ─────────────────────────────────────────────────────
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

MEMBERSHIP_TIERS = ["Bronze", "Silver", "Gold", "Platinum"]
DIETARY_PREFS = ["vegetarian", "vegan", "gluten-free", "keto", "paleo", "dairy-free", "nut-free", "none"]
FAVORITE_CATEGORIES = ["Produce", "Dairy", "Bakery", "Meat & Seafood", "Frozen", "Snacks", "Beverages", "Deli", "Organic"]
PAYMENT_METHODS = ["credit_card", "debit_card", "cash", "mobile_pay", "gift_card"]

# Product catalog by category
PRODUCTS_BY_CATEGORY = {
    "Produce": [
        ("Organic Bananas", "Dole", 0.79, "bunch"), ("Red Apples", "Honeycrisp", 2.49, "lb"),
        ("Baby Spinach", "Earthbound", 3.99, "bag"), ("Avocados", "Hass", 1.49, "each"),
        ("Roma Tomatoes", "Local Farm", 1.99, "lb"), ("Blueberries", "Driscoll's", 4.99, "pint"),
        ("Sweet Potatoes", "Local Farm", 1.29, "lb"), ("Broccoli Crowns", "Green Giant", 2.49, "lb"),
        ("Strawberries", "Driscoll's", 5.99, "pack"), ("Lemons", "Sunkist", 0.69, "each"),
        ("Cucumbers", "English", 1.79, "each"), ("Bell Peppers", "Local Farm", 1.49, "each"),
        ("Carrots", "Bolthouse", 1.99, "bag"), ("Russet Potatoes", "Idaho", 4.99, "5lb bag"),
        ("Mixed Greens", "Taylor Farms", 4.49, "bag"), ("Grapes Red Seedless", "Chile", 3.49, "lb"),
    ],
    "Dairy": [
        ("Whole Milk", "Horizon Organic", 5.49, "gallon"), ("2% Milk", "Darigold", 4.29, "gallon"),
        ("Greek Yogurt Plain", "Chobani", 5.99, "32oz"), ("Cheddar Cheese Block", "Tillamook", 5.99, "8oz"),
        ("Butter Unsalted", "Kerrygold", 4.99, "8oz"), ("Heavy Cream", "Darigold", 3.99, "pint"),
        ("Sour Cream", "Daisy", 2.49, "16oz"), ("Cream Cheese", "Philadelphia", 3.29, "8oz"),
        ("Shredded Mozzarella", "Galbani", 4.49, "8oz"), ("Almond Milk", "Silk", 3.99, "half gallon"),
        ("Oat Milk", "Oatly", 4.49, "half gallon"), ("Cottage Cheese", "Daisy", 3.99, "16oz"),
        ("Parmesan Wedge", "BelGioioso", 6.99, "5oz"), ("Egg Dozen Large", "Pete & Gerry's", 5.49, "dozen"),
    ],
    "Bakery": [
        ("Sourdough Bread", "Bakery Fresh", 4.99, "loaf"), ("Whole Wheat Bread", "Dave's Killer", 5.49, "loaf"),
        ("Croissants", "Bakery Fresh", 3.99, "4 pack"), ("Bagels Everything", "Bakery Fresh", 4.49, "6 pack"),
        ("Baguette", "Bakery Fresh", 2.99, "each"), ("Cinnamon Rolls", "Bakery Fresh", 5.99, "4 pack"),
        ("Tortillas Flour", "Mission", 3.49, "10 pack"), ("Hamburger Buns", "Bakery Fresh", 3.99, "8 pack"),
        ("Multigrain Bread", "Bakery Fresh", 4.49, "loaf"), ("Dinner Rolls", "Bakery Fresh", 3.49, "12 pack"),
    ],
    "Meat & Seafood": [
        ("Chicken Breast Boneless", "Foster Farms", 6.99, "lb"), ("Ground Beef 80/20", "Angus", 5.99, "lb"),
        ("Atlantic Salmon Fillet", "Fresh Catch", 12.99, "lb"), ("Pork Chops", "Smithfield", 4.99, "lb"),
        ("Bacon Thick Cut", "Applegate", 7.99, "12oz"), ("Shrimp Large Peeled", "Wild Caught", 11.99, "lb"),
        ("Turkey Breast Deli", "Boar's Head", 9.99, "lb"), ("Italian Sausage", "Johnsonville", 5.49, "pack"),
        ("Ribeye Steak", "USDA Choice", 14.99, "lb"), ("Ground Turkey", "Jennie-O", 5.49, "lb"),
        ("Tilapia Fillet", "Fresh Catch", 7.99, "lb"), ("Lamb Chops", "New Zealand", 13.99, "lb"),
    ],
    "Frozen": [
        ("Frozen Pizza Margherita", "Amy's", 8.99, "each"), ("Ice Cream Vanilla", "Tillamook", 5.99, "1.5qt"),
        ("Frozen Vegetables Mixed", "Birds Eye", 2.99, "bag"), ("Frozen Berries Mixed", "Wyman's", 5.49, "bag"),
        ("Frozen Waffles", "Eggo", 3.49, "10 pack"), ("Frozen Burritos", "Amy's", 3.49, "each"),
        ("Fish Sticks", "Gorton's", 4.99, "box"), ("Frozen Edamame", "Seapoint Farms", 3.49, "bag"),
        ("Ice Cream Bars", "Haagen-Dazs", 5.99, "3 pack"), ("Frozen Mac & Cheese", "Stouffer's", 3.99, "each"),
    ],
    "Snacks": [
        ("Potato Chips Sea Salt", "Kettle Brand", 4.49, "bag"), ("Trail Mix", "Kirkland", 8.99, "bag"),
        ("Granola Bars", "Nature Valley", 3.99, "6 pack"), ("Pretzels Twists", "Snyder's", 3.49, "bag"),
        ("Dark Chocolate Bar", "Lindt", 3.99, "bar"), ("Popcorn Butter", "SkinnyPop", 4.49, "bag"),
        ("Crackers Wheat", "Triscuit", 3.99, "box"), ("Hummus Classic", "Sabra", 4.49, "10oz"),
        ("Mixed Nuts Roasted", "Planters", 7.99, "can"), ("Rice Cakes", "Lundberg", 3.49, "bag"),
        ("Tortilla Chips", "Late July", 3.99, "bag"), ("Fruit Snacks", "Annie's", 4.49, "box"),
    ],
    "Beverages": [
        ("Orange Juice", "Tropicana", 4.99, "52oz"), ("Sparkling Water Lime", "LaCroix", 5.49, "12 pack"),
        ("Coffee Ground Medium", "Stumptown", 12.99, "12oz bag"), ("Green Tea Bags", "Tazo", 4.49, "20 bags"),
        ("Kombucha Ginger", "GT's", 3.99, "16oz"), ("Apple Juice", "Martinelli's", 3.49, "1.5L"),
        ("Cold Brew Coffee", "Stumptown", 4.99, "12oz"), ("Coconut Water", "Vita Coco", 2.99, "16oz"),
        ("Lemonade", "Simply", 3.49, "52oz"), ("Sports Drink", "Gatorade", 1.49, "32oz"),
    ],
    "Pantry": [
        ("Olive Oil Extra Virgin", "California Olive Ranch", 9.99, "bottle"), ("Pasta Spaghetti", "Barilla", 1.79, "box"),
        ("Marinara Sauce", "Rao's", 7.99, "jar"), ("Rice Jasmine", "Mahatma", 4.99, "2lb bag"),
        ("Black Beans", "Goya", 1.29, "can"), ("Chicken Broth", "Swanson", 2.49, "32oz"),
        ("Peanut Butter", "Jif", 3.99, "jar"), ("Honey", "Local Harvest", 8.99, "16oz"),
        ("Canned Tuna", "Wild Planet", 3.49, "can"), ("Coconut Milk", "Thai Kitchen", 2.49, "can"),
        ("Maple Syrup", "Grade A", 9.99, "12oz"), ("Flour All Purpose", "King Arthur", 4.49, "5lb bag"),
        ("Sugar Granulated", "C&H", 3.99, "4lb bag"), ("Soy Sauce", "Kikkoman", 3.49, "10oz"),
    ],
    "Deli": [
        ("Roast Turkey Breast", "Boar's Head", 10.99, "lb"), ("Ham Black Forest", "Boar's Head", 9.99, "lb"),
        ("Swiss Cheese Sliced", "Boar's Head", 8.99, "lb"), ("Chicken Salad", "Deli Fresh", 7.99, "lb"),
        ("Potato Salad", "Deli Fresh", 4.99, "lb"), ("Rotisserie Chicken", "Store Made", 8.99, "each"),
        ("Coleslaw", "Deli Fresh", 3.99, "lb"), ("Macaroni Salad", "Deli Fresh", 4.49, "lb"),
    ],
    "Household": [
        ("Paper Towels", "Bounty", 12.99, "6 roll"), ("Dish Soap", "Dawn", 3.99, "bottle"),
        ("Trash Bags", "Glad", 9.99, "45 count"), ("Laundry Detergent", "Tide", 11.99, "bottle"),
        ("Aluminum Foil", "Reynolds", 4.49, "roll"), ("Sponges", "Scotch-Brite", 3.49, "3 pack"),
        ("Ziplock Bags Gallon", "Ziploc", 4.99, "30 count"), ("All Purpose Cleaner", "Method", 4.49, "bottle"),
    ],
}

STORE_NAMES = [
    "FreshMart Downtown", "FreshMart Westside", "FreshMart Pearl District",
    "FreshMart Hawthorne", "FreshMart Lake Oswego", "FreshMart Beaverton",
    "FreshMart Sellwood", "FreshMart Alberta", "FreshMart Division",
    "FreshMart Hillsdale",
]


def random_phone():
    return f"({random.randint(200,999)}) {random.randint(200,999)}-{random.randint(1000,9999)}"


def random_email(first, last):
    domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"]
    sep = random.choice([".", "_", ""])
    num = random.choice(["", str(random.randint(1, 99))])
    return f"{first.lower()}{sep}{last.lower()}{num}@{random.choice(domains)}"


def random_zip():
    return f"{random.randint(10000, 99999)}"


# ── 1. Customers ───────────────────────────────────────────────────
print("Generating customers...")
customers = []
for i in range(1, 201):
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    city, state = random.choice(CITIES_STATES)
    prefs = {
        "dietary": random.sample(DIETARY_PREFS, k=random.randint(0, 2)),
        "favorite_categories": random.sample(FAVORITE_CATEGORIES, k=random.randint(1, 3)),
        "organic_preference": random.choice([True, False]),
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
customers_df.write.mode("overwrite").saveAsTable(f"{FULL_SCHEMA}.customers")
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
            "stock_quantity": random.randint(0, 500),
            "aisle": aisles[cat],
            "unit": unit,
        })
        pid += 1

# Pad to ~500 products with variations
while len(products) < 500:
    cat = random.choice(list(PRODUCTS_BY_CATEGORY.keys()))
    base = random.choice(PRODUCTS_BY_CATEGORY[cat])
    variation = random.choice(["Organic ", "Family Size ", "Value Pack ", "Premium ", "Lite "])
    products.append({
        "product_id": f"PROD-{pid:04d}",
        "name": f"{variation}{base[0]}",
        "category": cat,
        "brand": base[1],
        "price": round(base[2] * random.uniform(0.8, 1.5), 2),
        "stock_quantity": random.randint(0, 500),
        "aisle": aisles[cat],
        "unit": base[3],
    })
    pid += 1

products_df = spark.createDataFrame(products)
products_df.write.mode("overwrite").saveAsTable(f"{FULL_SCHEMA}.products")
print(f"  Wrote {products_df.count()} products")

# ── 3. Stores ───────────────────────────────────────────────────────
print("Generating stores...")
stores = []
for i, name in enumerate(STORE_NAMES, 1):
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
stores_df.write.mode("overwrite").saveAsTable(f"{FULL_SCHEMA}.stores")
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
    num_items = random.randint(2, 8)
    txn_products = random.sample(products, k=min(num_items, len(products)))

    total = 0.0
    for prod in txn_products:
        qty = random.randint(1, 5)
        discount = round(random.choice([0.0, 0.0, 0.0, 0.5, 1.0, 1.5, 2.0]), 2)
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
transactions_df.write.mode("overwrite").saveAsTable(f"{FULL_SCHEMA}.transactions")
print(f"  Wrote {transactions_df.count()} transactions")

transaction_items_df = spark.createDataFrame(transaction_items)
transaction_items_df.write.mode("overwrite").saveAsTable(f"{FULL_SCHEMA}.transaction_items")
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
payment_history_df.write.mode("overwrite").saveAsTable(f"{FULL_SCHEMA}.payment_history")
print(f"  Wrote {payment_history_df.count()} payment records")

print("\nAll tables created successfully in", FULL_SCHEMA)
