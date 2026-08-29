# CAUSALA examples

These run without a warehouse. Copy, edit, and ingest your own.

```bash
# 1. warehouse export (CSV from Snowflake/BigQuery)
causala ingest-csv --file examples/warehouse.csv --tenant acme

# 2. single claim
causala ingest --cause price --effect demand --conf 0.82 --source finance-q3-review --tenant acme

# 3. simulate with honesty
causala simulate --lever price --delta 3 --tenant acme
# -> demand: 2.46% [1.985, 2.935] audit cd98f5cc  thin data widened

# 4. fetch the receipt
causala audit --id cd98f5cc --tenant acme
causala verify-chain --tenant acme
```

Edit `warehouse.csv` with your own `cause,effect,confidence,source` and re-run. The twin re-fits instantly, no model retrain.
