import os

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
)

DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"mysql+aiomysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', '')}@"
    f"{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'ApoiaMaisDB')}"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)