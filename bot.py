import asyncio
import logging
import os
import random
import re
import sqlite3
import time
from datetime import datetime, time as dtime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters, PollAnswerHandler
)
from telegram.error import Forbidden, BadRequest

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8661822300:AAG0epifmA0C_6OeMuPh9Ll-yD6LQZihyvU"

# --------- SOZLAMALAR ---------
ADMIN_ID = 988635477  # admin Telegram ID

# Majburiy obuna kanali (foydalanuvchi botdan foydalanishdan oldin a'zo bo'lishi shart)
REQUIRED_CHANNEL = "@Korea_book"

CHANNELS = {
    "초급": "https://t.me/+988635477",   # <-- darajaga mos kanal linklari (keyin alohida qo'ying)
    "중급": "https://t.me/+988635477",
    "고급": "https://t.me/+988635477",
    "default": "https://t.me/+988635477",
}

# Mini App (Web App) manzili - GitHub Pages / Replit static hosting orqali joylashtiriladi
MINI_APP_URL = "https://uzkor.github.io/Telegram-bot/webapp/"  # GitHub Pages orqali hostlangan Mini App

# Kunlik test poll'lari yuboriladigan guruh ID
GROUP_CHAT_ID = -1001297463776

DEFAULT_POLL_SECONDS_GROUP = 35   # kunlik guruh testi uchun (eski standart, endi LEVEL_SECONDS ishlatiladi)
DEFAULT_POLL_SECONDS_PERSONAL = 30  # shaxsiy /start testi uchun standart (agar daraja aniqlanmasa)

# Har bir daraja uchun alohida vaqt (soniya) - oson tezroq, qiyin sekinroq
LEVEL_SECONDS = {
    "초급": 20,
    "중급": 30,
    "고급": 45,
}
DAILY_GROUP_QUESTION_COUNT = 10
PERSONAL_TEST_QUESTION_COUNT = 10

DB_PATH = "bot_database.db"

# ---------- HOLATLAR ----------
(ASK_NAME, ASK_REASON) = range(2)

# Daraja darajalari va ularning og'irligi (tartibi)
LEVELS = ["초급", "중급", "고급"]
LEVEL_INDEX = {"초급": 0, "중급": 1, "고급": 2}

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
        CREATE TABLE IF NOT EXISTS daily_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            username TEXT,
            full_name TEXT,
            score INTEGER,
            total INTEGER,
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


def save_daily_result(telegram_id, username, full_name, score, total, test_date):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO daily_results (telegram_id, username, full_name, score, total, test_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (telegram_id, username, full_name, score, total, test_date))
    conn.commit()
    conn.close()


# ============================================================
# 100 TA SAVOLNI TXT DAN O'QISH
# ============================================================
#
# TXT FORMAT NAMUNASI (har savol orasida BO'SH QATOR bo'lishi shart):
#
# DARAJA: oson
# 1) 안녕하세요 nimani bildiradi?
# A) Salom
# B) Rahmat
# C) Kechirasiz
# D) Xayr
# JAVOB: A
#
# DARAJA: orta
# 2) ...
#
# DARAJA: qiyin
# 3) ...
#
# (oson -> 초급, orta -> 중급, qiyin -> 고급)

DIFFICULTY_TO_LEVEL = {"oson": "초급", "orta": "중급", "qiyin": "고급"}


