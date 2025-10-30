from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from constant import MYSQL_HOST, MYSQL_PASSWORD, MYSQL_USERNAME, MYSQL_PORT, MYSQL_DATABASE
from models.models import Base
from typing import Optional
import logging

class DatabaseManager:
    """Quản lý kết nối và session với MySQL database"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        self._setup_database()
    
    def _setup_database(self):
        """Thiết lập engine và session factory"""
        try:
            self.engine = create_engine(
                self.database_url,
                echo=False,  # Set True để debug SQL queries
                pool_pre_ping=True,  # Kiểm tra connection trước khi sử dụng
                pool_recycle=3600    # Recycle connection sau 1 giờ
            )
            self.SessionLocal = sessionmaker(
                bind=self.engine, 
                expire_on_commit=False  # Prevent objects from being detached after commit
            )
            logging.info("✅ Database engine created successfully")
        except SQLAlchemyError as e:
            logging.error(f"❌ Failed to create database engine: {e}")
            raise
    
    def create_tables(self):
        """Tạo tất cả bảng trong database"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logging.info("✅ All tables created successfully")
        except SQLAlchemyError as e:
            logging.error(f"❌ Failed to create tables: {e}")
            raise
    
    def get_session(self) -> Session:
        """Lấy database session mới"""
        return self.SessionLocal()
    
    def test_connection(self) -> bool:
        """Test kết nối database"""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            logging.info("✅ Database connection test successful")
            return True
        except SQLAlchemyError as e:
            logging.error(f"❌ Database connection test failed: {e}")
            return False

class DatabaseConfig:
    """Cấu hình database"""
    
    @staticmethod
    def get_database_url(
        username: str = MYSQL_USERNAME,
        password: str = MYSQL_PASSWORD,
        host: str = MYSQL_HOST,
        port: int = MYSQL_PORT,
        database: str = MYSQL_DATABASE
    ) -> str:
        """Tạo database URL cho MySQL"""
        return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
    
    @staticmethod
    def get_default_config() -> dict:
        """Cấu hình mặc định"""
        return {
            "username": MYSQL_USERNAME,
            "password": MYSQL_PASSWORD,
            "host": MYSQL_HOST, 
            "port": MYSQL_PORT,
            "database": MYSQL_DATABASE
        }

# Singleton pattern cho database manager
_db_manager: Optional[DatabaseManager] = None

def get_database_manager(database_url: str = None) -> DatabaseManager:
    """Lấy instance của DatabaseManager (singleton)"""
    global _db_manager
    
    if _db_manager is None:
        if database_url is None:
            # Sử dụng cấu hình mặc định
            config = DatabaseConfig.get_default_config()
            database_url = DatabaseConfig.get_database_url(**config)
        
        _db_manager = DatabaseManager(database_url)
    
    return _db_manager

def init_database(database_url: str = None):
    """Khởi tạo database và tạo tables"""
    db_manager = get_database_manager(database_url)
    db_manager.create_tables()
    return db_manager

# Context manager cho database session
class DatabaseSession:
    """Context manager cho database session với auto-commit/rollback"""
    
    def __init__(self, db_manager: DatabaseManager = None):
        self.db_manager = db_manager or get_database_manager()
        self.session = None
    
    def __enter__(self) -> Session:
        self.session = self.db_manager.get_session()
        return self.session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.session.rollback()
            logging.error(f"Database transaction rolled back due to error: {exc_val}")
        else:
            try:
                self.session.commit()
            except SQLAlchemyError as e:
                self.session.rollback()
                logging.error(f"Failed to commit transaction: {e}")
                raise
        self.session.close()