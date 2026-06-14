import asyncio
import logging
import sqlite3
import re
import time
from datetime import datetime, time as dtime

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters, ApplicationHandlerStop
)
from telegram.error import Forbidden, BadRequest

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8661822300:AAG0epifmA0C_6OeMuPh9Ll-yD6LQZihyvU"

# --------- SOZLAMALAR ---------
ADMIN_ID = 988635477  # admin Telegram ID

CHANNELS = {
    "초급": "https://t.me/+988635477",   # <-- darajaga mos kanal linklari (keyin alohida qo'ying)
    "중급": "https://t.me/+988635477",
    "고급": "https://t.me/+988635477",
    "default": "https://t.me/+988635477",   # umumiy kanal (reyting shu yerga yuboriladi)
}

# Kunlik test poll'lari yuboriladigan guruh ID (Telegram guruh ID'lari -100 bilan boshlanadi)
GROUP_CHAT_ID = -1001297463776

# Har bir savolga ajratiladigan vaqt (soniya), txt faylning birinchi qatorida
# "VAQT: 35" ko'rinishida o'zgartirilishi mumkin
DEFAULT_POLL_SECONDS = 35

DB_PATH = "bot_database.db"

# ---------- HOLATLAR ----------
(ASK_NAME, ASK_LEVEL, TESTING, ASK_REASON) = range(4)