def parse_question_bank(text: str):
    """100ta (yoki istalgan miqdordagi) savolni DARAJA: bilan parse qiladi.
    Natija: {"초급": [...], "중급": [...], "고급": [...]}"""
    bank = {"초급": [], "중급": [], "고급": []}
    blocks = re.split(r"\n\s*\n", text.strip())
    for block in blocks:
        lines = [l.strip() for l in block.strip().split("\n") if l.strip()]
        if len(lines) < 7:
            continue

        m = re.match(r"^DARAJA:\s*(oson|orta|qiyin)$", lines[0], re.IGNORECASE)
        if not m:
            continue
        level = DIFFICULTY_TO_LEVEL[m.group(1).lower()]

        q_text = re.sub(r"^\d+\)\s*", "", lines[1])
        options = []
        for line in lines[2:6]:
            m2 = re.match(r"^([A-D])\)\s*(.+)$", line, re.IGNORECASE)
            if m2:
                options.append(m2.group(2).strip())

        ans_line = lines[6] if len(lines) > 6 else ""
        m2 = re.match(r"^JAVOB:\s*([A-D])$", ans_line, re.IGNORECASE)
        if m2 and len(options) == 4:
            answer_idx = "ABCD".index(m2.group(1).upper())
            bank[level].append({"q": q_text, "options": options, "answer": answer_idx})

    return bank


# ============================================================
# OBUNANI TEKSHIRISH (@Korea_book)
# ============================================================

async def is_subscribed(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logging.warning(f"Obuna tekshirishda xato: {e}")
        # Agar bot kanalga admin sifatida qo'shilmagan bo'lsa, xato chiqadi.
        # Xavfsizlik uchun False qaytaramiz (obuna yo'q deb hisoblaymiz).
        return False


async def send_subscription_prompt(update: Update):
    await update.message.reply_text(
        f"📢 Botdan foydalanish uchun avval {REQUIRED_CHANNEL} kanaliga a'zo bo'ling!\n\n"
        f"👉 https://t.me/{REQUIRED_CHANNEL.lstrip('@')}\n\n"
        f"A'zo bo'lgandan keyin qaytadan /start buyrug'ini bosing."
    )


# ============================================================
# /start -> ISM SO'RASH -> ADAPTIV TEST (POLL, DM)
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not await is_subscribed(context, user.id):
        await send_subscription_prompt(update)
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data["telegram_id"] = user.id
    context.user_data["telegram_username"] = user.username or ""

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Ilovani ochish (Kitoblar, Darslar)", web_app=WebAppInfo(url=MINI_APP_URL))]
    ])

    await update.message.reply_text(
        "Salom! Koreys tili darajangizni aniqlash testiga xush kelibsiz.\n\n"
        "👉 Pastdagi tugma orqali ilovani ochib, kitoblar va video darslarni ko'rishingiz mumkin.\n\n"
        "Test boshlash uchun ism va familyangizni kiriting:",
        reply_markup=keyboard
    )
    return ASK_NAME


async def begin_adaptive_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["full_name"] = update.message.text.strip()

    bank = context.bot_data.get("question_bank")
    if not bank or not any(bank.values()):
        await update.message.reply_text(
            "❌ Hozircha test savollari yuklanmagan. Iltimos, keyinroq urinib ko'ring."
        )
        return ConversationHandler.END

    # Test holatini tayyorlash
    context.user_data["adaptive_level_idx"] = 0  # 0=초급, 1=중급, 2=고급 - boshlang'ich daraja
    context.user_data["adaptive_q_num"] = 0      # nechanchi savol (0-9)
    context.user_data["adaptive_correct"] = 0
    context.user_data["used_questions"] = {0: set(), 1: set(), 2: set()}
    context.user_data["personal_poll_map"] = {}

    await update.message.reply_text(
        f"Rahmat, {context.user_data['full_name']}!\n\n"
        f"Test boshlanadi. Jami {PERSONAL_TEST_QUESTION_COUNT} ta savol.\n"
        f"Vaqt savol qiyinligiga qarab beriladi: 초급 — 20 sek, 중급 — 30 sek, 고급 — 45 sek.\n"
        f"Savol qiyinligi javoblaringizga qarab moslashadi. Omad! 🍀"
    )

    await send_adaptive_question(update.effective_chat.id, context)
    return ConversationHandler.END  # endi javoblar poll_answer_handler orqali keladi


