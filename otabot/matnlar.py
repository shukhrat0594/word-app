"""Bot matnlari: o'zbekcha va ruscha. `t(til, kalit, **qiymatlar)`."""

TILLAR = ("uz", "ru")

MATNLAR = {
    "til_tanlang": {
        "uz": "Tilni tanlang / Выберите язык",
        "ru": "Tilni tanlang / Выберите язык",
    },
    "salom_telefon": {
        "uz": "Assalomu alaykum! Farzandingiz haqida xabar olish uchun telefon raqamingizni ulashing "
              "(pastdagi tugma orqali).",
        "ru": "Здравствуйте! Чтобы получать сообщения о вашем ребёнке, поделитесь номером телефона "
              "(кнопка внизу).",
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
        "uz": "Buyruqlar:\n/farzandlarim — ulangan farzandlar\n/til — tilni almashtirish\n"
              "/stop — xabarlarni to'xtatish\n/start — qayta yoqish",
        "ru": "Команды:\n/farzandlarim — подключённые дети\n/til — сменить язык\n"
              "/stop — остановить сообщения\n/start — включить снова",
    },
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
