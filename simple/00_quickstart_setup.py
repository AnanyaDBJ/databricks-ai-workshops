# Databricks notebook source
# MAGIC %md
# MAGIC # FreshMart Workshop Setup
# MAGIC
# MAGIC This notebook creates everything you need for the workshop:
# MAGIC
# MAGIC | Step | What it creates |
# MAGIC |------|----------------|
# MAGIC | 1 | Catalog and schema in Unity Catalog |
# MAGIC | 2 | 6 retail data tables (customers, products, stores, transactions, etc.) |
# MAGIC | 3 | Policy documents table (chunked for search) |
# MAGIC | 4 | Vector Search endpoint and index |
# MAGIC | 5 | Genie Space for natural language data queries |
# MAGIC | 6 | MLflow experiment for agent evaluation |
# MAGIC
# MAGIC **Instructions:** Fill in your catalog and schema names in the widgets at the top of the notebook, then click **Run All**.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration
# MAGIC
# MAGIC Set your catalog and schema names using the widgets above. These will be used for all resources created in this notebook.

# COMMAND ----------

# MAGIC %pip install databricks-vectorsearch
# MAGIC %restart_python

# COMMAND ----------

dbutils.widgets.text("catalog", "", "1. Catalog Name")
dbutils.widgets.text("schema", "retail_grocery", "2. Schema Name")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")

if not CATALOG:
    raise ValueError("Please enter a catalog name in the widget at the top of the notebook.")

FULL_SCHEMA = f"{CATALOG}.{SCHEMA}"
print(f"Using schema: {FULL_SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Create Catalog and Schema

# COMMAND ----------

# spark.sql(f"CREATE CATALOG IF NOT EXISTS {CATALOG}")
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {FULL_SCHEMA}")
print(f"Catalog '{CATALOG}' and schema '{FULL_SCHEMA}' are ready.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Create Retail Data Tables
# MAGIC
# MAGIC This generates synthetic data for a fictional grocery chain called **FreshMart**:
# MAGIC - **customers** — 200 shoppers with membership tiers and preferences
# MAGIC - **products** — ~500 grocery items across 10 categories
# MAGIC - **stores** — 10 FreshMart locations
# MAGIC - **transactions** — 2,000 purchase records
# MAGIC - **transaction_items** — ~8,000 line items
# MAGIC - **payment_history** — 400 payment method records

# COMMAND ----------

import json
import random
from datetime import datetime, timedelta

random.seed(42)

# ── Domain data ──────────────────────────────────────────────────────

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


print("Domain data loaded. Generating tables...")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Customers (200 rows)

# COMMAND ----------

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
        "zip_code": f"{random.randint(10000, 99999)}",
        "membership_tier": random.choices(MEMBERSHIP_TIERS, weights=[40, 30, 20, 10])[0],
        "join_date": (datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1800))).strftime("%Y-%m-%d"),
        "preferences": json.dumps(prefs),
    })