# ---------- TEST SAVOLLARI (har daraja uchun 10 ta) ----------
TESTS = {
    "초급": [
        {"q": "1) '안녕하세요' so'zining ma'nosi nima?",
         "options": ["Salom", "Rahmat", "Kechirasiz", "Xayr"], "answer": 0},
        {"q": "2) '저는 학생입니다' - bu gap nima haqida?",
         "options": ["Men o'qituvchiman", "Men talabaman", "Men ishchiman", "Men o'qiyman"], "answer": 1},
        {"q": "3) '감사합니다' so'zi qaysi ma'noni bildiradi?",
         "options": ["Rahmat", "Iltimos", "Kechirasiz", "Salom"], "answer": 0},
        {"q": "4) '이것은 무엇입니까?' - tarjimasi?",
         "options": ["Bu nima?", "Bu kim?", "Bu qayerda?", "Bu qachon?"], "answer": 0},
        {"q": "5) '하나, 둘, 셋' - bu nima?",
         "options": ["Kunlar", "Sonlar", "Ranglar", "Hayvonlar"], "answer": 1},
        {"q": "6) '물' so'zi nimani bildiradi?",
         "options": ["Non", "Suv", "Olma", "Sut"], "answer": 1},
        {"q": "7) '책' so'zi nimani anglatadi?",
         "options": ["Kitob", "Stol", "Stul", "Daftar"], "answer": 0},
        {"q": "8) '학교에 갑니다' - tarjimasi?",
         "options": ["Maktabga boraman", "Uyga boraman", "Do'konga boraman", "Ishga boraman"], "answer": 0},
        {"q": "9) '오늘' so'zi qachonni bildiradi?",
         "options": ["Kecha", "Bugun", "Ertaga", "Hafta"], "answer": 1},
        {"q": "10) '안녕히 가세요' qachon ishlatiladi?",
         "options": ["Uchrashganda", "Xayrlashganda", "Ovqatlanishda", "Uyg'onganda"], "answer": 1},
    ],
    "중급": [
        {"q": "1) '비록 ~지만' grammatikasi nimani bildiradi?",
         "options": ["Garchi...lekin", "Chunki", "Agar", "Keyin"], "answer": 0},
        {"q": "2) '~는 것 같다' qachon ishlatiladi?",
         "options": ["Buyruq berishda", "Taxmin qilishda", "So'rashda", "Rad etishda"], "answer": 1},
        {"q": "3) '결심하다' so'zining ma'nosi?",
         "options": ["Qaror qabul qilmoq", "Tushunmoq", "Unutmoq", "Yordam berish"], "answer": 0},
        {"q": "4) '~ㄴ 적이 있다' nimani anglatadi?",
         "options": ["Hozir qilayotgan ish", "Tajriba/qilgan ish", "Kelajak reja", "Buyruq"], "answer": 1},
        {"q": "5) '환경 보호' iborasi nimani bildiradi?",
         "options": ["Atrof-muhitni muhofaza qilish", "Sayohat qilish", "Ishlab chiqarish", "Tarbiyalash"], "answer": 0},
        {"q": "6) '~기 때문에' qaysi ma'noni beradi?",
         "options": ["Sababini bildiradi", "Maqsadini bildiradi", "Shartni bildiradi", "Vaqtni bildiradi"], "answer": 0},
        {"q": "7) '경제' so'zi nimani anglatadi?",
         "options": ["Iqtisod", "Siyosat", "Madaniyat", "Tarix"], "answer": 0},
        {"q": "8) '~는 동안' grammatikasi ma'nosi?",
         "options": ["...vaqtida/davomida", "...dan keyin", "...dan oldin", "...uchun"], "answer": 0},
        {"q": "9) '존경하다' so'zining ma'nosi?",
         "options": ["Hurmat qilmoq", "Yoqtirmaslik", "Tanqid qilmoq", "Unutmoq"], "answer": 0},
        {"q": "10) '~ㄹ 수밖에 없다' nimani bildiradi?",
         "options": ["Iloji yo'q, faqat shu yo'l", "Imkoniyat ko'p", "Taqiqlangan", "Ixtiyoriy"], "answer": 0},
    ],
    "고급": [
        {"q": "1) '~다시피' grammatikasi qanday ishlatiladi?",
         "options": ["Bilganingizdek...", "Agar...", "Garchi...", "Chunki..."], "answer": 0},
        {"q": "2) '간과하다' so'zining ma'nosi?",
         "options": ["E'tibordan chetda qoldirmoq", "Diqqat qilmoq", "Tahlil qilmoq", "Rad etmoq"], "answer": 0},
        {"q": "3) '~는 한편' nimani bildiradi?",
         "options": ["Bir tomondan...", "Aksincha", "Natijada", "Shu sababli"], "answer": 0},
        {"q": "4) '타협' so'zining ma'nosi?",
         "options": ["Kelishuv/murosa", "Janjal", "G'alaba", "Mag'lubiyat"], "answer": 0},
        {"q": "5) '~로 인해' qaysi ma'noni beradi?",
         "options": ["Sababli/natijasida", "Maqsad bilan", "Qaramay", "O'rniga"], "answer": 0},
        {"q": "6) '여론' so'zining ma'nosi?",
         "options": ["Jamoatchilik fikri", "Shaxsiy fikr", "Rasmiy hujjat", "Ilmiy maqola"], "answer": 0},
        {"q": "7) '~을지언정' grammatikasi nimani anglatadi?",
         "options": ["...bo'lsa ham (kuchli qarshi qo'yish)", "...bo'lgani uchun", "...bo'lganda", "...bo'lib"], "answer": 0},
        {"q": "8) '심층적' so'zining ma'nosi?",
         "options": ["Chuqur/atroflicha", "Yuzaki", "Tezkor", "Oddiy"], "answer": 0},
        {"q": "9) '~기 마련이다' nimani bildiradi?",
         "options": ["Tabiiy holat/odat", "Kutilmagan holat", "Taqiq", "Buyruq"], "answer": 0},
        {"q": "10) '대두되다' so'zining ma'nosi?",
         "options": ["Yuzaga kelmoq/paydo bo'lmoq", "Yo'qolmoq", "Kichraymoq", "Tugamoq"], "answer": 0},
    ],
}

REASONS = ["Ishim uchun", "O'qish uchun (universitet)", "Koreyaga ishlash uchun ketish",
           "K-pop/K-drama qiziqishi", "Sayohat uchun", "Boshqa"]

