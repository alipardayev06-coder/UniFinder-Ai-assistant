import os
import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import google.generativeai as genai

# Tizim xavfsizligi va loglarini sozlash
logging.basicConfig(level=logging.INFO)

# Tokenlarni server muhitidan yuklash
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)

# Universitetlar uchun bosqichma-bosqich diagnostika prompti
SYSTEM_PROMPT = (
    "You are a professional multi-language AI Academic Advisor using a strict step-by-step diagnostic system. "
    "Identify the user's language automatically (Uzbek, Russian, English, etc.) and strictly follow this protocol:\n\n"
    "1. FIRST MESSAGE (When user says START_DIAGNOSTIC or starts): Do NOT recommend any universities yet. "
    "Warmly welcome the user and ask them 3 specific questions: Their Age, whether they graduated school/college, and their current fields of interest.\n"
    "2. SECOND STEP (When user provides details): Analyze their chosen field or career interest. Objectively explain the PLUS (advantages) and MINUS (disadvantages/realities) sides of this career path so they understand it fully.\n"
    "3. FINAL STEP (After analysis): Provide a PERFECT personalized academic road map. Recommend specific top global and local universities, available international scholarships (like GKS, Stipendium Hungaricum, Turkiye Burslari, etc.), and step-by-step actions they should take.\n\n"
    "Keep all responses clean, structured, highly professional, and motivational. Do NOT use complex markdown or formatting symbols that can break Telegram, write in clear plain text format."
)

# Faqat siz uchun ishlaydigan Shaxsiy Assistant Prompti
PERSONAL_ASSISTANT_PROMPT = (
    "Siz Alibossning shaxsiy, eng sodiq and maxfiy AI Assistantisiz. "
    "U sizning yagona xo'jayiningiz va rahbardingiz. Unga hayotiy masalalarda, biznesda, rejalashtirishda va har qanday shaxsiy savolda "
    "eng oliy darajada, chuqur tahlil bilan, aqlli va cheksiz sodiqlik bilan javob bering. Ohangingiz doim hurmat va do'stona ruhda bo'lsin."
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# SQLite Ma'lumotlar bazasini 2 ta jadval bilan sozlash
conn = sqlite3.connect("bot_database.db", check_same_thread=False)
cursor = conn.cursor()

# 1-JADVAL: Foydalanuvchilar va xavfsizlik nazorati
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    is_banned INTEGER DEFAULT 0
)
""")

# 2-JADVAL: Talabalar kiritgan diagnostika ma'lumotlari ombori
cursor.execute("""
CREATE TABLE IF NOT EXISTS diagnostic_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    user_input TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# Admin FSM (Jarayonlar) holati
class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_ban = State()

# Kesh xotiralari
user_chats = {}
personal_chats = {}      
admin_sessions = set()    
assistant_sessions = set() 
last_messages = []
def get_user_chat(user_id: int):
    if user_id not in user_chats:
        model = genai.GenerativeModel(model_name="gemini-3.5-flash", system_instruction=SYSTEM_PROMPT)
        user_chats[user_id] = model.start_chat(history=[])
    return user_chats[user_id]

def get_personal_chat(user_id: int):
    if user_id not in personal_chats:
        model = genai.GenerativeModel(model_name="gemini-3.5-flash", system_instruction=PERSONAL_ASSISTANT_PROMPT)
        personal_chats[user_id] = model.start_chat(history=[])
    return personal_chats[user_id]

# Elite Admin panel tugmalari

def get_admin_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📊 Foydalanuvchilar soni")
    builder.button(text="📣 Reklama tarqatish")
    builder.button(text="🚫 Foydalanuvchini bloklash")
    builder.button(text="💬 Oxirgi xabarlar")
    builder.button(text="🔄 Tizimni yangilash")
    builder.button(text="❌ Admin paneldan chiqish")
    builder.adjust(2, 2, 2)
    return builder.as_markup(resize_keyboard=True)

# Shaxsiy Assistant boshqaruv tugmalari
def get_assistant_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔄 Assistant Xotirasini Tozalash")
    builder.button(text="🚪 Shaxsiy rejimdan chiqish")
    builder.adjust(1, 1)
    return builder.as_markup(resize_keyboard=True)

# /start buyrug'i (Diagnostikani boshlash)
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoName"
    
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    if user_data and user_data[0] == 1:
        await message.answer("Siz ushbu botdan bloklangansiz! ❌")
        return

    if user_id in user_chats:
        del user_chats[user_id]
        
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        chat_session = get_user_chat(user_id)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, chat_session.send_message, "START_DIAGNOSTIC")
        await message.answer(response.text)
    except Exception as e:
        logging.error(f"Start xatoligi: {e}")
        await message.answer(
            "Assalomu alaykum! UniFinder AI akademik diagnostika botiga xush kelibsiz. 🎓\n\n"
            "Sizga eng to'g'ri universitet va grantlarni tavsiya qilishim uchun iltimos, birinchi bo'lib o'zingiz haqingizda ma'lumot bering:\n"
            "1. Yoshingiz nechada?\n"
            "2. Maktab, litsey yoki kollejni bitirganmisiz?\n"
            "3. Hozirda qaysi sohalarga yoki fanlarga qiziqasiz?"
        )

