import os
from dotenv import load_dotenv

# Config

load_dotenv()

BASE_URL = "https://www.imdb.com"
START_URL = "https://www.imdb.com/chart/top/?ref_=nv_mv_250"
DELAY = 2
MAX_PAGES = 10 

# Database Config
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER') 
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')