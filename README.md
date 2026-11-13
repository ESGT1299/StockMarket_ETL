# Stock Market ETL: reliable financial data ingestion

A Python portfolio project that fetches daily Yahoo Finance OHLCV data, validates it, and loads it into a dedicated PostgreSQL database. A SQLite/offline mode makes the core workflow reproducible without accounts, credentials, or network access.

## What this demonstrates
- Source normalization for flat and two-level yfinance columns.
- Explicit data-quality checks: missing/invalid prices, OHLC ranges, dates, integer volumes, and contradictory duplicate observations fail the run.
- Atomic upserts keyed by `(symbol, date)`, rather than a race-prone read-before-insert deduplication step.
- Transactional batches and corrected source-price updates.
- Configuration through `DATABASE_URL`; no embedded credentials and no credential-bearing exception logging.
- Repeatable tests and an honest distinction between demo results and production validation.

## Quick start (offline)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL = 'sqlite:///demo.db'
python etl_pipeline_prof.py --ticker DEMO --start 2024-01-01 --end 2024-02-01 --csv synthetic_prices.csv --init-schema
python etl_pipeline_prof.py --ticker DEMO --start 2024-01-01 --end 2024-02-01 --csv synthetic_prices.csv
python -m unittest test_etl -v
```

The CSV is **synthetic test data**, not investment returns. Both runs process two observations and leave two rows, not four. The reported count is processed observations, not newly inserted records.

For live data, set `DATABASE_URL` privately to a dedicated demo PostgreSQL database, then omit `--csv`. Use ISO date arguments (`YYYY-MM-DD`); the end date is exclusive. Never put a real password in the command history, README, or Git. This program does not automatically read `.env` files.

## Schema and existing installations

`--init-schema` is for a **new demo database only**. The table uses a composite primary key on symbol/date. It does not migrate an existing `stock_data` table from the old version. Back up and review existing data, resolve duplicate keys, and perform a separately reviewed migration before using this loader against an older database. Do not point this portfolio demo at production.

## Validation and limitations

Unit tests cover parsing, rejection paths, repeated ingestion, multiple symbols and correction updates using SQLite. PostgreSQL SQL compilation is tested; a live PostgreSQL integration/concurrency test and live Yahoo availability are not claimed. The loader does not yet implement retries, scheduling, alerting or corporate-action-adjusted return calculations. Raw OHLC prices must not be used as total-return measures without adjustment. Market-data licensing and Yahoo Finance usage restrictions remain applicable.

## Security note

An earlier source version included a database credential. Removing it from current code does **not** revoke it or erase Git history. The owner must rotate it anywhere it remains valid, check for reuse and review access. This update preserves repository history; no secret value is reproduced here.

## Next evidence-driven extension

Combine this validated ingestion with a data-quality report (missing sessions, stale observations and cross-provider checks), then feed a walk-forward risk dashboard. Keep data lineage and validation evidence with each output rather than adding unsupported performance claims.
