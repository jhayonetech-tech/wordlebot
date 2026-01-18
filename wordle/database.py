import aiosqlite
import json
from datetime import date

DB = "wordle.db"


async def init():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS games(
            user_id INTEGER,
            username TEXT,
            word TEXT,
            guesses TEXT,
            attempts INTEGER,
            game_date TEXT,
            finished INTEGER
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS leaderboard(
            user_id INTEGER,
            username TEXT,
            points INTEGER
        )
        """)
        await db.commit()


async def today_game(uid):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT * FROM games WHERE user_id=? AND game_date=?", (uid, str(date.today())))
        return await cur.fetchone()


async def new_game(uid, username, word):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO games VALUES (?, ?, ?, ?, ?, ?, ?)", (uid, username, word, json.dumps([]), 5, str(date.today()), 0))
        await db.commit()


async def update(uid, guesses, attempts, finished):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE games SET guesses=?, attempts=?, finished=? WHERE user_id=? AND game_date=?", (json.dumps(guesses), attempts, finished, uid, str(date.today())))
        await db.commit()


async def score(uid, username, pts):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT points FROM leaderboard WHERE user_id=?", (uid,))
        row = await cur.fetchone()
        if row:
            await db.execute("UPDATE leaderboard SET points=points+? WHERE user_id=?", (pts, uid))
        else:
            await db.execute("INSERT INTO leaderboard VALUES (?, ?, ?)", (uid, username, pts))
        await db.commit()


async def get_board():
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT username, points FROM leaderboard ORDER BY points ASC")
        return await cur.fetchall()


async def reset_board():
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM leaderboard")
        await db.commit()