RECOMMENDATIONS = {
    "초급": {
        "default": {
            "text": "Sizning darajangiz - BOSHLANG'ICH (초급). Asosiy lug'at va grammatikaga e'tibor bering.",
            "book": "https://t.me/korea_book/13859",
            "video": "https://youtu.be/GWaOpcoEHdU?si=3RjfRBvDnR0Kydx0"
        },
        "Koreyaga ishlash uchun ketish": {
            "text": "EPS-TOPIK imtihoniga tayyorgarlik uchun asosiy so'zlashuv va ish joyidagi atamalarni o'rganing.",
            "book": "https://t.me/korea_book/13745",
            "video": "https://youtu.be/Q6jrLp9lXa0?si=FmqoPZ4UE66aTkyo"
        },
        "K-pop/K-drama qiziqishi": {
            "text": "Kundalik so'zlashuv iboralarini drama orqali mashq qiling - bu motivatsiyangizni oshiradi.",
            "book": "https://t.me/korea_book/13859",
            "video": "https://youtu.be/GWaOpcoEHdU?si=3RjfRBvDnR0Kydx0"
        },
    },
    "중급": {
        "default": {
            "text": "Sizning darajangiz - O'RTA (중급). Grammatik konstruksiyalarni mustahkamlash va o'qish-tinglashga ko'proq vaqt ajrating.",
            "book": "https://t.me/korea_book/13745",
            "video": "https://youtu.be/0yJDymAvE0Q?si=xLsoORcMgV1vMcTt"
        },
        "O'qish uchun (universitet)": {
            "text": "TOPIK II ga tayyorgarlik ko'ring, akademik lug'at va insho yozishni mashq qiling.",
            "book": "https://t.me/korea_book/13859",
            "video": "https://youtu.be/mElwIlwiubY?si=JcqXsRWVM8aj_MvP"
        },
        "Ishim uchun": {
            "text": "Biznes koreys tili va rasmiy muloqot uslubini (존댓말) chuqurroq o'rganing.",
            "book": "https://t.me/korea_book/13745",
            "video": "https://youtu.be/0yJDymAvE0Q?si=xLsoORcMgV1vMcTt"
        },
    },
    "고급": {
        "default": {
            "text": "Sizning darajangiz - YUQORI (고급). Murakkab matnlar, yangiliklar va akademik manbalar bilan ishlashni davom ettiring.",
            "book": "https://t.me/korea_book/13859",
            "video": "https://youtu.be/mElwIlwiubY?si=JcqXsRWVM8aj_MvP"
        },
        "O'qish uchun (universitet)": {
            "text": "TOPIK 5-6 darajaga tayyorgarlik uchun akademik yozish va tinglashga e'tibor qiling.",
            "book": "https://t.me/korea_book/13745",
            "video": "https://youtu.be/0yJDymAvE0Q?si=xLsoORcMgV1vMcTt"
        },
        "Ishim uchun": {
            "text": "Professional muzokaralar va hujjat yozish uslublarini o'rganishni tavsiya qilamiz.",
            "book": "https://t.me/korea_book/13859",
            "video": "https://youtu.be/mElwIlwiubY?si=JcqXsRWVM8aj_MvP"
        },
    },
}


