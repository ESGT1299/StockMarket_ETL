import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine, exc
import logging

# ---------------------- Setup Logging ----------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ---------------------- Database Configuration ----------------------
DB_CONFIG = {
    "username": "postgres",
    "password": "gg",  # ⚠️ Store securely in an environment variable in production!
    "host": "localhost",
    "port": "5432",
    "database": "finance_db"
}

# Create a database connection
def create_db_engine():
    """
    Creates and returns a SQLAlchemy database engine.
    """
    try:
        engine = create_engine(f"postgresql://{DB_CONFIG['username']}:{DB_CONFIG['password']}@"
                               f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
        logging.info("✅ Database connection established successfully.")
        return engine
    except exc.SQLAlchemyError as e:
        logging.error(f"❌ Error connecting to database: {e}")
        return None

# ---------------------- Data Extraction ----------------------
def fetch_stock_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetches historical stock data from Yahoo Finance for the given ticker and date range.
    
    :param ticker: Stock symbol (e.g., "AAPL")
    :param start_date: Start date (YYYY-MM-DD)
    :param end_date: End date (YYYY-MM-DD)
    :return: Pandas DataFrame with formatted stock data
    """
    try:
        stock_data = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False)

        if stock_data.empty:
            logging.warning(f"⚠️ No stock data retrieved for {ticker}. Check the ticker symbol or date range.")
            return None

        # Flatten MultiIndex columns if needed
        if isinstance(stock_data.columns, pd.MultiIndex):
            stock_data.columns = ['_'.join(col).strip() for col in stock_data.columns]

        logging.info(f"📊 Stock data retrieved for {ticker}. Columns: {list(stock_data.columns)}")

        stock_data.reset_index(inplace=True)

        # ✅ Dynamically rename columns to match PostgreSQL schema
        column_mapping = {
            f"Open_{ticker}": "open_price",
            f"High_{ticker}": "high_price",
            f"Low_{ticker}": "low_price",
            f"Close_{ticker}": "close_price",
            f"Volume_{ticker}": "volume",
            "Date": "date"
        }

        # ✅ Ensure column names are correctly renamed
        stock_data.rename(columns={k: v for k, v in column_mapping.items() if k in stock_data.columns}, inplace=True)

        # ✅ Ensure the 'symbol' column is added
        stock_data["symbol"] = ticker  

        # ✅ Select only necessary columns
        selected_columns = ["symbol", "date", "open_price", "high_price", "low_price", "close_price", "volume"]
        stock_data = stock_data[[col for col in selected_columns if col in stock_data.columns]]

        # ✅ Convert column names to lowercase
        stock_data.columns = [col.lower().strip() for col in stock_data.columns]

        return stock_data
    except Exception as e:
        logging.error(f"❌ Error fetching stock data for {ticker}: {e}")
        return None

# ---------------------- Data Insertion (Avoid Duplicates) ----------------------
from sqlalchemy.sql import text  # ✅ Import text function

def get_existing_dates(engine, ticker: str):
    """
    Retrieves existing dates for a given ticker from the database to prevent duplicate entries.
    
    :param engine: SQLAlchemy database engine
    :param ticker: Stock symbol
    :return: Set of existing dates in the database
    """
    query = text("SELECT date FROM stock_data WHERE symbol = :symbol")  # ✅ Use parameterized query
    try:
        with engine.connect() as connection:
            result = connection.execute(query, {"symbol": ticker})  # ✅ Properly execute with parameters
            existing_dates = {row[0] for row in result.fetchall()}  # ✅ Fetch results properly
            logging.info(f"📅 Retrieved {len(existing_dates)} existing dates for {ticker}.")
            return existing_dates
    except exc.SQLAlchemyError as e:
        logging.error(f"❌ Error retrieving existing dates from database: {e}")
        return set()

def insert_stock_data(engine, stock_data: pd.DataFrame):
    """
    Inserts stock data into the PostgreSQL database while avoiding duplicate entries.
    
    :param engine: SQLAlchemy database engine
    :param stock_data: DataFrame containing stock data to be inserted
    """
    if stock_data is None or stock_data.empty:
        logging.warning("⚠️ No new data to insert.")
        return

    ticker = stock_data["symbol"].iloc[0]
    existing_dates = get_existing_dates(engine, ticker)

    # Remove already existing dates before inserting new data
    stock_data["date"] = pd.to_datetime(stock_data["date"])  # Ensure correct dtype
    stock_data = stock_data[~stock_data["date"].isin(pd.to_datetime(list(existing_dates)))]


    if stock_data.empty:
        logging.info(f"⚠️ No new stock data to insert for {ticker}. All dates already exist.")
        return

    try:
        stock_data.to_sql("stock_data", engine, if_exists="append", index=False, method="multi")
        logging.info(f"✅ {len(stock_data)} new records inserted into database for {ticker}.")
    except exc.SQLAlchemyError as db_error:
        logging.error(f"❌ Error inserting data into database: {db_error}")

# ---------------------- Main Execution ----------------------
if __name__ == "__main__":
    engine = create_db_engine()
    if engine is not None:
        ticker = "BTC-USD"
        start_date = "2024-01-01"
        end_date = "2024-02-21"

        stock_data = fetch_stock_data(ticker, start_date, end_date)
        insert_stock_data(engine, stock_data)