# Admin: Reklama tarqatish jarayoni
@dp.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Reklama yuborish bekor qilindi.", reply_markup=get_admin_keyboard())
        return
        
    cursor.execute("SELECT user_id FROM users WHERE is_banned = 0")
    all_users = cursor.fetchall()
    success, failed = 0, 0
    await message.answer("📢 E'lon tarqatish boshlandi, iltimos kuting...")
    
    for u in all_users:
        try:
            await bot.forward_message(chat_id=u[0], from_chat_id=message.chat.id, message_id=message.message_id)
            success += 1
            await asyncio.sleep(0.05)  
        except Exception:
            failed += 1
            
    await state.clear()
    await message.answer(f"📢 Tarqatish yakunlandi!\n✅ Yetkazildi: {success} ta foydalanuvchiga\n❌ Yetkazilmadi: {failed} ta", reply_markup=get_admin_keyboard())

# Admin: Foydalanuvchini bloklash jarayoni
@dp.message(AdminStates.waiting_for_ban)
async def process_ban(message: types.Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bloklash jarayoni bekor qilindi.", reply_markup=get_admin_keyboard())
        return
        
    try:
        target_id = int(message.text.strip())
        cursor.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (target_id,))
        conn.commit()
        await state.clear()
        await message.answer(f"🚫 Foydalanuvchi ({target_id}) muvaffaqiyatli bloklandi!", reply_markup=get_admin_keyboard())
    except ValueError:
        await message.answer("Xato! Iltimos, foydalanuvchining faqat raqamlardan iborat Telegram ID sini kiriting:")

# Asosiy xabarlar mantiqiy zanjiri
@dp.message()
async def handle_main_logic(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    text = message.text.strip() if message.text else ""

    if text == "Aliboss":
        if user_id in assistant_sessions:
            assistant_sessions.remove(user_id)
        admin_sessions.add(user_id)
        await message.answer("Xush kelibsiz, Aliboss! 👑 Bot boshqaruv paneli ishga tushdi.", reply_markup=get_admin_keyboard())
        return

    if text == "Aliboss assistant":
        if user_id in admin_sessions:
            admin_sessions.remove(user_id)
        assistant_sessions.add(user_id)
        await message.answer("Sizning shaxsiy AI yordamchingiz tayyor, Aliboss. Xizmatingizdaman! 🕶️", reply_markup=get_assistant_keyboard())
        return

    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    if user_data and user_data[0] == 1:
        return

    if user_id in admin_sessions:
        if text == "📊 Foydalanuvchilar soni":
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()
            await message.answer(f"📊 Ma'lumotlar bazasidagi jami foydalanuvchilar: {count[0]} ta")
            return
        elif text == "📣 Reklama tarqatish":
            await state.set_state(AdminStates.waiting_for_broadcast)
            cancel_kb = ReplyKeyboardBuilder().button(text="❌ Bekor qilish")
            await message.answer("Menga barcha foydalanuvchilarga yubormoqchi bo'lgan e'loningizni yuboring:", reply_markup=cancel_kb.as_markup(resize_keyboard=True))
            return
        elif text == "🚫 Foydalanuvchini bloklash":
            await state.set_state(AdminStates.waiting_for_ban)
            cancel_kb = ReplyKeyboardBuilder().button(text="❌ Bekor qilish")
            await message.answer("Bloklamoqchi bo'lgan foydalanuvchining Telegram ID raqamini yozing:", reply_markup=cancel_kb.as_markup(resize_keyboard=True))
            return
        elif text == "💬 Oxirgi xabarlar":
            report = "\n".join(last_messages[-10:]) if last_messages else "Hozircha tizimda faollik yo'q."
            await message.answer(f"💬 Oxirgi faollik ko'rsatkichlari (Maks 10 ta):\n\n{report}")
            return
        elif text == "🔄 Tizimni yangilash":
            user_chats.clear()
            await message.answer("Tizimning kesh xotirasi muvaffaqiyatli tozalandi! 🔄")
            return
        elif text == "❌ Admin paneldan chiqish":
            admin_sessions.remove(user_id)
            await message.answer("Boshqaruv panelidan chiqdingiz. Bot oddiy akademik rejimga qaytdi.", reply_markup=types.ReplyKeyboardRemove())
            return

    if user_id in assistant_sessions:
        if text == "🔄 Assistant Xotirasini Tozalash":
            if user_id in personal_chats:
                del personal_chats[user_id]
            await message.answer("Siz bilan bo'lgan shaxsiy suhbatlar xotirasi butunlay tozalandi! 🔄")
            return
        elif text == "🚪 Shaxsiy rejimdan chiqish":
            assistant_sessions.remove(user_id)
            await message.answer("Shaxsiy assistant rejimi yopildi. Bot oddiy rejimga qaytdi.", reply_markup=types.ReplyKeyboardRemove())
            return

        if not text: return
        await bot.send_chat_action(chat_id=message.chat.id, action="typing")
        try:
            chat_session = get_personal_chat(user_id)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, chat_session.send_message, text)
            await message.answer(response.text)
        except Exception as e:
            await message.answer(f"Xatolik yuz berdi: {e}")
        return

    if not text: return

    cursor.execute("INSERT INTO diagnostic_data (user_id, user_input) VALUES (?, ?)", (user_id, text))
    conn.commit()

last_messages.append(f"👤 {user_name} ({user_id}): {text}")
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        chat_session = get_user_chat(user_id)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, chat_session.send_message, text)
        await message.answer(response.text)
    except Exception as e:
        logging.error(f"AI Xatoligi: {e}")
        await message.answer("Kechirasiz, so'rovingizni qayta ishlashda xatolik bo'ldi. Iltimos, qaytadan yozib ko'ring.")

async def main():
    print("Super-Elite AI Bot muvaffaqiyatli ishga tushdi!")
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())
