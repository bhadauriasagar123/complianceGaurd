"""Initialize database tables."""

import asyncio

from app.core.database import Base, engine


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized successfully")


if __name__ == "__main__":
    asyncio.run(main())
