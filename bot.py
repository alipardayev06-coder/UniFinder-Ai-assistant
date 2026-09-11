import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
import google.generativeai as genai

# Tizim xavfsizligi va loglarini sozlash
logging.basicConfig(level=logging.INFO)

# Tokenlarni yuklash
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

# Elite darajadagi Tizimli Prompt
SYSTEM_PROMPT = (
    "Siz O'zbekistondagi talabalar va o'quvchilarga xalqaro hamda mahalliy universitetlarni, "
    "shuningdek, grant dasturlarini topishda yordam beradigan eng kuchli va professional AI Akademik Maslahatchisiz. "
    "Foydalanuvchilarning qiziqishlari, IELTS ballari va GPA ko'rsatkichlariga qarab aniq universitetlar tizimini tavsiya qiling. "
    "Javoblaringiz juda aniq, lo'nda va tushunarli bo'lsin. Ortiqcha Markdown belgilarini ishlatmang, oddiy matnda yozing."
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Ma'lumotlar bazasi vazifasini o'tovchi xotira bloklari
user_chats = {}
registered_users = set()  # Foydalanuvchilar ro'yxati
admin_sessions = set()    # Aktiv adminlar ro'yxati
last_messages = []        # Oxirgi xabarlar logi

def get_user_chat(user_id: int):
    if user_id not in user_chats:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",  # Eng tezkor va barqaror global model
            system_instruction=SYSTEM_PROMPT
        )
        user_chats[user_id] = model.start_chat(history=[])
    return user_chats[user_id]

# Admin uchun chiroyli boshqaruv tugmalari
def get_admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📊 Foydalanuvchilar soni")
    builder.button(text="💬 Oxirgi xabarlarni ko'rish")
    builder.button(text="🔄 Tizimni yangilash")
    builder.button(text="❌ Admin paneldan chiqish")
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)

# /start buyrug'i
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    registered_users.add(user_id)
    
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
        "Men hammasini tezkor tahlil qilib, sizga eng zo'r variantlarni chiqarib beraman! 🚀"
    )
    await message.answer(welcome_text)

# Tarixni tozalash (/clear)
@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_chats:
        del user_chats[user_id]
    await message.answer("Suhbatimiz tarixi tozalandi. Yangidan ma'lumot kiritishingiz mumkin! 🔄")

# Matnli xabarlarni qayta ishlash zanjiri
@dp.message()
async def handle_main_logic(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    text = message.text.strip()

    # 1. Maxfiy kod orqali Adminlikni faollashtirish
    if text == "Aliboss":
        admin_sessions.add(user_id)
        await message.answer("Xush kelibsiz, Aliboss! 👑 Tizim boshqaruvi sizga topshirildi.", reply_markup=get_admin_keyboard())
        return

    # 2. Admin boshqaruv buyruqlari
    if user_id in admin_sessions:
        if text == "📊 Foydalanuvchilar soni":
            count = len(registered_users)
            await message.answer(f"📊 Hozirgi kunda botdan foydalangan jami foydalanuvchilar: {count} ta")
            return
        elif text == "💬 Oxirgi xabarlarni ko'rish":
            if not last_messages:
                await message.answer("Hozircha tizimda hech qanday xabarlar qayd etilmadi.")
                return
            report = "\n".join(last_messages[-10:])  # Oxirgi 10 ta xabar
            await message.answer(f"💬 Oxirgi faollik ko'rsatkichlari:\n\n{report}")
            return
        elif text == "🔄 Tizimni yangilash":
            user_chats.clear()
            await message.answer("Tizim kesh xotirasi muvaffaqiyatli tozalandi! 🔄")
            return
        elif text == "❌ Admin paneldan chiqish":
            admin_sessions.remove(user_id)
            await message.answer("Admin paneldan muvaffaqiyatli chiqdingiz. Bot oddiy rejimga qaytdi.", reply_markup=types.ReplyKeyboardRemove())
            return

    # 3. Oddiy foydalanuvchilar uchun AI javob tizimi
    registered_users.add(user_id)
    # Xabarlar logini yuritish
    last_messages.append(f"👤 {user_name} ({user_id}): {text}")
    
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        chat_session = get_user_chat(user_id)
        # Tezkor asinxron zanjir orqali javob olish (Blokirovkasiz)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, chat_session.send_message, text)
        
        # Maxsus parse_modlarsiz toza va xatosiz yuborish
        await message.answer(response.text)
    except Exception as e:
        logging.error(f"Tizim xatoligi: {e}")
        await message.answer("Kechirasiz, so'rovingizni qayta ishlashda xatolik bo'ldi. Iltimos qaytadan yozib ko'ring.")

async def main():
    print("Elite AI Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
