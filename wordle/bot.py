import asyncio
import random
import sqlite3
from datetime import datetime
import pytz

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# ================== CONFIG ==================
TOKEN = "8566314962:AAGvae42Q29y2P8SuOQsC1dJYpbaROrN5Y0"
ATTEMPTS = 6
# ============================================

bot = Bot(
    TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

# ================== WORD LIST ==================
def load_words():
    with open("wordlist.txt", "r") as f:
        return [w.strip().lower() for w in f if len(w.strip()) == 5]

WORDS = load_words()

# ================== DATABASE ==================
conn = sqlite3.connect("scores.db")
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS scores (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    points INTEGER,
    last_played TEXT
)
""")
conn.commit()

# ================== GAME STATE ==================
sessions = {}

# ================== WORDLE LOGIC ==================
def check_guess(guess, word):
    result = ["⬜"] * 5
    word_list = list(word)

    # Green
    for i in range(5):
        if guess[i] == word[i]:
            result[i] = "🟩"
            word_list[i] = None

    # Yellow
    for i in range(5):
        if result[i] == "⬜" and guess[i] in word_list:
            result[i] = "🟨"
            word_list[word_list.index(guess[i])] = None

    return result

def format_board(history):
    board = ""
    for guess, fb in history:
        tiles = "|" + "|".join(fb) + "|\n"
        letters = "| " + " | ".join(guess.upper()) + " |\n"
        board += tiles + letters + "\n"
    return board

def get_random_word():
    return random.choice(WORDS)

# ================== SCORE ==================
def save_score(user_id, username, points):
    today = datetime.utcnow().date().isoformat()
    c.execute("SELECT last_played FROM scores WHERE user_id=?", (user_id,))
    row = c.fetchone()

    if row and row[0] == today:
        return False

    c.execute("""
    INSERT OR REPLACE INTO scores (user_id, username, points, last_played)
    VALUES (
        ?, ?, 
        COALESCE((SELECT points FROM scores WHERE user_id=?), 0) + ?, 
        ?
    )
    """, (user_id, username, user_id, points, today))
    conn.commit()
    return True

# ================== WORDLE COMMAND ==================
@dp.message(Command("wordle"))
async def wordle(msg: types.Message):
    if msg.chat.type == "private":
        await msg.reply("❌ This game works only in groups.")
        return

    user_id = msg.from_user.id
    username = msg.from_user.username or msg.from_user.first_name
    parts = msg.text.split()

    # START GAME
    if len(parts) == 1:
        if user_id in sessions:
            await msg.reply("⚠️ You already have an active game today.")
            return

        sessions[user_id] = {
            "word": get_random_word(),
            "history": [],
            "attempts": 0
        }

        await msg.reply("🎮 Wordle started!\nGuess with:\n/wordle apple")
        return

    # GUESS
    if user_id not in sessions:
        await msg.reply("Start a game first using /wordle")
        return

    guess = parts[1].lower()

    if guess not in WORDS:
        await msg.reply("❌ Invalid 5-letter word.")
        return

    session = sessions[user_id]
    session["attempts"] += 1

    feedback = check_guess(guess, session["word"])
    session["history"].append((guess, feedback))

    attempts_left = ATTEMPTS - session["attempts"]
    board = format_board(session["history"])

    # WIN
    if guess == session["word"]:
        save_score(user_id, username, session["attempts"])
        del sessions[user_id]
        await msg.reply(f"🎉 @{username} WINS!\n\n{board}")
        return

    # LOSE
    if session["attempts"] >= ATTEMPTS:
        save_score(user_id, username, 10)
        answer = session["word"].upper()
        del sessions[user_id]
        await msg.reply(f"💀 Game Over!\nWord was: {answer}\n\n{board}")
        return

    # CONTINUE
    await msg.reply(
        f"👤 @{username}\n\n{board}Attempts left: {attempts_left}"
    )

# ================== LEADERBOARD ==================
@dp.message(Command("leaderboard"))
async def leaderboard(msg: types.Message):
    c.execute("SELECT username, points FROM scores ORDER BY points ASC LIMIT 10")
    rows = c.fetchall()

    if not rows:
        await msg.reply("No scores yet.")
        return

    text = "🏆 WEEKLY LEADERBOARD\n(Lower points = better)\n\n"
    for i, (name, pts) in enumerate(rows, 1):
        text += f"{i}. {name} — {pts} pts\n"

    await msg.reply(text)

# ================== WEEKLY RESET ==================
async def weekly_reset():
    c.execute("DELETE FROM scores")
    conn.commit()

scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/London"))
scheduler.add_job(weekly_reset, trigger="cron", day_of_week="sun", hour=0)

# ================== START BOT ==================
async def main():
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