def pick_question(context, level_idx):
    """Berilgan daraja indeksidan (yoki yaqinidan) ishlatilmagan savol tanlaydi."""
    bank = context.bot_data["question_bank"]
    used = context.user_data["used_questions"]

    # Avval xohlagan darajadan, bo'lmasa qo'shni darajalardan qidiramiz
    order = [level_idx]
    if level_idx - 1 >= 0:
        order.append(level_idx - 1)
    if level_idx + 1 <= 2:
        order.append(level_idx + 1)
    if level_idx - 1 < 0 and level_idx + 1 <= 2:
        pass

    for idx in order:
        level_name = LEVELS[idx]
        questions = bank.get(level_name, [])
        available = [i for i in range(len(questions)) if i not in used[idx]]
        if available:
            qi = random.choice(available)
            used[idx].add(qi)
            return idx, questions[qi]

    return None, None


async def send_adaptive_question(chat_id, context: ContextTypes.DEFAULT_TYPE):
    q_num = context.user_data["adaptive_q_num"]

    if q_num >= PERSONAL_TEST_QUESTION_COUNT:
        await finish_adaptive_test(chat_id, context)
        return

    level_idx = context.user_data["adaptive_level_idx"]
    chosen_idx, q = pick_question(context, level_idx)

    if q is None:
        # Savollar tugagan bo'lsa, testni shu yergacha tugatamiz
        context.user_data["adaptive_q_num"] = PERSONAL_TEST_QUESTION_COUNT
        await finish_adaptive_test(chat_id, context)
        return

    chosen_level_name = LEVELS[chosen_idx]
    poll_seconds = LEVEL_SECONDS.get(chosen_level_name, DEFAULT_POLL_SECONDS_PERSONAL)

    message = await context.bot.send_poll(
        chat_id=chat_id,
        question=f"{q_num + 1}/{PERSONAL_TEST_QUESTION_COUNT}) {q['q']}",
        options=q["options"],
        type="quiz",
        correct_option_id=q["answer"],
        is_anonymous=False,
        open_period=poll_seconds,
    )
    context.user_data["personal_poll_map"][message.poll.id] = {
        "answer": q["answer"],
        "level_idx": chosen_idx,
    }
    context.user_data["current_poll_id"] = message.poll.id
    context.user_data["current_poll_deadline"] = time.time() + poll_seconds + 1


