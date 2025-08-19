import sqlalchemy

DB_URL = "sqlite:///./trader.db"
engine = sqlalchemy.create_engine(DB_URL)
metadata = sqlalchemy.MetaData()

# Define tables here as per Module 11
