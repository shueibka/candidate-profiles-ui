from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///recruitment.db"

engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)

def get_session():
    return Session()

def get_engine():
    return engine