async def personal_poll_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shaxsiy adaptiv test uchun poll javoblarini ushlab oladi."""
    poll_answer = update.poll_answer
    poll_id = poll_answer.poll_id
    user = poll_answer.user

    udata = context.user_data
    poll_map = udata.get("personal_poll_map", {})
    info = poll_map.get(poll_id)
    if not info:
        return  # bu poll guruh testiga tegishli bo'lishi mumkin

    chosen_idx = info["level_idx"]
    correct = bool(poll_answer.option_ids and poll_answer.option_ids[0] == info["answer"])

    if correct:
        udata["adaptive_correct"] += 1
        # Keyingi savol qiyinroq (lekin 고급dan oshmaydi)
        udata["adaptive_level_idx"] = min(chosen_idx + 1, 2)
    else:
        # Keyingi savol osonroq (lekin 초급dan pasaymaydi)
        udata["adaptive_level_idx"] = max(chosen_idx - 1, 0)

    udata["adaptive_q_num"] += 1
    del poll_map[poll_id]

    await send_adaptive_question(user.id, context)


async def finish_adaptive_test(chat_id, context: ContextTypes.DEFAULT_TYPE):
    udata = context.user_data
    score = udata.get("adaptive_correct", 0)
    total = PERSONAL_TEST_QUESTION_COUNT

    # Final darajani aniqlash: foydalanuvchi qaysi daraja savollariga
    # qiyinroq o'tgani (adaptive_level_idx oxirgi holati) + umumiy ball asosida
    final_idx = udata.get("adaptive_level_idx", 0)

    if score >= 8:
        final_idx = min(final_idx + 1, 2) if final_idx < 2 else 2
    elif score <= 3:
        final_idx = max(final_idx - 1, 0)

    final_level = LEVELS[final_idx]

    if score >= 8:
        result_text = "A'lo natija! 잘했어요!"
    elif score >= 5:
        result_text = "Yaxshi natija, biroz mashq qilsangiz yanada yaxshi bo'ladi."
    else:
        result_text = "Asoslarni mustahkamlash tavsiya etiladi. 기초부터 다시!"

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"✅ Test yakunlandi!\n\n"
             f"Natija: {score}/{total}\n"
             f"Aniqlangan daraja: {final_level}\n"
             f"{result_text}\n\n"
             f"Endi, koreys tilini nima maqsadda o'rganayotganingizni yozing.\n"
             f"Variantlar: {', '.join(REASONS)}\n\n"
             f"(yozma ravishda yuqoridagi variantlardan birini kiriting)"
    )

    udata["final_score"] = score
    udata["final_level"] = final_level
    udata["awaiting_reason"] = True


async def reason_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Foydalanuvchi test tugagandan keyin maqsadini matn orqali yozganda ishlaydi."""
    if not context.user_data.get("awaiting_reason"):
        return  # boshqa handlerlarga yo'l ochish kerak, lekin PTB buni avtomatik qiladi

    reason = update.message.text.strip()
    if reason not in REASONS:
        await update.message.reply_text(
            f"Iltimos, quyidagi variantlardan birini aynan shu shaklda yozing:\n"
            f"{', '.join(REASONS)}"
        )
        return

    user = update.effective_user
    level = context.user_data["final_level"]
    score = context.user_data["final_score"]

    save_user(
        telegram_id=user.id,
        username=user.username or "",
        full_name=context.user_data.get("full_name", ""),
        level=level,
        score=score,
        reason=reason,
    )

    level_recs = RECOMMENDATIONS.get(level, {})
    rec = level_recs.get(reason, level_recs["default"])
    channel_link = CHANNELS.get(level, CHANNELS["default"])

    summary = (
        f"📋 NATIJALAR XULOSASI\n\n"
        f"👤 Ism: {context.user_data.get('full_name','')}\n"
        f"🆔 Telegram: @{user.username or 'Yo' + chr(39) + 'q'} (ID: {user.id})\n"
        f"📊 Daraja: {level}\n"
        f"✅ Test natijasi: {score}/{PERSONAL_TEST_QUESTION_COUNT}\n"
        f"🎯 Maqsad: {reason}\n\n"
        f"💡 TAVSIYA:\n{rec['text']}\n\n"
        f"📚 Kitob (PDF): {rec['book']}\n"
        f"🎬 Video dars: {rec['video']}\n\n"
        f"📢 Darajangizga mos kanalga qo'shiling:\n{channel_link}\n\n"
        f"Omad tilaymiz! Qaytadan boshlash uchun /start buyrug'ini bosing."
    )
    await update.message.reply_text(summary)

    # Adminga xabar
    admin_msg = (
        f"🆕 YANGI TEST NATIJASI\n\n"
        f"👤 Ism: {context.user_data.get('full_name','')}\n"
        f"🆔 ID: {user.id}\n"
        f"📱 Username: @{user.username or 'Yo' + chr(39) + 'q'}\n"
        f"📊 Daraja: {level}\n"
        f"✅ Natija: {score}/{PERSONAL_TEST_QUESTION_COUNT}\n"
        f"🎯 Maqsad: {reason}"
    )
    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
    except Exception as e:
        logging.warning(f"Adminga xabar yuborilmadi: {e}")

    context.user_data["awaiting_reason"] = False


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi. Qayta boshlash uchun /start ni bosing.")
    return ConversationHandler.END


