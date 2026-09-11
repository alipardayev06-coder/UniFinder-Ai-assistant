import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
import google.generativeai as genai

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_KEY")

SECRET_ADMIN_KEY = "Alibek_Boss"

# GOOGLE AI TIZIMINI YANGI MODELGA YO'NALTIRAMIZ
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel(
    model_name="gemini-3.6-flash",  # Eng so'nggi va xatosiz ishlaydigan model nomi
    system_instruction=(
        "Siz O'zbekistondagi o'quvchilarga xalqaro va mahalliy universitetlarni topishda "
        "yordam beradigan professional, samimiy va tajribali AI Akademik Maslahatchisiz. "
        "Foydalanuvchilar (o'quvchilar) sizga o'z qiziqishlari, IELTS/Topik ballari, GPA (baho), "
        "moliyaviy holati (grant yoki kontrakt xohishi) va o'qimoqchi bo'lgan davlatlarini aytishadi. "
        "Siz har bir talabaga individual yondashib, unga mos keladigan TOP-3 ta universitet, "
        "ularning talablari va grant dasturlari haqida aniq ma'lumot berasiz."
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
    
    welcome_text = (
        f"Assalomu alaykum, {message.from_user.full_name}! 🎓\n\n"
        "Men sizning shaxsiy akademik maslahatchi AI Assistantingizman. "
        "Sizga kelajagingiz uchun eng mos keladigan universitet va grantlarni topishda yordam beraman.\n\n"
        "Menga o'zingiz haqingizda quyidagi ma'lumotlarni yuboring:\n"
        "• Qiziqqan yo'nalishingiz (IT, Biznes, Tibbiyot...)\n"
        "• Til sertifikatlaringiz (IELTS, CEFR, TOPIK...)\n"
        "• Qaysi davlat yoki qit'ada o'qishni reja qilyapsiz?\n\n"
        "Erkin yozing, men sizga eng zo'r variantlarni tahlil qilib beraman!"
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

    if user_text == SECRET_ADMIN_KEY:
        admin_welcome = (
            f"👑 Salom, Alibek! Tizim sizni muvaffaqiyatli tanidi.\n\n"
            f"Siz ushbu AI botning asoschisi va loyiha rahbarisiz. "
            f"Tizimlar to'liq yangilandi va ideal holatda ishlamoqda, Boss!"
        )
        await message.reply(admin_welcome)
        return

    if user_id not in chat_sessions:
        chat_sessions[user_id] = model.start_chat(history=[])

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        chat = chat_sessions[user_id]
        response = chat.send_message(user_text)
        await message.reply(response.text, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await message.reply(
            "Kechirasiz, hozirda Google tizimida yangilanish bo'lmoqda. "
            "Iltimos, bir necha soniyadan so'ng qayta urinib ko'ring."
        )

async def main():
    logging.info("Bot ishga tushmoqda...")
    # skip_updates=True orqali boyagi eski serverdagi ziddiyatli xabarlarni tozalab tashlaymiz
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
