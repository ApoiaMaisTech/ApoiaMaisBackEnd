import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"mysql+aiomysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', '')}@"
    f"{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/"
    f"{os.getenv('DB_NAME', 'ApoiaMaisDB')}"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    poolclass=NullPool,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)