# ============================================================
# ADMIN: 100 TA SAVOLNI .TXT ORQALI YUKLASH
# ============================================================

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    bank = parse_question_bank(text)
    total = sum(len(v) for v in bank.values())

    if total == 0:
        await update.message.reply_text(
            "❌ Faylni o'qishda xato. Format quyidagicha bo'lishi kerak:\n\n"
            "DARAJA: oson\n"
            "1) Savol matni?\n"
            "A) Variant 1\n"
            "B) Variant 2\n"
            "C) Variant 3\n"
            "D) Variant 4\n"
            "JAVOB: A\n\n"
            "(DARAJA: oson/orta/qiyin, har savol orasida bo'sh qator bo'lishi kerak)"
        )
        return

    context.bot_data["question_bank"] = bank

    await update.message.reply_text(
        f"✅ Savollar bazasi yuklandi!\n\n"
        f"초급 (oson): {len(bank['초급'])} ta\n"
        f"중급 (orta): {len(bank['중급'])} ta\n"
        f"고급 (qiyin): {len(bank['고급'])} ta\n"
        f"Jami: {total} ta\n\n"
        f"Bu savollar:\n"
        f"- Har bir foydalanuvchining /start testida (adaptiv, 10ta savol)\n"
        f"- Har kuni 20:00da guruhga yuboriladigan kunlik testda (random 10ta)\n"
        f"Vaqt darajaga qarab: 초급 — 20 sek, 중급 — 30 sek, 고급 — 45 sek.\n"
        f"ishlatiladi.\n\n"
        f"Hoziroq guruh testini sinash uchun /test_yubor buyrug'ini ishlatishingiz mumkin."
    )


# ============================================================
# KUNLIK GURUH TESTI (RANDOM 10 TA, 20:00, POLL)
# ============================================================

async def send_daily_test_to_group(context: ContextTypes.DEFAULT_TYPE):
    bank = context.bot_data.get("question_bank")
    if not bank or not any(bank.values()):
        logging.info("Savollar bazasi yuklanmagan, kunlik test yuborilmadi.")
        return

    # Barcha savollarni daraja belgisi bilan birga bitta ro'yxatga yig'amiz
    all_questions = []
    for level_name, qs in bank.items():
        for q in qs:
            all_questions.append((level_name, q))

    count = min(DAILY_GROUP_QUESTION_COUNT, len(all_questions))
    selected = random.sample(all_questions, count)

    test_date = datetime.now().date().isoformat()
    context.bot_data["daily_test_date"] = test_date
    context.bot_data["daily_poll_map"] = {}
    context.bot_data["daily_scores"] = {}

    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=f"📝 Bugungi test boshlandi! Jami {count} ta savol.\n"
                 f"Vaqt qiyinlikka qarab beriladi: 초급 — 20 sek, 중급 — 30 sek, 고급 — 45 sek. Omad! 🍀"
        )
    except Exception as e:
        logging.warning(f"Guruhga boshlanish xabari yuborilmadi: {e}")

    for i, (level_name, q) in enumerate(selected, start=1):
        poll_seconds = LEVEL_SECONDS.get(level_name, DEFAULT_POLL_SECONDS_GROUP)
        try:
            message = await context.bot.send_poll(
                chat_id=GROUP_CHAT_ID,
                question=f"{i}/{count}) {q['q']}",
                options=q["options"],
                type="quiz",
                correct_option_id=q["answer"],
                is_anonymous=False,
                open_period=poll_seconds,
            )
            context.bot_data["daily_poll_map"][message.poll.id] = {"answer": q["answer"]}
        except Exception as e:
            logging.warning(f"Poll yuborilmadi (savol {i}): {e}")

        await asyncio.sleep(poll_seconds + 2)

    await context.bot.send_message(
        chat_id=GROUP_CHAT_ID,
        text="✅ Test tugadi! Natijalar tez orada e'lon qilinadi."
    )


