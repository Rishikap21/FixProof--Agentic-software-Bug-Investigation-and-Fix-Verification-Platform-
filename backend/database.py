import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, URL
from sqlalchemy.orm import sessionmaker, declarative_base
load_dotenv(Path(__file__).resolve().parents[1] / '.env')
url = os.getenv('DATABASE_URL')
if not url:
    if not os.getenv('DB_USER') or not os.getenv('DB_NAME'):
        raise RuntimeError('Set DB_USER and DB_NAME in .env, or explicitly configure DATABASE_URL.')
    url = URL.create('mysql+pymysql', username=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'), host=os.getenv('DB_HOST','localhost'), port=int(os.getenv('DB_PORT','3306')), database=os.getenv('DB_NAME'))
engine = create_engine(url, pool_pre_ping=True, connect_args={'check_same_thread':False} if str(url).startswith('sqlite') else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
def get_db():
    with SessionLocal() as db:
        yield db