# ============================================================
# MA'LUMOTLAR BAZASI
# ============================================================

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            level TEXT,
            score INTEGER,
            reason TEXT,
            registered_at TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS weekly_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            username TEXT,
            full_name TEXT,
            score INTEGER,
            total INTEGER,
            duration_seconds REAL,
            test_date TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_user(telegram_id, username, full_name, level, score, reason):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO users (telegram_id, username, full_name, level, score, reason, registered_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            username=excluded.username,
            full_name=excluded.full_name,
            level=excluded.level,
            score=excluded.score,
            reason=excluded.reason,
            registered_at=excluded.registered_at
    """, (telegram_id, username, full_name, level, score, reason, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_all_subscribers():
    """Botda ro'yxatdan o'tgan barcha foydalanuvchilar (haftalik test uchun)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT telegram_id, username, full_name FROM users")
    rows = c.fetchall()
    conn.close()
    return rows


def save_weekly_result(telegram_id, username, full_name, score, total, duration_seconds):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO weekly_results (telegram_id, username, full_name, score, total, duration_seconds, test_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (telegram_id, username, full_name, score, total, duration_seconds, datetime.now().date().isoformat()))
    conn.commit()
    conn.close()


def get_weekly_leaderboard(test_date):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT username, full_name, score, total, duration_seconds
        FROM weekly_results
        WHERE test_date = ?
        ORDER BY score DESC, duration_seconds ASC
    """, (test_date,))
    rows = c.fetchall()
    conn.close()
    return rows


# ============================================================
# KLAVIATURALAR
# ============================================================

def level_keyboard():
    return ReplyKeyboardMarkup(
        [["초급 (Boshlang'ich)"], ["중급 (O'rta)"], ["고급 (Yuqori)"]],
        resize_keyboard=True, one_time_keyboard=True
    )


def reason_keyboard():
    return ReplyKeyboardMarkup(
        [[r] for r in REASONS], resize_keyboard=True, one_time_keyboard=True
    )


LEVEL_MAP = {
    "초급 (Boshlang'ich)": "초급",
    "중급 (O'rta)": "중급",
    "고급 (Yuqori)": "고급",
}


# ============================================================
# ASOSIY RO'YXATDAN O'TISH + TEST OQIMI
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user = update.effective_user
    context.user_data["telegram_id"] = user.id
    context.user_data["telegram_username"] = user.username or "Yo'q"
    await update.message.reply_text(
        "Salom! Koreys tili darajangizni aniqlash testiga xush kelibsiz.\n\n"
        "Ism va familyangizni kiriting:"
    )
    return ASK_NAME


async def ask_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["full_name"] = update.message.text.strip()
    await update.message.reply_text(
        f"Rahmat, {context.user_data['full_name']}!\n\n"
        "Telegram ID: {}\nUsername: @{}\n\n"
        "Endi koreys tili darajangizni tanlang:".format(
            context.user_data["telegram_id"], context.user_data["telegram_username"]
        ),
        reply_markup=level_keyboard()
    )
    return ASK_LEVEL


async def start_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text not in LEVEL_MAP:
        await update.message.reply_text("Iltimos, tugmalardan birini tanlang.", reply_markup=level_keyboard())
        return ASK_LEVEL

    level = LEVEL_MAP[text]
    context.user_data["level"] = level
    context.user_data["questions"] = TESTS[level]
    context.user_data["current_q"] = 0
    context.user_data["score"] = 0

    await update.message.reply_text(
        f"Daraja tanlandi: {level}\n\nTest boshlanadi. Jami 10 ta savol. Omad!",
        reply_markup=None
    )
    await send_question(update, context)
    return TESTING


async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data["current_q"]
    questions = context.user_data["questions"]
    q = questions[idx]
    kb = ReplyKeyboardMarkup(
        [[opt] for opt in q["options"]], resize_keyboard=True, one_time_keyboard=True
    )
    await update.message.reply_text(q["q"], reply_markup=kb)


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = context.user_data["current_q"]
    questions = context.user_data["questions"]
    q = questions[idx]
    user_answer = update.message.text.strip()

    if user_answer not in q["options"]:
        await update.message.reply_text("Iltimos, variantlardan birini tanlang.")
        await send_question(update, context)
        return TESTING

    if q["options"].index(user_answer) == q["answer"]:
        context.user_data["score"] += 1

    context.user_data["current_q"] += 1

    if context.user_data["current_q"] < 10:
        await send_question(update, context)
        return TESTING
    else:
        score = context.user_data["score"]
        level = context.user_data["level"]
        context.user_data["final_score"] = score

        if score >= 8:
            result_level = "Yuqori (이번 단계는 잘 통과했습니다)"
        elif score >= 5:
            result_level = "O'rta (조금 더 연습이 필요합니다)"
        else:
            result_level = "Boshlang'ich (기초부터 다시 다지세요)"

        await update.message.reply_text(
            f"Test yakunlandi! ✅\n\n"
            f"Natija: {score}/10\n"
            f"Tanlangan daraja: {level}\n"
            f"Tahlil: {result_level}\n\n"
            f"Endi, koreys tilini nima maqsadda o'rganayotganingizni tanlang:",
            reply_markup=reason_keyboard()
        )
        return ASK_REASON


async def give_recommendation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason = update.message.text.strip()
    if reason not in REASONS:
        await update.message.reply_text("Iltimos, variantlardan birini tanlang.", reply_markup=reason_keyboard())
        return ASK_REASON

    context.user_data["reason"] = reason
    level = context.user_data["level"]
    score = context.user_data["final_score"]
    user = update.effective_user

    # Foydalanuvchini bazaga saqlash (haftalik testlar uchun ham ishlatiladi)
    save_user(
        telegram_id=user.id,
        username=user.username or "",
        full_name=context.user_data["full_name"],
        level=level,
        score=score,
        reason=reason,
    )

    level_recs = RECOMMENDATIONS.get(level, {})
    rec = level_recs.get(reason, level_recs["default"])

    channel_link = CHANNELS.get(level, CHANNELS["default"])

    summary = (
        f"📋 NATIJALAR XULOSASI\n\n"
        f"👤 Ism: {context.user_data['full_name']}\n"
        f"🆔 Telegram: @{context.user_data['telegram_username']} (ID: {context.user_data['telegram_id']})\n"
        f"📊 Daraja: {level}\n"
        f"✅ Test natijasi: {score}/10\n"
        f"🎯 Maqsad: {reason}\n\n"
        f"💡 TAVSIYA:\n{rec['text']}\n\n"
        f"📚 Kitob (PDF): {rec['book']}\n"
        f"🎬 Video dars: {rec['video']}\n\n"
        f"📢 Darajangizga mos kanalga qo'shiling:\n{channel_link}\n\n"
        f"Omad tilaymiz! Qaytadan boshlash uchun /start buyrug'ini bosing."
    )

    await update.message.reply_text(summary, reply_markup=None)

    # ---- ADMINGA XABAR ----
    admin_msg = (
        f"🆕 YANGI TEST NATIJASI\n\n"
        f"👤 Ism: {context.user_data['full_name']}\n"
        f"🆔 ID: {context.user_data['telegram_id']}\n"
        f"📱 Username: @{context.user_data['telegram_username']}\n"
        f"📊 Daraja: {level}\n"
        f"✅ Natija: {score}/10\n"
        f"🎯 Maqsad: {reason}"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
    except Exception as e:
        logging.warning(f"Adminga xabar yuborilmadi: {e}")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi. Qayta boshlash uchun /start ni bosing.")
    return ConversationHandler.END


# ============================================================
# HAFTALIK TEST TIZIMI (ADMIN .txt YUBORADI -> BOT BARCHAGA YUBORADI)
# ============================================================
#
# TXT FORMAT NAMUNASI (har savol orasida BO'SH QATOR bo'lishi shart):
#
# 1) 안녕하세요 nimani bildiradi?
# A) Salom
# B) Rahmat
# C) Kechirasiz
# D) Xayr
# JAVOB: A
#
# 2) 감사합니다 nimani bildiradi?
# A) Iltimos
# B) Rahmat
# C) Salom
# D) Xayr
# JAVOB: B
#
# ... (xohlagancha savol qo'shish mumkin)


def parse_weekly_txt(text: str):
    """TXT formatdagi savollarni parse qiladi.
    Birinchi qatorda 'VAQT: 35' bo'lishi mumkin - bu har bir poll uchun
    ajratiladigan vaqt (soniya). Bo'lmasa DEFAULT_POLL_SECONDS ishlatiladi."""
    text = text.strip()
    poll_seconds = DEFAULT_POLL_SECONDS

    first_line, _, rest = text.partition("\n")
    m = re.match(r"^VAQT:\s*(\d+)$", first_line.strip(), re.IGNORECASE)
    if m:
        poll_seconds = int(m.group(1))
        text = rest.strip()

    questions = []
    blocks = re.split(r"\n\s*\n", text.strip())
    for block in blocks:
        lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
        if len(lines) < 6:
            continue
        q_text = re.sub(r"^\d+\)\s*", "", lines[0])
        options = []
        for line in lines[1:5]:
            m2 = re.match(r"^([A-D])\)\s*(.+)$", line, re.IGNORECASE)
            if m2:
                options.append(m2.group(2).strip())
        ans_line = lines[5] if len(lines) > 5 else ""
        m2 = re.match(r"^JAVOB:\s*([A-D])$", ans_line, re.IGNORECASE)
        if m2 and len(options) == 4:
            answer_idx = "ABCD".index(m2.group(1).upper())
            questions.append({"q": q_text, "options": options, "answer": answer_idx})
    return questions, poll_seconds


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin .txt fayl yuborganda kunlik test savollarini yuklab oladi."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    doc = update.message.document
    if not doc.file_name.endswith(".txt"):
        await update.message.reply_text("Iltimos, .txt formatdagi fayl yuboring.")
        return

    file = await doc.get_file()
    file_bytes = await file.download_as_bytearray()
    text = file_bytes.decode("utf-8")

    questions, poll_seconds = parse_weekly_txt(text)
    if not questions:
        await update.message.reply_text(
            "❌ Faylni o'qishda xato. Format quyidagicha bo'lishi kerak:\n\n"
            "VAQT: 35\n\n"
            "1) Savol matni?\n"
            "A) Variant 1\n"
            "B) Variant 2\n"
            "C) Variant 3\n"
            "D) Variant 4\n"
            "JAVOB: A\n\n"
            "(har bir savol orasida bo'sh qator bo'lishi kerak, 'VAQT: 35' qatori ixtiyoriy)"
        )
        return

    context.bot_data["daily_questions"] = questions
    context.bot_data["daily_poll_seconds"] = poll_seconds

    await update.message.reply_text(
        f"✅ {len(questions)} ta savol qabul qilindi! Har bir savolga {poll_seconds} soniya beriladi.\n\n"
        f"Bugun soat 20:00da bu savollar guruhga so'rovnoma (poll) shaklida ketma-ket yuboriladi.\n\n"
        f"Hoziroq sinab ko'rish uchun /test_yubor buyrug'ini ishlatishingiz mumkin."
    )




async def manual_send_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin uchun: kunlik testni qo'lda darhol guruhga yuborish (sinov uchun)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    questions = context.bot_data.get("daily_questions")
    if not questions:
        await update.message.reply_text("Hozircha kunlik savollar yuklanmagan. Avval .txt fayl yuboring.")
        return
    await update.message.reply_text("Test guruhga yuborilmoqda...")
    await send_daily_test_to_group(context)


async def manual_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin uchun: reytingni darhol e'lon qilish (sinov uchun)."""
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    await announce_daily_leaderboard(context)
    await update.message.reply_text("✅ Reyting e'lon qilindi.")


# ============================================================
# GURUHGA QUIZ POLL YUBORISH (har savol alohida, ketma-ket)
# ============================================================

async def send_daily_test_to_group(context: ContextTypes.DEFAULT_TYPE):
    """Admin yuklagan savollarni guruhga non-anonymous quiz poll
    sifatida ketma-ket yuboradi. Har bir poll uchun belgilangan vaqt
    (poll_seconds) o'tgach keyingisi yuboriladi."""
    questions = context.bot_data.get("daily_questions")
    poll_seconds = context.bot_data.get("daily_poll_seconds", DEFAULT_POLL_SECONDS)
    if not questions:
        logging.info("Kunlik savollar yuklanmagan, test yuborilmadi.")
        return

    test_date = datetime.now().date().isoformat()
    context.bot_data["daily_test_date"] = test_date
    context.bot_data["daily_poll_map"] = {}     # poll_id -> {"answer": idx, "q_index": i}
    context.bot_data["daily_scores"] = {}       # user_id -> {"username":, "full_name":, "correct": 0, "total":0}

    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=f"📝 Bugungi test boshlandi! Jami {len(questions)} ta savol.\n"
                 f"Har bir savolga {poll_seconds} soniya vaqt beriladi. Omad! 🍀"
        )
    except Exception as e:
        logging.warning(f"Guruhga boshlanish xabari yuborilmadi: {e}")

    for i, q in enumerate(questions, start=1):
        try:
            message = await context.bot.send_poll(
                chat_id=GROUP_CHAT_ID,
                question=f"{i}/{len(questions)}) {q['q']}",
                options=q["options"],
                type="quiz",
                correct_option_id=q["answer"],
                is_anonymous=False,
                open_period=poll_seconds,
            )
            context.bot_data["daily_poll_map"][message.poll.id] = {
                "answer": q["answer"],
                "q_index": i,
            }
        except Exception as e:
            logging.warning(f"Poll yuborilmadi (savol {i}): {e}")

        # Keyingi savol uchun kutish (poll_seconds + biroz qo'shimcha)
        await asyncio.sleep(poll_seconds + 2)

    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text="✅ Test tugadi! Natijalar tez orada e'lon qilinadi."
    )