async def group_poll_answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kunlik guruh testi uchun poll javoblarini ushlab oladi."""
    poll_answer = update.poll_answer
    poll_id = poll_answer.poll_id
    user = poll_answer.user

    poll_map = context.bot_data.get("daily_poll_map", {})
    info = poll_map.get(poll_id)
    if not info:
        return  # bu poll shaxsiy testga tegishli bo'lishi mumkin

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

        test_date = context.bot_data.get("daily_test_date") or datetime.now().date().isoformat()
        for uid, r in scores.items():
            save_daily_result(
                telegram_id=uid,
                username=r["username"],
                full_name=r["full_name"],
                score=r["correct"],
                total=r["total"],
                test_date=test_date,
            )

    try:
        await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=text)
    except Exception as e:
        logging.warning(f"Reyting guruhga yuborilmadi: {e}")

    try:
        await context.bot.send_message(chat_id=ADMIN_ID, text=text)
    except Exception as e:
        logging.warning(f"Reyting adminga yuborilmadi: {e}")

    context.bot_data["daily_scores"] = {}
    context.bot_data["daily_poll_map"] = {}


async def manual_send_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    bank = context.bot_data.get("question_bank")
    if not bank or not any(bank.values()):
        await update.message.reply_text("Hozircha savollar bazasi yuklanmagan. Avval .txt fayl yuboring.")
        return
    await update.message.reply_text("Test guruhga yuborilmoqda...")
    await send_daily_test_to_group(context)


async def manual_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        return
    await announce_daily_leaderboard(context)
    await update.message.reply_text("✅ Reyting e'lon qilindi.")


# ============================================================
# JOB QUEUE
# ============================================================

async def daily_test_job(context: ContextTypes.DEFAULT_TYPE):
    await send_daily_test_to_group(context)


async def daily_leaderboard_job(context: ContextTypes.DEFAULT_TYPE):
    await announce_daily_leaderboard(context)


# ============================================================
# COMBINED POLL ANSWER ROUTER
# ============================================================

async def poll_answer_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bitta poll_answer kelganda, u shaxsiy testga yoki guruh testiga
    tegishli ekanini aniqlab, mos handlerga yo'naltiradi."""
    poll_id = update.poll_answer.poll_id

    if poll_id in context.bot_data.get("daily_poll_map", {}):
        await group_poll_answer_handler(update, context)
        return

    if poll_id in context.user_data.get("personal_poll_map", {}):
        await personal_poll_answer_handler(update, context)
        return


# ============================================================
# MINI APP: KITOBLAR RO'YXATI VA WEB_APP_DATA QABULI
# ============================================================

# Mini App'dagi "requestBook(bookId)" chaqirig'iga mos kitob havolalari.
# Har bir qiymat Telegram fayl/kanal post linki bo'lishi mumkin.
BOOKS = {
    "topik": "https://t.me/korea_book/13859",
    "eps_topik": "https://t.me/korea_book/13745",
    "ttmik": "https://t.me/korea_book/13859",
    "klat": "https://t.me/korea_book/13745",
    "kiip": "https://t.me/korea_book/13859",
    "proverbs": "https://t.me/korea_book/13745",
    "grammar": "https://t.me/korea_book/13859",
    "dictionary": "https://t.me/korea_book/13745",
}

BOOK_NAMES = {
    "topik": "TOPIK to'plami",
    "eps_topik": "EPS-TOPIK qo'llanma",
    "ttmik": "TTMIK 이야기",
    "klat": "KLAT 시험",
    "kiip": "KIIP (사회통합프로그램)",
    "proverbs": "Proverbs & Idioms",
    "grammar": "Grammar books",
    "dictionary": "Dictionary books",
}


