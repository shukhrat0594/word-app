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
    "to_xtadi": {
        "uz": "Xabarlar o'chirildi. Qayta yoqish uchun /start ni bosing.",
        "ru": "Сообщения отключены. Чтобы включить снова, нажмите /start.",
    },
    "til_ozgardi": {"uz": "Til o'zgartirildi: o'zbekcha.", "ru": "Язык изменён: русский."},
    "yordam": {
        "uz": "Buyruqlar:\n/farzandlarim — ulangan farzandlar\n/sozlamalar — qaysi xabarlarni olish\n"
              "/til — tilni almashtirish\n/stop — xabarlarni to'xtatish\n/start — qayta yoqish",
        "ru": "Команды:\n/farzandlarim — подключённые дети\n/sozlamalar — какие сообщения получать\n"
              "/til — сменить язык\n/stop — остановить сообщения\n/start — включить снова",
    },
    "tugma_farzandlar": {"uz": "👨‍👩‍👧 Farzandlarim", "ru": "👨‍👩‍👧 Мои дети"},
    "tugma_til": {"uz": "🌐 Til", "ru": "🌐 Язык"},
    "tugma_yordam": {"uz": "ℹ️ Yordam", "ru": "ℹ️ Помощь"},
    "tugma_stop": {"uz": "⏸ Xabarlarni to'xtatish", "ru": "⏸ Остановить сообщения"},
    "tugma_start": {"uz": "▶️ Xabarlarni qayta yoqish", "ru": "▶️ Включить сообщения"},
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
    # Natijalar yig'masi. {davr} — "bugungi" yoki "01.10–05.10".
    "natija_yigma": {
        "uz": "📊 {ism}: {davr} natijalar\n{qatorlar}",
        "ru": "📊 {ism}: результаты {davr}\n{qatorlar}",
    },
    "natija_bugun": {"uz": "bugungi", "ru": "за сегодня"},
    "natija_davr": {"uz": "{boshi}–{oxiri} kunlardagi", "ru": "за {boshi}–{oxiri}"},
    "natija_mashq": {"uz": "• Mashqlar: {soni} ta", "ru": "• Упражнения: {soni}"},
    "natija_mashq_foiz": {
        "uz": "• Mashqlar: {soni} ta, o'rtacha natija {foiz}%",
        "ru": "• Упражнения: {soni}, средний результат {foiz}%",
    },
    "natija_band": {"uz": "• {nom}: {soni} ta, band {band}", "ru": "• {nom}: {soni}, band {band}"},
    # Ota-ona sozlamalari (/sozlamalar)
    "sozlamalar": {
        "uz": "⚙️ Qaysi xabarlarni olishni tanlang (bosib yoqing/o'chiring):",
        "ru": "⚙️ Выберите, какие сообщения получать (нажмите, чтобы включить/выключить):",
    },
    "toifa_davomat": {"uz": "Davomat", "ru": "Посещаемость"},
    "toifa_tolov": {"uz": "To'lovlar", "ru": "Оплаты"},
    "toifa_qarz": {"uz": "Qarz eslatmasi", "ru": "Напоминание о долге"},
    "toifa_natija": {"uz": "Natijalar", "ru": "Результаты"},
    "toifa_markaz_ochirgan": {
        "uz": "Bu xabarlarni markaz hozircha yubormaydi.",
        "ru": "Центр пока не отправляет эти сообщения.",
    },
    "tugma_sozlamalar": {"uz": "⚙️ Sozlamalar", "ru": "⚙️ Настройки"},
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
        ("start", "Boshlash / qayta yoqish"),
        ("farzandlarim", "Ulangan farzandlarim"),
        ("sozlamalar", "Qaysi xabarlarni olish"),
        ("til", "Tilni o'zgartirish"),
        ("stop", "Xabarlarni to'xtatish"),
        ("yordam", "Buyruqlar ro'yxati"),
    ],
    "ru": [
        ("start", "Начать / включить снова"),
        ("farzandlarim", "Мои дети"),
        ("sozlamalar", "Какие сообщения получать"),
        ("til", "Сменить язык"),
        ("stop", "Остановить сообщения"),
        ("yordam", "Список команд"),
    ],
}


def kun_matni(til, sana, bugun):
    """Xabardagi sana: bugun bo'lsa "bugun" / "сегодня", aks holda aniq sana."""
    if sana == bugun:
        return "bugun" if til == "uz" else "сегодня"
    matn = sana.strftime("%d.%m.%Y")
    return f"{matn} kuni" if til == "uz" else matn