async def poll_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi pollga javob berganda chaqiriladi (non-anonymous poll
    bo'lgani uchun bot kim javob berganini bilishi mumkin)."""
    poll_answer = update.poll_answer
    poll_id = poll_answer.poll_id
    user = poll_answer.user

    poll_map = context.bot_data.get("daily_poll_map", {})
    info = poll_map.get(poll_id)
    if not info:
        return

    scores = context.bot_data.setdefault("daily_scores", {})
    record = scores.setdefault(user.id, {
        "username": user.username or "",
        "full_name": f"{user.first_name or ''} {user.last_name or ''}".strip(),
        "correct": 0,
        "total": 0,
    })

    record["total"] += 1
    if poll_answer.option_ids and poll_answer.option_ids[0] == info["answer"]:
        record["correct"] += 1


async def announce_daily_leaderboard(context: ContextTypes.DEFAULT_TYPE):
    """Kunlik test natijalarini guruhga va adminga reyting shaklida yuboradi,
    har bir ishtirokchining @username'i va nechanchi o'rinda turgani bilan."""
    scores = context.bot_data.get("daily_scores", {})
    if not scores:
        text = "Bugun hech kim testda ishtirok etmadi."
    else:
        ranked = sorted(scores.values(), key=lambda r: r["correct"], reverse=True)
        lines = ["🏆 BUGUNGI TEST NATIJALARI 🏆\n"]
        for i, r in enumerate(ranked, start=1):
            uname = f"@{r['username']}" if r["username"] else r["full_name"]
            lines.append(f"{i}-o'rin: {uname} — {r['correct']}/{r['total']} to'g'ri javob")
        text = "\n".join(lines)

        # Natijalarni bazaga ham saqlaymiz
        for uid, r in scores.items():
            save_weekly_result(
                telegram_id=uid,
                username=r["username"],
                full_name=r["full_name"],
                score=r["correct"],
                total=r["total"],
                duration_seconds=0,
            )

    # Guruhga yuborish
    try:
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=text)
    except Exception as e:
        logging.warning(f"Reyting guruhga yuborilmadi: {e}")

    # Adminga ham yuborish
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=text)
    except Exception as e:
        logging.warning(f"Reyting adminga yuborilmadi: {e}")

    # Keyingi kun uchun tozalash
    context.bot_data["daily_scores"] = {}
    context.bot_data["daily_poll_map"] = {}


