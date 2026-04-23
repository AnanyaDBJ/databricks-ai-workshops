# CLAUDE.md — Simple Workshop Guide

## Project Overview

Simple tier of the Databricks AI Workshops. Targets business analysts who run everything inside the Databricks workspace — no local tooling required. A single notebook creates synthetic FreshMart retail data and all Databricks resources needed for the workshop.

## Key Files

- `00_quickstart_setup.py` — Databricks notebook: creates catalog/schema, 7 data tables, Vector Search endpoint + index, Genie Space, and MLflow experiment
- `README.md` — Workshop guide with 4 modules (Genie, Vector Search, Agent Builder, Evaluation)

## Notebook Format

The notebook uses Databricks `.py` notebook format:
- `# Databricks notebook source` header
- `# COMMAND ----------` cell separators
- `# MAGIC %md` for markdown cells

This format is git-friendly and renders as a native notebook when imported into a Databricks workspace.

## Data Sources

- **Structured data**: Generated inline (customers, products, stores, transactions, transaction_items, payment_history)
- **Policy documents**: Read at runtime from `../data/policy_docs/` (7 markdown files shared with the advanced tier)

## Resources Created

| Resource | Naming Pattern |
|---|---|
| Vector Search Endpoint | `freshmart-vs-<schema>` |
| Vector Search Index | `<catalog>.<schema>.policy_docs_index` |
| Genie Space | `FreshMart Retail Data (<schema>)` |
| MLflow Experiment | `/Users/<username>/freshmart-agent-workshop` |

## User Input

`dbutils.widgets.text()` at the top of the notebook for catalog and schema names. Schema defaults to `retail_grocery`.

## Idempotency

All resource creation checks for existing resources first (CREATE IF NOT EXISTS, endpoint/index existence checks, Genie Space title match).
