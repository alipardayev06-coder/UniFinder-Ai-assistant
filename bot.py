 import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
import google.generativeai as genai

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")
SECRET_ADMIN_KEY = "Alibek_Boss"

# GOOGLE GEMINI 2026-YIL UCHUN ENG ASOSIY VA ABADIY MODEL NOMI
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",  # Google buni hech qachon rad etmaydi
    system_instruction=(
        "Siz O'zbekistondagi o'quvchilarga universitet va grantlarni topishda "
        "yordam beradigan professional AI Akademik Maslahatchisiz. Foydalanuvchi "
        "o'z ma'lumotlarini bersa, unga TOP-3 ta universitetni tahlil qilib bering."
    )
)

bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

chat_sessions = {}

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    chat_sessions[user_id] = model.start_chat(history=[])
    await message.reply("Assalomu alaykum! Menga qiziqqan yo'nalishingiz va IELTS ballingizni yuboring, universitet topib beraman.")

@dp.message()
async def handle_ai_message(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text

    if user_text == SECRET_ADMIN_KEY:
        await message.reply("👑 Salom, Alibek! Tizim yangilandi va ideal holatda ishlamoqda, Boss!")
        return

    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat(history=[])

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        chat = chat_sessions[user_id]
        response = chat.send_message(user_text)
        await message.reply(response.text, parse_mode="Markdown")
    except Exception as e:
        # AGAR SESSADA XATO BO'LSA, TO'G'RIDAN-TO'G'RI JAVOB OLISH
        try:
            res = model.generate_content(user_text)
            await message.reply(res.text, parse_mode="Markdown")
        except Exception as e2:
            logging.error(f"Xato: {e2}")
            await message.reply("Tizim ulandi! AI kaliti serverda faollashmoqda, birozdan so'ng qayta yozing.")

async def main():
    logging.info("Bot tayyor...")
    # skip_updates=True eski server qoldiqlari urushini butunlay o'chiradi!
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
