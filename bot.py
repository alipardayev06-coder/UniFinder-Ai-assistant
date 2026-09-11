import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
import google.generativeai as genai
from aiohttp import web

# Loglarni serverda kuzatish uchun yuqori darajada sozlash
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Kalitlarni FAOLAT Render panelidan o'qiydi (Kod ichida maxfiy ma'lumot yo'q)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
SECRET_ADMIN_KEY = "Alibek_Boss"

# Google Gemini AI xavfsiz sozlamalari
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    system_instruction=(
        "Siz O'zbekistondagi o'quvchilarga xalqaro va mahalliy universitetlarni topishda "
        "yordam beradigan professional, o'ta samimiy va tajribali AI Akademik Maslahatchisiz. "
        "Foydalanuvchilar (o'quvchilar) sizga o'z qiziqishlari, IELTS/Topik ballari, GPA (baho), "
        "moliyaviy holati (grant yoki kontrakt xohishi) va o'qimoqchi bo'lgan davlatlarini aytishadi. "
        "Siz har bir talabaga individual yondashib, unga mos keladigan TOP-3 ta universitet, "
        "ularning aniq talablari va mavjud global grant dasturlari (masalan: GKS, Stipendium Hungaricum, "
        "Chevening, turli universitet ichki grantlari) haqida aniq, tushunarli va dalillar bilan ma'lumot berasiz. "
        "Javob bera turib matnni juda chiroyli formatlang: muhim nomlarni qalin (bold) qiling, "
        "ro'yxatlarni nuqtalar bilan tartibli chiqaring. Har doim o'quvchini ruhan qo'llab-quvvatlang va motivatsiya bering."
    )
)

# Aiogram 3 xotira arxitekturasi
storage = MemoryStorage()
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(storage=storage)

# Suhbat tarixini eslab qolish uchun lug'at
chat_sessions = {}

# Render Port xatoligini oldini olish uchun veb-server funksiyasi
async def dummy_web_server():
    app = web.Application()
    app.router.add_get('/', lambda request: web.Response(text="Bot muvaffaqiyatli ishlamoqda!"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Render veb-serveri {port}-portda ishga tushdi.")

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    chat_sessions[user_id] = model.start_chat(history=[])
    
    welcome_text = (
        f"Assalomu alaykum, {message.from_user.full_name}! 🎓\n\n"
        "Men sizning shaxsiy akademik maslahatchi AI Assistantingizman. "
        "Sizga kelajagingiz uchun eng mos keladigan universitet va grantlarni topishda yordam beraman.\n\n"
        "Menga o'zingiz haqingizda quyidagi ma'lumotlarni erkin shaklda yuboring:\n"
        "• Qiziqqan yo'nalishingiz (IT, Biznes, Tibbiyot, Logistika...)\n"
        "• Til sertifikatlaringiz (IELTS, CEFR, TOPIK...)\n"
        "• Baholaringiz (Maktab/Kollej GPA)\n"
        "• Qaysi davlatda o'qishni reja qilyapsiz?\n"
        "• Grant asosidami yoki kontrakt?\n\n"
        "Xohlagan uslubda yozing, men hammasini eslab qolib, sizga eng zo'r variantlarni tahlil qilib beraman!"
    )
    await message.reply(welcome_text)

@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    user_id = message.from_user.id
    chat_sessions[user_id] = model.start_chat(history=[])
    await message.reply("🔄 Suhbat tarixi muvaffaqiyatli tozalandi. Yangitdan ma'lumot berishingiz mumkin.")

@dp.message()
async def handle_ai_message(message: types.Message):
    user_id = message.from_user.id
    user_text = message.text

    if user_text == SECRET_ADMIN_KEY:
        admin_welcome = (
            f"👑 Salom, Alibek! Tizim sizni muvaffaqiyatli tanidi.\n\n"
            f"Siz ushbu professional AI botning asoschisi va loyiha rahbarisiz. "
            f"Hozirda Render serverlari ideal holatda ishlamoqda, "
            f"AI modeli (Gemini 1.5 Pro) aloqada. Omad tilayman, Boss!"
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
        logging.error(f"AI Xatolik yuz berdi: {e}")
        try:
            direct_response = model.generate_content(user_text)
            await message.reply(direct_response.text, parse_mode="Markdown")
        except Exception as e2:
            await message.reply(
                "Tizim ulandi! AI kaliti serverda to'liq faollashmoqda. "
                "Iltimos, 30 soniya kutib qayta yozib ko'ring, Boss."
            )

async def main():
    logging.info("Professional Bot muvaffaqiyatli ishga tushmoqda...")
    asyncio.create_task(dummy_web_server())
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot to'xtatildi.")
 
