import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler,
    ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = "8661822300:AAG0epifmA0C_6OeMuPh9Ll-yD6LQZihyvU"

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

# Tavsiyalar: daraja + sabab kombinatsiyasi bo'yicha
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


def level_keyboard():
    return ReplyKeyboardMarkup(
        [["초급 (Boshlang'ich)"], ["중급 (O'rta)"], ["고급 (Yuqori)"]],
        resize_keyboard=True, one_time_keyboard=True
    )


def reason_keyboard():
    return ReplyKeyboardMarkup(
        [[r] for r in REASONS], resize_keyboard=True, one_time_keyboard=True
    )


# ---------- HANDLERLAR ----------

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


LEVEL_MAP = {
    "초급 (Boshlang'ich)": "초급",
    "중급 (O'rta)": "중급",
    "고급 (Yuqori)": "고급",
}


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

    level_recs = RECOMMENDATIONS.get(level, {})
    rec = level_recs.get(reason, level_recs["default"])

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
        f"Omad tilaymiz! Qaytadan boshlash uchun /start buyrug'ini bosing."
    )

    await update.message.reply_text(summary, reply_markup=None)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi. Qayta boshlash uchun /start ni bosing.")
    return ConversationHandler.END


def main():
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
    app.run_polling()


if __name__ == "__main__":
    main()
