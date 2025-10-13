import os
from dotenv import load_dotenv

URL_CONNECTION_GRAPH_DB = "bolt://localhost:7687"
USER_GRAPH_DB = "neo4j"
PASSWORD_GRAPH_DB = "test123456"

# Load .env nếu đang chạy local (khi deploy thật thì Aiven / Docker sẽ tự inject env)
load_dotenv()

# Bắt buộc phải có các biến môi trường, nếu thiếu thì raise lỗi
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
