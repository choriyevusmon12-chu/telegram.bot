import asyncio
import sqlite3
import re
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from aiogram.client.session.aiohttp import AiohttpSession
# --- SOZLAMALAR (O'zingizniki bilan almashtiring) ---
TOKEN = "7921629828:AAGl8VEGUhZ8Lsrz50emFQcJSUdr5Z-UVdQ"
ADMIN_ID = 5060143317  # O'zingizning ID raqamingizni yozing
CHANNEL_ID = -1003547083967 # Kanalingiz ID-si (-100 bilan boshlanadi)


session = AiohttpSession(proxy="http://proxy.server:3128")

# 2. KEYIN esa botni shu sessiya bilan birga yaratamiz (BU JUDA MUHIM!)
bot = Bot(token=TOKEN, session=session)
dp = Dispatcher()

# --- BAZA BILAN ISHLASH ---
db = sqlite3.connect("kino_baza.db")
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS movies (code TEXT PRIMARY KEY, file_id TEXT, name TEXT)")
db.commit()

def parse_movie_data(text):
    if not text: return None, "Nomsiz kino"
    match = re.search(r'\b\d{3,4}\b', text) # 3 yoki 4 xonali kodlarni ham oladi
    if match:
        code = match.group()
        name = text.replace(code, "").replace("-", "").strip()
        if not name: name = "Nomsiz kino"
        return code, name
    return None, None

# --- BOT BUYRUQLARI ---

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("🎬 Salom! Kino kodini yuboring.")

# 1. RO'YXATNI BO'LIB CHIQARISH (LONG MESSAGE ERROR TUZATILDI)
@dp.message(Command("list"), F.from_user.id == ADMIN_ID)
async def list_movies(message: Message):
    cursor.execute("SELECT code, name FROM movies")
    rows = cursor.fetchall()
    if not rows:
        await message.answer("📭 Bazada kinolar yo'q.")
        return

    text = "📂 Kino ro'yxati:\n\n"
    for row in rows:
        line = f"🔢 `{row[0]}` — 🎬 {row[1]}\n"
        if len(text) + len(line) > 4000:
            await message.answer(text)
            text = ""
        text += line
    await message.answer(text)

# 2. KINONI O'CHIRISH FUNKSIYASI
@dp.message(Command("del"), F.from_user.id == ADMIN_ID)
async def delete_movie(message: Message, command: CommandObject):
    if command.args:
        code = command.args.strip()
        cursor.execute("DELETE FROM movies WHERE code = ?", (code,))
        db.commit()
        await message.answer(f"🗑 Kod {code} bo'yicha kino o'chirildi.")
    else:
        await message.answer("⚠️ O'chirish uchun kodni ham yozing. Masalan: `/del 101`")

# 3. KINO QO'SHISH (FORWARD)
@dp.message(F.video & (F.from_user.id == ADMIN_ID))
async def handle_forward(message: Message):
    code, name = parse_movie_data(message.caption)
    if code:
        cursor.execute("INSERT OR REPLACE INTO movies VALUES (?, ?, ?)", (code, message.video.file_id, name))
        db.commit()
        await message.answer(f"✅ Saqlandi: {code} - {name}")
    else:
        await message.answer("⚠️ Kod topilmadi (3 xonali son yozing).")

# 4. KINONI BERISH
@dp.message(F.text)
async def send_movie(message: Message):
    code = message.text.strip()
    if code.isdigit():
        cursor.execute("SELECT file_id, name FROM movies WHERE code = ?", (code,))
        res = cursor.fetchone()
        if res:
            await message.answer_video(video=res[0], caption=f"🎬 {res[1]}\n🔢 Kodi: {code}")
        else:
            await message.answer("❌ Topilmadi.")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())