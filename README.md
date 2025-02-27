# StockMarket_ETL

# 📊 Stock Market ETL Pipeline

## 🚀 Overview
This project is an **ETL (Extract, Transform, Load) pipeline** that retrieves stock market data from **Yahoo Finance**, processes it using **Pandas**, and loads it into a **PostgreSQL database**.

The goal is to **automate stock data collection**, avoid duplicate entries, and store historical financial data for further analysis.

---

## 🔥 Technologies Used
✅ **Python** (Data Extraction, Transformation)  
✅ **Yahoo Finance API** (Stock Data Source)  
✅ **Pandas** (Data Processing)  
✅ **PostgreSQL** (Database for Storage)  
✅ **SQLAlchemy** (Python to SQL Interface)  
✅ **Git & GitHub** (Version Control & Collaboration)  
✅ **Logging** (Monitoring & Debugging)

---

## 📂 Project Structure
📁 finance_project/ 
├── etl_pipeline.py # Main ETL script 
├── requirements.txt # Python dependencies 
├── README.md # Project documentation 
├── stock_data.sql # Sample SQL queries 
├── config.py # Database credentials (hidden in .gitignore) 
├── .gitignore # Ignore unnecessary files


---

## 📌 Features
✅ **Extracts stock data from Yahoo Finance**  
✅ **Prevents duplicate entries using SQL**  
✅ **Stores data securely in PostgreSQL**  
✅ **Automated logging for debugging**  

---

## 📊 Data Model (Database Schema)
This project stores stock data in **PostgreSQL**, following this schema:

| Column        | Data Type  | Description                          |
|--------------|------------|--------------------------------------|
| `id`        | SERIAL (PK) | Unique record identifier            |
| `symbol`    | VARCHAR     | Stock ticker symbol (e.g., AAPL)    |
| `date`      | DATE        | Trading date                        |
| `open_price` | FLOAT      | Opening price of the stock          |
| `high_price` | FLOAT      | Highest price of the day            |
| `low_price`  | FLOAT      | Lowest price of the day             |
| `close_price`| FLOAT      | Closing price of the stock          |
| `volume`    | BIGINT      | Total shares traded                 |

---

## 🚀 How to Run the Project

### **1️⃣ Clone the Repository**
```sh
git clone https://github.com/ESGT1299/StockMarket_ETL
cd StockMarket_ETL
```

### **2️⃣ Install Dependencies**
```sh
pip install -r requirements.txt
```

### **3️⃣ Set Up PostgreSQL Database**
Ensure PostgreSQL is installed and running.
Create the database manually:   
```sh
CREATE DATABASE finance_db;
``` 
Create the stock_data table:
```sh
CREATE DATABASE finance_db;
Create the stock_data table:
sql
Copiar
CREATE TABLE stock_data (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    date DATE NOT NULL,
    open_price FLOAT,
    high_price FLOAT,
    low_price FLOAT,
    close_price FLOAT,
    volume BIGINT
);
```
### **4️⃣ Run the ETL Pipeline**
```sh
python etl_pipeline.py
```

### **🔮 Future Improvements**
✅ Deploy the ETL pipeline on AWS Lambda or Google Cloud
✅ Build a Tableau Dashboard for stock price trends
✅ Implement machine learning to predict stock prices

### **📢 Author & Contact**
📌 Author: Erick Guagua
📧 Email: erick.guagua@yachaytech.edu.ec
🔗 LinkedIn: [Your LinkedIn Profile](https://www.linkedin.com/in/erick-guagua-14b143214/)