async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mini App ichidan tg.sendData() orqali kelgan so'rovlarni qabul qiladi."""
    import json
    raw = update.message.web_app_data.data
    try:
        data = json.loads(raw)
    except Exception:
        return

    action = data.get("action")
    payload = data.get("payload")
    user = update.effective_user

    if action == "get_book":
        link = BOOKS.get(payload)
        name = BOOK_NAMES.get(payload, "Kitob")
        if link:
            await update.message.reply_text(f"📚 {name}\n\n{link}")
        else:
            await update.message.reply_text("❌ Bu kitob hozircha mavjud emas.")

    elif action == "order_book":
        book_id = payload.get("bookId") if isinstance(payload, dict) else None
        book_name = payload.get("bookName") if isinstance(payload, dict) else "Noma'lum kitob"
        price = payload.get("price") if isinstance(payload, dict) else ""
        phone = payload.get("phone") if isinstance(payload, dict) else ""

        await update.message.reply_text(
            f"✅ Buyurtmangiz qabul qilindi!\n\n"
            f"📚 Kitob: {book_name}\n"
            f"💰 Narx: {price}\n"
            f"📞 Raqam: {phone}\n\n"
            f"Tez orada admin siz bilan bog'lanadi."
        )

        admin_msg = (
            f"🛒 YANGI BUYURTMA\n\n"
            f"📚 Kitob: {book_name}\n"
            f"💰 Narx: {price}\n"
            f"👤 Ism: {user.first_name or ''} {user.last_name or ''}\n"
            f"🆔 ID: {user.id}\n"
            f"📱 Username: @{user.username or 'Yo' + chr(39) + 'q'}\n"
            f"📞 Telefon: {phone}"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg)
        except Exception as e:
            logging.warning(f"Buyurtma haqida adminga xabar yuborilmadi: {e}")

    elif action == "start_test":
        await start(update, context)

    elif action == "test_yubor":
        if user.id == ADMIN_ID:
            await manual_send_daily(update, context)
        else:
            await update.message.reply_text("Bu funksiya faqat admin uchun.")

    elif action == "reyting":
        if user.id == ADMIN_ID:
            await manual_leaderboard(update, context)
        else:
            await update.message.reply_text("Bu funksiya faqat admin uchun.")

    elif action == "get_admin_stats":
        if user.id != ADMIN_ID:
            return
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        c.execute("SELECT level, COUNT(*) FROM users GROUP BY level")
        level_counts = dict(c.fetchall())
        conn.close()

        bank = context.bot_data.get("question_bank", {"초급": [], "중급": [], "고급": []})

        await update.message.reply_text(
            f"📊 Statistika\n\n"
            f"Jami ro'yxatdan o'tganlar: {total_users}\n"
            f"초급: {level_counts.get('초급', 0)}\n"
            f"중급: {level_counts.get('중급', 0)}\n"
            f"고급: {level_counts.get('고급', 0)}\n\n"
            f"🗂 Savollar bazasi:\n"
            f"초급 (oson): {len(bank.get('초급', []))} ta\n"
            f"중급 (orta): {len(bank.get('중급', []))} ta\n"
            f"고급 (qiyin): {len(bank.get('고급', []))} ta"
        )




def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, begin_adaptive_test)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)

    # Mini App'dan kelgan ma'lumotlar (web_app_data)
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))

    # Test tugagandan keyin maqsad (reason) matnini ushlab olish
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reason_text_handler))

    # Admin: 100ta savollik .txt yuklash
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    # Admin buyruqlari (sinov uchun)
    app.add_handler(CommandHandler("test_yubor", manual_send_daily))
    app.add_handler(CommandHandler("reyting", manual_leaderboard))

    # Barcha poll javoblari (shaxsiy + guruh) -> router
    app.add_handler(PollAnswerHandler(poll_answer_router))

    # ---- JOB QUEUE: har kuni 20:00da avtomatik yuborish ----
    job_queue = app.job_queue
    job_queue.run_daily(daily_test_job, time=dtime(hour=20, minute=0))
    job_queue.run_daily(daily_leaderboard_job, time=dtime(hour=20, minute=45))

    app.run_polling()


if __name__ == "__main__":
    main()
