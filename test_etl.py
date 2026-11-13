import os
import unittest
from unittest.mock import patch
import pandas as pd
from sqlalchemy import create_engine, select, func
from etl_pipeline_prof import normalize_stock_data, create_db_engine, metadata, prices, insert_stock_data


def sample():
    return pd.DataFrame({'Date':['2024-01-02','2024-01-03'], 'Open':[100,102],
                         'High':[103,105], 'Low':[99,101], 'Close':[102,104], 'Volume':[1000,1500]})

class QualityTests(unittest.TestCase):
    def test_flat_columns(self):
        result = normalize_stock_data(sample(), 'aapl')
        self.assertEqual(result.symbol.tolist(), ['AAPL','AAPL'])
        self.assertEqual(str(result.date.iloc[0]), '2024-01-02')
    def test_multilevel_columns(self):
        data = sample().set_index('Date')
        data.columns = pd.MultiIndex.from_product([data.columns,['AAPL']])
        self.assertEqual(len(normalize_stock_data(data, 'AAPL')), 2)
    def test_reversed_multilevel_columns(self):
        data = sample().set_index('Date')
        data.columns = pd.MultiIndex.from_product([['AAPL'],data.columns])
        self.assertEqual(len(normalize_stock_data(data, 'AAPL')), 2)
    def test_missing_field(self):
        with self.assertRaises(ValueError): normalize_stock_data(sample().drop(columns='High'), 'AAPL')
    def test_invalid_numeric(self):
        for value in [float('nan'), float('inf'), -1]:
            with self.subTest(value=value):
                data=sample(); data['Close']=value
                with self.assertRaises(ValueError): normalize_stock_data(data, 'AAPL')
    def test_bad_ranges(self):
        data=sample(); data['Low']=200
        with self.assertRaises(ValueError): normalize_stock_data(data, 'AAPL')
    def test_invalid_volume(self):
        for value in [-1, 1.5, 2**64]:
            data=sample(); data['Volume']=value
            with self.assertRaises(ValueError): normalize_stock_data(data, 'AAPL')
    def test_duplicate_identical(self):
        data=pd.concat([sample(),sample()])
        self.assertEqual(len(normalize_stock_data(data, 'AAPL')),2)
    def test_duplicate_conflict(self):
        data=sample(); other=sample(); other.loc[0,'Close']=101
        with self.assertRaises(ValueError): normalize_stock_data(pd.concat([data,other]), 'AAPL')
    def test_missing_dates(self):
        data=sample(); data.loc[0,'Date']=None
        with self.assertRaises(ValueError): normalize_stock_data(data, 'AAPL')
    def test_empty_rejected(self):
        with self.assertRaises(ValueError): normalize_stock_data(pd.DataFrame(), 'AAPL')
    def test_no_implicit_credentials(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError): create_db_engine()

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.engine=create_engine('sqlite:///:memory:')
        metadata.create_all(self.engine)
    def tearDown(self): self.engine.dispose()
    def test_repeat_run_idempotent_and_updates_corrections(self):
        data=normalize_stock_data(sample(),'AAPL')
        self.assertEqual(insert_stock_data(self.engine,data),2)
        self.assertEqual(insert_stock_data(self.engine,data),2)
        data.loc[0,'close_price']=101
        insert_stock_data(self.engine,data)
        with self.engine.connect() as c:
            self.assertEqual(c.scalar(select(func.count()).select_from(prices)),2)
            self.assertEqual(c.scalar(select(prices.c.close_price).order_by(prices.c.date)),101)
    def test_distinct_symbols_same_date(self):
        data=pd.concat([normalize_stock_data(sample(),'AAPL'),normalize_stock_data(sample(),'MSFT')])
        self.assertEqual(insert_stock_data(self.engine,data),4)
        with self.engine.connect() as c: self.assertEqual(c.scalar(select(func.count()).select_from(prices)),4)
    def test_invalid_data_does_not_write(self):
        data=normalize_stock_data(sample(),'AAPL'); data.loc[1,'volume']=-1
        with self.assertRaises(ValueError): insert_stock_data(self.engine,data)
        with self.engine.connect() as c: self.assertEqual(c.scalar(select(func.count()).select_from(prices)),0)
    def test_postgres_upsert_compiles(self):
        from sqlalchemy.dialects.postgresql import insert, dialect
        stmt=insert(prices).values(symbol='AAPL',date='2024-01-02',open_price=1,high_price=1,low_price=1,close_price=1,volume=1)
        stmt=stmt.on_conflict_do_update(index_elements=['symbol','date'],set_={'close_price':stmt.excluded.close_price})
        self.assertIn('ON CONFLICT (symbol, date) DO UPDATE', str(stmt.compile(dialect=dialect())))

if __name__ == '__main__': unittest.main()
