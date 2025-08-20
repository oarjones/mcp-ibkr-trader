import sqlalchemy
from sqlalchemy import Column, Integer, String, Float, DateTime, Table

DB_URL = "sqlite:///./trader.db"
engine = sqlalchemy.create_engine(DB_URL)
metadata = sqlalchemy.MetaData()

# Define tables here as per Module 11
realtime_market_data = Table(
    "realtime_market_data",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("symbol", String, nullable=False),
    Column("price", Float, nullable=False),
    Column("timestamp", DateTime, nullable=False),
    Column("order_id", Integer, nullable=True)
)

metadata.create_all(engine)