customers_df = spark.createDataFrame(customers)
customers_df.write.mode("overwrite").saveAsTable(f"{FULL_SCHEMA}.customers")
print(f"Created {FULL_SCHEMA}.customers — {customers_df.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Products (~500 rows)

# COMMAND ----------

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
print(f"Created {FULL_SCHEMA}.products — {products_df.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Stores (10 rows)

# COMMAND ----------

stores = []
for i, name in enumerate(STORE_NAMES, 1):
    city, state = CITIES_STATES[i % len(CITIES_STATES)]
    stores.append({
        "store_id": f"STORE-{i:02d}",
        "name": name,
        "address": f"{random.randint(100,9999)} {random.choice(STREETS)}",
        "city": city,
        "state": state,
        "zip_code": f"{random.randint(10000, 99999)}",
        "hours": "7:00 AM - 10:00 PM",
        "phone": random_phone(),
    })

stores_df = spark.createDataFrame(stores)
stores_df.write.mode("overwrite").saveAsTable(f"{FULL_SCHEMA}.stores")
print(f"Created {FULL_SCHEMA}.stores — {stores_df.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Transactions (2,000 rows) and Transaction Items (~8,000 rows)

# COMMAND ----------

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
print(f"Created {FULL_SCHEMA}.transactions — {transactions_df.count()} rows")

transaction_items_df = spark.createDataFrame(transaction_items)
transaction_items_df.write.mode("overwrite").saveAsTable(f"{FULL_SCHEMA}.transaction_items")
print(f"Created {FULL_SCHEMA}.transaction_items — {transaction_items_df.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Payment History (400 rows)

# COMMAND ----------

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
print(f"Created {FULL_SCHEMA}.payment_history — {payment_history_df.count()} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Verify All Tables

# COMMAND ----------

print(f"Tables in {FULL_SCHEMA}:\n")
tables = ["customers", "products", "stores", "transactions", "transaction_items", "payment_history"]
for table in tables:
    count = spark.sql(f"SELECT COUNT(*) as cnt FROM {FULL_SCHEMA}.{table}").collect()[0]["cnt"]
    print(f"  {table:25s} {count:>8,} rows")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Create Policy Documents Table
# MAGIC
# MAGIC This reads the 7 FreshMart policy documents from the `data/policy_docs/` directory, splits them into
# MAGIC overlapping text chunks, and writes them to a table that Vector Search will index.

# COMMAND ----------

import hashlib
import os

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Locate the policy_docs directory relative to this notebook
# In a Databricks Repo, the repo root is available via the workspace file system
notebook_path = dbutils.entry_point.getDbutils().notebook().getContext().notebookPath().get()
repo_root = "/".join(notebook_path.split("/")[:-2])  # go up from simple/00_quickstart_setup
docs_dir = f"/Workspace{repo_root}/data/policy_docs"

# Fallback: try relative path if running locally or in a different context
if not os.path.isdir(docs_dir):
    docs_dir = os.path.join(os.path.dirname(os.path.abspath(".")), "data", "policy_docs")
if not os.path.isdir(docs_dir):
    raise FileNotFoundError(
        f"Could not find policy_docs directory. Looked in:\n"
        f"  /Workspace{repo_root}/data/policy_docs\n"
        f"  {os.path.join(os.path.dirname(os.path.abspath('.')), 'data', 'policy_docs')}\n"
        f"Make sure you cloned the full repository."
    )


def chunk_text(text):
    """Split text into overlapping chunks by paragraph."""
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 2 <= CHUNK_SIZE:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                chunks.append(current.strip())
            if len(para) > CHUNK_SIZE:
                words = para.split()
                current = ""
                for word in words:
                    if len(current) + len(word) + 1 <= CHUNK_SIZE:
                        current = f"{current} {word}" if current else word
                    else:
                        chunks.append(current.strip())
                        overlap_text = current[-CHUNK_OVERLAP:] if len(current) > CHUNK_OVERLAP else current
                        current = f"{overlap_text} {word}"
            else:
                if chunks:
                    prev = chunks[-1]
                    overlap_text = prev[-CHUNK_OVERLAP:] if len(prev) > CHUNK_OVERLAP else prev
                    current = f"{overlap_text}\n\n{para}"
                else:
                    current = para

    if current.strip():
        chunks.append(current.strip())
    return chunks


# Read and chunk all policy documents
all_chunks = []
print(f"Reading policy documents from: {docs_dir}\n")
for filename in sorted(os.listdir(docs_dir)):
    if not filename.endswith(".md"):
        continue
    filepath = os.path.join(docs_dir, filename)
    with open(filepath, "r") as f:
        content = f.read()

    doc_name = filename.replace(".md", "")
    chunks = chunk_text(content)
    print(f"  {filename}: {len(chunks)} chunks")

    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.md5(f"{doc_name}::{i}".encode()).hexdigest()[:16]
        all_chunks.append({
            "chunk_id": chunk_id,
            "doc_name": doc_name,
            "content": chunk,
        })

chunks_df = spark.createDataFrame(all_chunks)
chunks_df.write.mode("overwrite").saveAsTable(f"{FULL_SCHEMA}.policy_docs_chunked")
print(f"\nCreated {FULL_SCHEMA}.policy_docs_chunked — {chunks_df.count()} chunks from {len(set(c['doc_name'] for c in all_chunks))} documents")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Create Vector Search Endpoint and Index
# MAGIC
# MAGIC Vector Search lets you find relevant policy documents using natural language instead of exact keyword matches.
# MAGIC This creates:
# MAGIC 1. A **Vector Search endpoint** (the compute that powers similarity search)
# MAGIC 2. A **Delta Sync index** on the policy docs table (automatically generates embeddings)
# MAGIC
# MAGIC The endpoint takes 5-10 minutes to become ready. The cell will wait automatically.

# COMMAND ----------

import time
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.vectorsearch import (
    DeltaSyncVectorIndexSpecRequest,
    EmbeddingSourceColumn,
    EndpointType,
    PipelineType,
    VectorIndexType,
)

w = WorkspaceClient()

VS_ENDPOINT_NAME = f"freshmart-vs-{SCHEMA.replace('_', '-')}"
VS_INDEX_NAME = f"{FULL_SCHEMA}.policy_docs_index"

# --- Create endpoint (or reuse existing) ---
try:
    endpoint = w.vector_search_endpoints.get_endpoint(VS_ENDPOINT_NAME)
    print(f"Vector Search endpoint '{VS_ENDPOINT_NAME}' already exists (status: {endpoint.endpoint_status.state.value})")
except Exception:
    print(f"Creating Vector Search endpoint '{VS_ENDPOINT_NAME}'...")
    w.vector_search_endpoints.create_endpoint_and_wait(
        name=VS_ENDPOINT_NAME,
        endpoint_type=EndpointType.STANDARD,
    )
    print(f"Vector Search endpoint '{VS_ENDPOINT_NAME}' is ONLINE.")

# Wait until endpoint is ONLINE
for attempt in range(60):
    endpoint = w.vector_search_endpoints.get_endpoint(VS_ENDPOINT_NAME)
    status = endpoint.endpoint_status.state.value
    if status == "ONLINE":
        break
    if attempt % 6 == 0:
        print(f"  Waiting for endpoint to be ONLINE (currently: {status})...")
    time.sleep(10)
else:
    print(f"WARNING: Endpoint status is '{status}' after 10 minutes. It may still be provisioning.")

print(f"Endpoint '{VS_ENDPOINT_NAME}' is ready.")

# COMMAND ----------

# MAGIC %sql 
# MAGIC ALTER TABLE qsic_workshop_prep_catalog.level_100_testing.policy_docs_chunked
# MAGIC   SET TBLPROPERTIES (delta.enableChangeDataFeed = true)

# COMMAND ----------

from databricks.vector_search.client import VectorSearchClient

client = VectorSearchClient()

index = client.create_delta_sync_index(
  endpoint_name=VS_ENDPOINT_NAME,
  source_table_name="qsic_workshop_prep_catalog.level_100_testing.policy_docs_chunked",
  index_name=VS_INDEX_NAME,
  pipeline_type="TRIGGERED",
  primary_key="chunk_id",
  embedding_source_column="content",
  embedding_model_endpoint_name="databricks-gte-large-en",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Create Genie Space
# MAGIC
# MAGIC Genie lets you ask questions about your data in plain English. It converts your questions into SQL automatically.
# MAGIC
# MAGIC This creates a Genie Space connected to all 6 FreshMart data tables.

# COMMAND ----------

import json

GENIE_SPACE_TITLE = f"FreshMart Retail Data ({SCHEMA})"


# Get the first available SQL warehouse
warehouses = w.warehouses.list()
warehouse_id = None
for wh in warehouses:
    if wh.state and wh.state.value in ("RUNNING", "STARTING"):
        warehouse_id = wh.id
        break
    if wh.id:
        warehouse_id = wh.id  # fallback to any warehouse

if not warehouse_id:
    print("WARNING: No SQL warehouse found. Please create one and re-run this cell.")
else:
    table_identifiers = [f"{FULL_SCHEMA}.{t}" for t in tables]

    # Check if a Genie Space with this title already exists
    existing_spaces = w.api_client.do("GET", "/api/2.0/genie/spaces")
    genie_space_id = None
    for space in existing_spaces.get("spaces", []):
        if space.get("title") == GENIE_SPACE_TITLE:
            genie_space_id = space.get("space_id")
            print(f"Genie Space '{GENIE_SPACE_TITLE}' already exists (ID: {genie_space_id})")
            break

    if not genie_space_id:
        print(f"Creating Genie Space '{GENIE_SPACE_TITLE}'...")
        serialized = json.dumps({
            "version": 1,
            "data_sources": {
                "tables": [{"identifier": t} for t in sorted(table_identifiers)]
            }
        })
        response = w.api_client.do("POST", "/api/2.0/genie/spaces", body={
            "title": GENIE_SPACE_TITLE,
            "description": (
                "FreshMart retail grocery data for the AI workshop. "
                "Contains customer information, product catalog, store locations, "
                "transaction history, and payment records."
            ),
            "warehouse_id": warehouse_id,
            "serialized_space": serialized,
        })
        genie_space_id = response.get("space_id")
        print(f"Genie Space created (ID: {genie_space_id})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Create MLflow Experiment
# MAGIC
# MAGIC MLflow tracks your agent's performance. This creates an experiment where traces and evaluation metrics will be logged.

# COMMAND ----------

import mlflow

mlflow.set_tracking_uri("databricks")

username = spark.sql("SELECT current_user()").collect()[0][0]
experiment_name = f"/Users/{username}/freshmart-agent-workshop"

try:
    experiment = mlflow.get_experiment_by_name(experiment_name)
    if experiment and experiment.lifecycle_stage == "active":
        experiment_id = experiment.experiment_id
        print(f"MLflow experiment already exists: {experiment_name} (ID: {experiment_id})")
    else:
        experiment_id = mlflow.create_experiment(experiment_name)
        print(f"MLflow experiment created: {experiment_name} (ID: {experiment_id})")
except Exception:
    experiment_id = mlflow.create_experiment(experiment_name)
    print(f"MLflow experiment created: {experiment_name} (ID: {experiment_id})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup Complete
# MAGIC
# MAGIC All resources have been created. Here's a summary of everything that's ready for you:

# COMMAND ----------

print("=" * 70)
print("  FRESHMART WORKSHOP SETUP COMPLETE")
print("=" * 70)
print()
print(f"  Catalog/Schema:     {FULL_SCHEMA}")
print()
print("  Data Tables:")
for table in tables:
    count = spark.sql(f"SELECT COUNT(*) as cnt FROM {FULL_SCHEMA}.{table}").collect()[0]["cnt"]
    print(f"    {table:25s} {count:>8,} rows")
chunks_count = spark.sql(f"SELECT COUNT(*) as cnt FROM {FULL_SCHEMA}.policy_docs_chunked").collect()[0]["cnt"]
print(f"    {'policy_docs_chunked':25s} {chunks_count:>8,} chunks")
print()
print(f"  Vector Search Endpoint:  {VS_ENDPOINT_NAME}")
print(f"  Vector Search Index:     {VS_INDEX_NAME}")
print()
if genie_space_id:
    print(f"  Genie Space ID:          {genie_space_id}")
    print(f"  Genie Space Title:       {GENIE_SPACE_TITLE}")
print()
print(f"  MLflow Experiment:       {experiment_name}")
print(f"  MLflow Experiment ID:    {experiment_id}")
print()
print("=" * 70)
print("  Next Steps:")
print("    1. Open the Genie Space and try asking questions about your data")
print("    2. Explore the Vector Search index in Catalog Explorer")
print("    3. Open the Databricks Playground to build your first agent")
print("    4. See the README for detailed workshop modules")
print("=" * 70)