# ============================================================
# JOB QUEUE: HAR KUNI 20:00DA AVTOMATIK YUBORISH
# ============================================================

async def daily_test_job(context: ContextTypes.DEFAULT_TYPE):
    await send_daily_test_to_group(context)


async def daily_leaderboard_job(context: ContextTypes.DEFAULT_TYPE):
    await announce_daily_leaderboard(context)


# ============================================================
# MAIN
# ============================================================

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_level)],
            ASK_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, start_test)],
            TESTING: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
            ASK_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, give_recommendation)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)

    # Admin: .txt fayl yuklash orqali kunlik test savollarini belgilash
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Admin buyruqlari (sinov uchun)
    app.add_handler(CommandHandler("test_yubor", manual_send_daily))
    app.add_handler(CommandHandler("reyting", manual_leaderboard))

    # Guruhdagi poll javoblarini ushlab olish
    from telegram.ext import PollAnswerHandler
    app.add_handler(PollAnswerHandler(poll_answer_handler))

    # ---- JOB QUEUE: har kuni 20:00da avtomatik yuborish ----
    job_queue = app.job_queue
    job_queue.run_daily(daily_test_job, time=dtime(hour=20, minute=0))
    # Reytingni testdan keyin (taxminan 10 ta savol x 35 sek + bo'sh joy) e'lon qilish
    job_queue.run_daily(daily_leaderboard_job, time=dtime(hour=20, minute=45))

    app.run_polling()


if __name__ == "__main__":
    main()
