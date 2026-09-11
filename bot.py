import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
import google.generativeai as genai

# Tizim loglarini sozlash
logging.basicConfig(level=logging.INFO)

# Tokenlarni Render serveridan olish
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Eng so'nggi yangilangan Gemini API sozlamasi
genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = (
    "Siz O'zbekistondagi talabalar va o'quvchilarga xalqaro hamda mahalliy universitetlarni, "
    "shuningdek, grant dasturlarini topishda yordam beradigan professional AI Akademik Maslahatchisiz. "
    "Foydalanuvchilar sizga o'z qiziqishlari, IELTS ballari, GPA ko'rsatkichlari va moliyaviy holatini aytishadi. "
    "Siz ularga mos keladigan TOP universitetlar va grantlarni (masalan: Stipendium Hungaricum, GKS va boshqalar) "
    "tavsiya qilasiz. Matnni juda chiroyli va tartibli formatlang, muhim so'zlarni qalin (bold) qiling. "
    "O'quvchilarga doim samimiy va motivatsiya beruvchi ohangda javob qaytaring."
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_chats = {}

def get_user_chat(user_id: int):
    if user_id not in user_chats:
        # Eng yangi va bepul 'gemini-2.5-flash' modelidan foydalanamiz
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction=SYSTEM_PROMPT
        )
        user_chats[user_id] = model.start_chat(history=[])
    return user_chats[user_id]

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_chats:
        del user_chats[user_id]
        
    welcome_text = (
        f"Assalomu alaykum, {message.from_user.first_name}! 🎓\n\n"
        "Men sizning shaxsiy akademik AI Assistantingizman. "
        "Sizga eng mos keladigan universitet va grantlarni topishda yordam beraman.\n\n"
        "Menga o'zingiz haqingizda erkin shaklda yozing:\n"
        "• Qiziqqan yo'nalishingiz (IT, Biznes...)\n"
        "• Til sertifikatingiz (IELTS...)\n"
        "• Baholaringiz (GPA)\n"
        "• Qaysi davlatda o'qishni xohlaysiz?\n\n"
        "Men hammasini tahlil qilib, sizga eng zo'r variantlarni chiqarib beraman! 🚀"
    )
    await message.answer(welcome_text)

@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_chats:
        del user_chats[user_id]
    await message.answer("Suhbatimiz tarixi tozalandi. Yangidan ma'lumot kiritishingiz mumkin! 🔄")

@dp.message()
async def handle_ai_response(message: types.Message):
    user_id = message.from_user.id
    user_message = message.text
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        chat_session = get_user_chat(user_id)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, chat_session.send_message, user_message)
        await message.answer(response.text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await message.answer("Kechirasiz, so'rovingizni qayta ishlashda xatolik bo'ldi. Iltimos qaytadan yozib ko'ring.")

async def main():
    print("Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
