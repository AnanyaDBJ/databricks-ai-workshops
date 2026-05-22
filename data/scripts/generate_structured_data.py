#!/usr/bin/env python3
"""Generate structured tables for an industry (PySpark + Unity Catalog)."""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pyspark.sql import SparkSession
from lib.generate import generate_workshop_data, INDUSTRIES


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--industry", required=True, choices=INDUSTRIES)
    p.add_argument("--catalog", required=True)
    p.add_argument("--schema", required=True)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    spark = SparkSession.builder.getOrCreate()
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {args.catalog}.{args.schema}")
    result = generate_workshop_data(
        args.industry, args.catalog, args.schema, spark, seed=args.seed
    )
    print(f"Done: {result.brand_name} — {result.tables}")


if __name__ == "__main__":
    main()
