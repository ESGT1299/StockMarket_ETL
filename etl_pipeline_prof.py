"""Validated daily-price ETL. No connection or download occurs on import."""
import argparse
import logging
import math
import os
from datetime import date

import pandas as pd
from sqlalchemy import (BigInteger, CheckConstraint, Column, Date, Float, MetaData,
                        String, Table, create_engine)

LOG = logging.getLogger(__name__)
COLUMNS = ['symbol', 'date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']
metadata = MetaData()
prices = Table('stock_data', metadata,
    Column('symbol', String(32), primary_key=True),
    Column('date', Date, primary_key=True),
    Column('open_price', Float, nullable=False),
    Column('high_price', Float, nullable=False),
    Column('low_price', Float, nullable=False),
    Column('close_price', Float, nullable=False),
    Column('volume', BigInteger, nullable=False),
    CheckConstraint('volume >= 0', name='nonnegative_volume'))


def create_db_engine(url=None):
    """Require explicit configuration; never use checked-in credentials."""
    url = url or os.environ.get('DATABASE_URL')
    if not url:
        raise ValueError('Set DATABASE_URL to a dedicated demo database.')
    engine = create_engine(url, pool_pre_ping=True, hide_parameters=True)
    if engine.dialect.name not in {'sqlite', 'postgresql'}:
        engine.dispose()
        raise ValueError('Only PostgreSQL and SQLite are supported.')
    return engine


def normalize_stock_data(frame, ticker):
    """Accept flat or yfinance MultiIndex OHLCV; fail closed on invalid rows."""
    ticker = str(ticker).strip().upper()
    if not ticker or len(ticker) > 32:
        raise ValueError('Invalid ticker.')
    if frame is None or frame.empty:
        raise ValueError('The source returned no price observations.')
    data = frame.copy()
    if isinstance(data.columns, pd.MultiIndex):
        if data.columns.nlevels != 2:
            raise ValueError('Unsupported source column structure.')
        matches = [i for i in range(2) if ticker in data.columns.get_level_values(i)]
        if len(matches) != 1:
            raise ValueError('Requested ticker is not unambiguous in source columns.')
        data = data.xs(ticker, axis=1, level=matches[0]).copy()
    if 'date' not in data and 'Date' not in data:
        data = data.reset_index()
    data = data.rename(columns={'Date':'date', 'Open':'open_price', 'High':'high_price',
                                'Low':'low_price', 'Close':'close_price', 'Volume':'volume'})
    data['symbol'] = ticker
    missing = set(COLUMNS) - set(data.columns)
    if missing:
        raise ValueError('Missing required OHLCV columns: ' + ', '.join(sorted(missing)))
    data = data[COLUMNS].copy()
    if data['date'].isna().any():
        raise ValueError('Missing trading date.')
    # Keep the source trading date; do not shift exchange dates through UTC.
    data['date'] = [pd.Timestamp(value).date() for value in data['date']]
    for column in COLUMNS[2:]:
        data[column] = pd.to_numeric(data[column], errors='raise')
        if not data[column].map(lambda x: pd.notna(x) and math.isfinite(float(x))).all():
            raise ValueError('Non-finite values in ' + column)
    if (data[COLUMNS[2:6]] <= 0).any().any():
        raise ValueError('OHLC prices must be positive.')
    if ((data['high_price'] < data[['open_price','low_price','close_price']].max(axis=1)) |
        (data['low_price'] > data[['open_price','high_price','close_price']].min(axis=1))).any():
        raise ValueError('Inconsistent OHLC range.')
    if ((data['volume'] < 0) | (data['volume'] % 1 != 0) | (data['volume'] > 2**63-1)).any():
        raise ValueError('Volume must be a nonnegative signed 64-bit integer.')
    data['volume'] = data['volume'].astype('int64')
    data = data.drop_duplicates()
    if data.duplicated(['symbol','date']).any():
        raise ValueError('Conflicting prices for the same symbol and date.')
    return data.sort_values(['symbol','date']).reset_index(drop=True)


def fetch_stock_data(ticker, start_date, end_date):
    """Yahoo daily data; end date is exclusive. Failure is not an empty success."""
    import yfinance as yf
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    if start >= end:
        raise ValueError('Start must be before the exclusive end date.')
    raw = yf.download(ticker, start=start.isoformat(), end=end.isoformat(),
                      auto_adjust=False, progress=False, timeout=20)
    return normalize_stock_data(raw, ticker)


def insert_stock_data(engine, stock_data):
    """Atomic insert-or-update by symbol/date. Existing tables need matching PK."""
    if stock_data is None or stock_data.empty:
        raise ValueError('No validated data supplied.')
    # Revalidate each symbol, including callers supplying frames directly.
    if 'symbol' not in stock_data or stock_data['symbol'].isna().any():
        raise ValueError('Every observation needs a symbol.')
    normalized = pd.concat([normalize_stock_data(group, symbol)
                            for symbol, group in stock_data.groupby('symbol')], ignore_index=True)
    records = normalized.to_dict('records')
    if engine.dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    elif engine.dialect.name == 'sqlite':
        from sqlalchemy.dialects.sqlite import insert
    else:
        raise ValueError('Unsupported database dialect.')
    with engine.begin() as connection:
        for offset in range(0, len(records), 100):
            statement = insert(prices).values(records[offset:offset + 100])
            statement = statement.on_conflict_do_update(
                index_elements=['symbol','date'],
                set_={column: getattr(statement.excluded, column) for column in COLUMNS[2:]})
            connection.execute(statement)
    return len(records)  # processed observations, not a count of new inserts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ticker', required=True)
    parser.add_argument('--start', required=True, help='YYYY-MM-DD')
    parser.add_argument('--end', required=True, help='YYYY-MM-DD, exclusive')
    parser.add_argument('--csv', help='Offline input with Date/Open/High/Low/Close/Volume')
    parser.add_argument('--init-schema', action='store_true', help='Create tables in a NEW demo database only')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    engine = None
    try:
        start, end = date.fromisoformat(args.start), date.fromisoformat(args.end)
        if start >= end:
            raise ValueError('Start must be before end.')
        if args.csv:
            data = normalize_stock_data(pd.read_csv(args.csv), args.ticker)
            data = data[(data['date'] >= start) & (data['date'] < end)]
            if data.empty:
                raise ValueError('No CSV observations in the requested date range.')
        else:
            data = fetch_stock_data(args.ticker, args.start, args.end)
        engine = create_db_engine()
        if args.init_schema:
            metadata.create_all(engine)
        processed = insert_stock_data(engine, data)
        LOG.info('Processed %d validated observations for %s.', processed, args.ticker.upper())
        return 0
    except Exception as error:
        # Never log a DB exception or URL: drivers may include credentials.
        LOG.error('ETL failed (%s). Check source quality, schema and private configuration.', type(error).__name__)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == '__main__':
    raise SystemExit(main())
