import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
import google.generativeai as genai

# Loglarni sozlash (Serverda bot ishini kuzatish uchun)
logging.basicConfig(level=logging.INFO)

# Server muhitidan maxfiy kalitlarni olish
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

# MAXFIY KALIT SO'Z (Buni o'zingiz xohlagan so'zga o'zgartirishingiz mumkin)
SECRET_ADMIN_KEY = "Alibek_Boss"

# Google Gemini AI modelini sozlash
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    system_instruction=(
        "Siz O'zbekistondagi o'quvchilarga xalqaro va mahalliy universitetlarni topishda "
        "yordam beradigan professional, samimiy va tajribali AI Akademik Maslahatchisiz. "
        "Foydalanuvchilar (o'quvchilar) sizga o'z qiziqishlari, IELTS/Topik ballari, GPA (baho), "
        "moliyaviy holati (grant yoki kontrakt xohishi) va o'qimoqchi bo'lgan davlatlarini aytishadi. "
        "Siz har bir talabaga individual yondashib, unga mos keladigan TOP-3 ta universitet, "
        "ularning talablari va mavjud grant dasturlari haqida aniq va tushunarli ma'lumot berasiz. "
        "Har doim o'quvchini ruhan qo'llab-quvvatlang va unga motivatsiya bering."
    )
)

# Aiogram 3.x uchun asosiy obyektlar
bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Suhbat tarixini foydalanuvchi IDsi bo'yicha saqlash uchun lug'at
chat_sessions = {}

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    chat_sessions[user_id] = model.start_chat(history=[])
    
    welcome_text = (
        f"Assalomu alaykum, {message.from_user.full_name}! 🎓\n\n"
        "Men sizning shaxsiy akademik maslahatchi AI Assistantingizman. "
        "Sizga kelajagingiz uchun eng mos keladigan universitet va grantlarni topishda yordam beraman.\n\n"
        "Menga o'zingiz haqingizda quyidagi ma'lumotlarni yuboring:\n"
        "• Qiziqqan yo'nalishingiz (IT, Biznes, Tibbiyot...)\n"
        "• Til sertifikatlaringiz (IELTS, CEFR, TOPIK...)\n"
        "• Qaysi davlat yoki qit'ada o'qishni reja qilyapsiz?\n\n"
        "O'z qiziqishlaringizni erkin yozing, men sizga eng zo'r variantlarni tahlil qilib beraman!"
    )
    await message.reply(welcome_text)

@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    user_id = message.from_user.id
    chat_sessions[user_id] = model.start_chat(history=[])
    await message.reply("🔄 Suhbat tarixi tozalandi. Yangitdan ma'lumot berishingiz mumkin.")

@dp.message()
async def handle_ai_message(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text

    # 🔑 MAXFIY KALIT SO'Z TEKSHIRUVI (Sizni tanib olish funksiyasi)
    if user_text == SECRET_ADMIN_KEY:
        admin_welcome = (
            f"👑 Salom, Alibek! Tizim sizni muvaffaqiyatli tanidi.\n\n"
            f"Siz ushbu AI botning asoschisi va loyiha rahbarisiz. "
            f"Hozirda serverlar ideal holatda ishlamoqda, AI modeli (Gemini 1.5 Flash) aloqada. "
            f"Omad tilayman, Boss!"
        )
        await message.reply(admin_welcome)
        return  # AI ga yubormasdan jarayonni shu yerda to'xtatamiz

    # Agar oddiy foydalanuvchi yozsa, AI ishga tushadi
    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat(history=[])

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        chat = chat_sessions[user_id]
        response = chat.send_message(user_text)
        await message.reply(response.text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Xatolik yuz berdi: {e}")
        await message.reply(
            "Kechirasiz, hozirda so'rovlar soni ko'payganligi sababli tizimda biroz uzilish bo'ldi. "
            "Iltimos, bir necha soniyadan so'ng qayta urinib ko'ring."
        )

async def main():
    logging.info("Bot muvaffaqiyatli ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
