import aiosqlite

DATABASE = "src/database/seenit.db"


async def get_db():
    return await aiosqlite.connect(DATABASE)
