

@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()