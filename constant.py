import os
from dotenv import load_dotenv

# Load .env nếu đang chạy local (khi deploy thật thì Aiven / Docker sẽ tự inject env)
load_dotenv()
URL_CONNECTION_GRAPH_DB = os.environ["URL_CONNECTION_GRAPH_DB"]
USER_GRAPH_DB = os.environ["USER_GRAPH_DB"]
PASSWORD_GRAPH_DB = os.environ["PASSWORD_GRAPH_DB"]

MYSQL_HOST = os.environ["MYSQL_HOST"]
MYSQL_PORT = int(os.environ["MYSQL_PORT"])
MYSQL_USERNAME = os.environ["MYSQL_USERNAME"]
MYSQL_PASSWORD = os.environ["MYSQL_PASSWORD"]
MYSQL_DATABASE = os.environ["MYSQL_DATABASE"]

# Kết nối SQLAlchemy
DATABASE_URL = (
    f"mysql+pymysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}"
    f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
)
