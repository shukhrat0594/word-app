"""Bot matnlari: o'zbekcha va ruscha. `t(til, kalit, **qiymatlar)`."""

TILLAR = ("uz", "ru")

MATNLAR = {
    "til_tanlang": {
        "uz": "Tilni tanlang / Выберите язык",
        "ru": "Tilni tanlang / Выберите язык",
    },
    "salom_telefon": {
        "uz": "Assalomu alaykum! Farzandingiz haqida xabar olish uchun telefon raqamingizni ulashing "
              "(pastdagi tugma orqali).\n\nTelegram tasdiq so'rashi mumkin — «Ulashish» "
              "(Поделиться / Share) tugmasini bosing.",
        "ru": "Здравствуйте! Чтобы получать сообщения о вашем ребёнке, поделитесь номером телефона "
              "(кнопка внизу).\n\nTelegram может запросить подтверждение — нажмите «Поделиться» "
              "(Ulashish / Share).",
    },
    "telefon_tugma": {"uz": "📱 Raqamni ulashish", "ru": "📱 Поделиться номером"},
    "begona_kontakt": {
        "uz": "Iltimos, faqat o'zingizning raqamingizni ulashing (pastdagi tugma orqali).",
        "ru": "Пожалуйста, поделитесь только своим номером (кнопка внизу).",
    },
    "ulandi": {
        "uz": "✅ Ulandi: {ismlar}.\nEndi davomat, to'lov va natijalar haqida xabar olasiz.\n\n"
              "/farzandlarim — ro'yxat, /yordam — buyruqlar.",
        "ru": "✅ Подключено: {ismlar}.\nТеперь вы будете получать сообщения о посещаемости, оплате и "
              "результатах.\n\n/farzandlarim — список, /yordam — команды.",
    },
    "farzand_ism_so": {
        "uz": "Raqamingiz bo'yicha farzand topilmadi. Farzandingizning ism-familiyasini yozing "
              "(masalan: Aziz Karimov).",
        "ru": "По вашему номеру ребёнок не найден. Напишите имя и фамилию ребёнка "
              "(например: Aziz Karimov).",
    },
    "farzand_sana_so": {
        "uz": "Tug'ilgan sanasini yozing (kk.oo.yyyy, masalan: 16.01.2010).",
        "ru": "Напишите дату рождения (дд.мм.гггг, например: 16.01.2010).",
    },
    "ism_xato": {
        "uz": "Iltimos, farzandingizning ism-familiyasini harflar bilan yozing.",
        "ru": "Пожалуйста, напишите имя и фамилию ребёнка буквами.",
    },
    "sana_xato": {
        "uz": "Sanani kk.oo.yyyy ko'rinishida yozing, masalan: 16.01.2010.",
        "ru": "Напишите дату в формате дд.мм.гггг, например: 16.01.2010.",
    },
    # Topildi/topilmadi ATAYLAB aytilmaydi: begona odam kim o'qishini aniqlay olmasin.
    "sorov_yuborildi": {
        "uz": "So'rovingiz markaz adminlariga yuborildi. Ular tekshirib, sizni ulab beradi — natija shu "
              "yerda xabar qilinadi.",
        "ru": "Ваш запрос отправлен администраторам центра. Они проверят и подключат вас — результат "
              "придёт сюда.",
    },
    "urinish_kop": {
        "uz": "Urinishlar soni ko'payib ketdi. Iltimos, ertaga qayta urinib ko'ring yoki markazga murojaat "
              "qiling.",
        "ru": "Слишком много попыток. Пожалуйста, попробуйте завтра или обратитесь в центр.",
    },
    "farzandlar": {"uz": "Farzandlaringiz:\n{royxat}", "ru": "Ваши дети:\n{royxat}"},
    "farzand_yoq": {
        "uz": "Hali hech kim ulanmagan. /start ni bosing.",
        "ru": "Пока никто не подключён. Нажмите /start.",
    },
    "til_ozgardi": {"uz": "Til o'zgartirildi: o'zbekcha.", "ru": "Язык изменён: русский."},
    "yordam": {
        "uz": "Buyruqlar:\n/farzandlarim — ulangan farzandlar\n/til — tilni almashtirish\n"
              "/start — boshidan boshlash\n\nSavollar bo'lsa — markazga murojaat qiling.",
        "ru": "Команды:\n/farzandlarim — подключённые дети\n/til — сменить язык\n"
              "/start — начать сначала\n\nЕсли есть вопросы — обратитесь в центр.",
    },
    "tugma_farzandlar": {"uz": "👨‍👩‍👧 Farzandlarim", "ru": "👨‍👩‍👧 Мои дети"},
    "tugma_til": {"uz": "🌐 Til", "ru": "🌐 Язык"},
    "tugma_yordam": {"uz": "ℹ️ Yordam", "ru": "ℹ️ Помощь"},
    # Davomat xabarlari. {kun} — "bugun" yoki "05.10.2026 kuni" (tilga qarab).
    "davomat_kelmadi": {
        "uz": "⚠️ {ism} {kun} «{guruh}» guruhida darsga kelmadi.",
        "ru": "⚠️ {ism} {kun} отсутствовал(а) на занятии в группе «{guruh}».",
    },
    "davomat_kechikdi": {
        "uz": "⏰ {ism} {kun} «{guruh}» guruhidagi darsga kechikib keldi.",
        "ru": "⏰ {ism} {kun} опоздал(а) на занятие в группе «{guruh}».",
    },
    "davomat_sababli": {
        "uz": "ℹ️ {ism} {kun} «{guruh}» guruhida sababli kelmadi.",
        "ru": "ℹ️ {ism} {kun} отсутствовал(а) по уважительной причине (группа «{guruh}»).",
    },
    # To'lov va qarz
    "tolov_qabul": {
        "uz": "✅ {ism} uchun {summa} so'm to'lov qabul qilindi ({sana}, «{guruh}» guruhi). Rahmat!",
        "ru": "✅ Оплата за {ism} принята: {summa} сум ({sana}, группа «{guruh}»). Спасибо!",
    },
    "qarz_eslatma": {
        "uz": "💳 Eslatma: {ism} hisobida {summa} so'm qarzdorlik bor. Iltimos, to'lovni amalga oshiring. "
              "Savol bo'lsa — markazga murojaat qiling.",
        "ru": "💳 Напоминание: на счёте {ism} задолженность {summa} сум. Пожалуйста, произведите оплату. "
              "Если есть вопросы — обратитесь в центр.",
    },
    # Natijalar yig'masi. {davr} — "kunlik" (so'nggi 24 soat) yoki "01.10–05.10 kunlardagi".
    "natija_yigma": {
        "uz": "📊 {ism}: {davr} natijalar\n{qatorlar}",
        "ru": "📊 {ism}: результаты {davr}\n{qatorlar}",
    },
    "natija_kunlik": {"uz": "kunlik", "ru": "за день"},
    "natija_davr": {"uz": "{boshi}–{oxiri} kunlardagi", "ru": "за {boshi}–{oxiri}"},
    "natija_mashq": {"uz": "• Mashqlar: {soni} ta", "ru": "• Упражнения: {soni}"},
    "natija_mashq_foiz": {
        "uz": "• Mashqlar: {soni} ta, o'rtacha natija {foiz}%",
        "ru": "• Упражнения: {soni}, средний результат {foiz}%",
    },
    "natija_band": {"uz": "• {nom}: {soni} ta, band {band}", "ru": "• {nom}: {soni}, band {band}"},
    "tushunmadim": {
        "uz": "Tushunmadim. Buyruqlar uchun /yordam ni bosing.",
        "ru": "Не понял. Команды — /yordam.",
    },
    # Admin qarori (ota-onaga xabar)
    "admin_ulandi": {
        "uz": "✅ Markaz admini sizni ulab berdi: {ismlar}.\nEndi davomat, to'lov va natijalar haqida "
              "xabar olasiz.",
        "ru": "✅ Администратор центра подключил вас: {ismlar}.\nТеперь вы будете получать сообщения "
              "о посещаемости, оплате и результатах.",
    },
    "admin_rad": {
        "uz": "Afsuski, so'rovingizni tasdiqlab bo'lmadi. Iltimos, markazga murojaat qiling.",
        "ru": "К сожалению, запрос подтвердить не удалось. Пожалуйста, обратитесь в центр.",
    },
}


def t(til, kalit, **qiymatlar):
    ma = MATNLAR[kalit]
    matn = ma.get(til) or ma["uz"]
    return matn.format(**qiymatlar) if qiymatlar else matn


# "/" bosilganda Telegram ko'rsatadigan buyruqlar ro'yxati (BotFather menyusi, `setMyCommands`).
BUYRUQLAR = {
    "uz": [
        ("start", "Boshlash"),
        ("farzandlarim", "Ulangan farzandlarim"),
        ("til", "Tilni o'zgartirish"),
        ("yordam", "Buyruqlar ro'yxati"),
    ],
    "ru": [
        ("start", "Начать"),
        ("farzandlarim", "Мои дети"),
        ("til", "Сменить язык"),
        ("yordam", "Список команд"),
    ],
}


def kun_matni(til, sana, bugun):
    """Xabardagi sana: bugun bo'lsa "bugun" / "сегодня", aks holda aniq sana."""
    if sana == bugun:
        return "bugun" if til == "uz" else "сегодня"
    matn = sana.strftime("%d.%m.%Y")
    return f"{matn} kuni" if til == "uz" else matn
