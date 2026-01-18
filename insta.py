import asyncio
import sqlite3
import re
import logging
import warnings
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.session.aiohttp import AiohttpSession

# 1. Barcha keraksiz ogohlantirishlarni o'chiramiz
warnings.filterwarnings("ignore", category=UserWarning)

# --- SOZLAMALAR ---
TOKEN = "7921629828:AAGl8VEGUhZ8Lsrz50emFQcJSUdr5Z-UVdQ"
ADMIN_ID = 5060143317  # O'z ID-ngizni kiriting

# Kanallar ro'yxati (Yopiq kanal ID-si va ochiq kanal yuzernami)
CHANNELS = [-1003547083967, "@CodeBridge_IT_Akademy"]

# Foydalanuvchi bosishi uchun linklar
LINK1 = "https://t.me/+K1TaHbJsTvA2NGEy"
LINK2 = "https://t.me/CodeBridge_IT_Akademy"
INSTA_URL = "https://instagram.com/profil_nomi"

# --- PROXY (PythonAnywhere Free uchun shart) ---
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect("kino_baza.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS movies (code TEXT PRIMARY KEY, file_id TEXT, name TEXT)")
    conn.commit()
    return conn, cur

db_conn, cursor = init_db()

# --- PROFESSIONAL OBUNA TEKSHIRUVI ---
async def check_subs(user_id):
    if user_id == ADMIN_ID:
        return True
    for channel in CHANNELS:
        try:
            chat_member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if chat_member.status in ["left", "kicked"]:
                return False
        except Exception:
            # Agar bot admin bo'lmasa yoki kanal topilmasa
            return False
    return True

def sub_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1-kanalga a'zo bo'lish", url=LINK1)],
        [InlineKeyboardButton(text="2-kanalga a'zo bo'lish", url=LINK2)],
        [InlineKeyboardButton(text="Instagram", url=INSTA_URL)],
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="check")]
    ])

# --- HANDLERLAR ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    if await check_subs(message.from_user.id):
        await message.answer(f"👋 Salom {message.from_user.first_name}!\n🎬 Kino kodini kiriting:")
    else:
        await message.answer("⚠️ Botdan foydalanish uchun kanallarga a'zo bo'ling:", reply_markup=sub_kb())

@dp.callback_query(F.data == "check")
async def process_check(call: CallbackQuery):
    if await check_subs(call.from_user.id):
        await call.message.delete()
        await call.message.answer("✅ Rahmat! Endi kino kodini yuboring.")
    else:
        await call.answer("❌ Hali obuna bo'lmagansiz!", show_alert=True)

# --- ADMIN FUNKSIYALARI ---

@dp.message(Command("list"), F.from_user.id == ADMIN_ID)
async def cmd_list(message: Message):
    cursor.execute("SELECT code, name FROM movies")
    data = cursor.fetchall()
    if not data:
        return await message.answer("Baza bo'sh.")

    text = "📂 Barcha kinolar:\n\n" + "\n".join([f"🔢 {r[0]} | {r[1]}" for r in data])
    if len(text) > 4096:
        file = BufferedInputFile(bytes(text, 'utf-8'), filename="kinolar.txt")
        await message.answer_document(document=file)
    else:
        await message.answer(text)

@dp.message(Command("del"), F.from_user.id == ADMIN_ID)
async def cmd_del(message: Message, command: CommandObject):
    if command.args:
        cursor.execute("DELETE FROM movies WHERE code = ?", (command.args.strip(),))
        db_conn.commit()
        await message.answer(f"🗑 Kod {command.args} o'chirildi.")

@dp.message(F.video & (F.from_user.id == ADMIN_ID))
async def add_video(message: Message):
    caption = message.caption or ""
    code_match = re.search(r'\b\d{3,6}\b', caption)
    if code_match:
        code = code_match.group()
        name = caption.replace(code, "").strip() or "Nomsiz kino"
        cursor.execute("INSERT OR REPLACE INTO movies VALUES (?, ?, ?)", (code, message.video.file_id, name))
        db_conn.commit()
        await message.answer(f"✅ Kino bazaga qo'shildi!\n🔢 Kod: {code}\n🎬 Nomi: {name}")
    else:
        await message.answer("❌ Xato! Video tagiga 3-6 xonali sonli kod yozing.")

# --- QIDIRUV ---

@dp.message(F.text)
async def search_movie(message: Message):
    if not await check_subs(message.from_user.id):
        return await message.answer("⚠️ Avval obuna bo'ling!", reply_markup=sub_kb())

    if message.text.isdigit():
        cursor.execute("SELECT file_id, name FROM movies WHERE code = ?", (message.text.strip(),))
        res = cursor.fetchone()
        if res:
            await message.answer_video(video=res[0], caption=f"🎬 {res[1]}\n🔢 Kodi: {message.text}")
        else:
            await message.answer("😔 Kechirasiz, bu kod bilan kino topilmadi.")

# --- ISHGA TUSHIRISH ---
async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    print("🚀 Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi")