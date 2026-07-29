"""Gunicorn sozlamalari (2026-07-27).

Nega bu fayl bor: prod'da IELTS Writing testini tekshirganda talaba
"Xatolik yuz berdi" xabarini olardi. Render logi sababni ko'rsatdi —
`gunicorn/workers/base.py handle_abort -> SystemExit`, ya'ni worker AI
javobini kutayotib **timeout bo'yicha o'ldirilgan**. Gunicorn'ning
standart timeout'i 30 sekund, bir so'rovda esa 2 (Writing) yoki 3
(Speaking) ta ketma-ket AI chaqiruvi bo'ladi.

Nega dashboard'dagi start command emas: gunicorn ishga tushganda ishchi
katalogdan `gunicorn.conf.py` faylini O'ZI topib o'qiydi
(`gunicorn/config.py: get_default_config_file`). Shu sababli sozlama
kod bilan birga deploy bo'ladi va Render panelida qo'lda o'zgartirish
kerak emas — yangi muhitga ko'chirilganda ham yo'qolmaydi.

ESLATMA: buyruq satrida berilgan flaglar bu fayldan USTUN turadi. Ya'ni
start command'ga `--timeout` qo'shilsa, quyidagi qiymat e'tiborsiz
qoladi.
"""

# Bitta AI chaqiruvi odatda 2-4 sekund, lekin sinovda 45.8 sekundlik
# javob ham kuzatilgan. Eng yomon holat: 3 qism x 2 urinish x 40s
# (SOROV_TIMEOUT_MS) = 240 sekund. 300 shuni ham qamrab oladi.
timeout = 300

# Worker to'xtatilganda (deploy/qayta ishga tushirish) tugallanmagan
# so'rovni kutish vaqti — timeout bilan bir xil bo'lsin, aks holda
# baholanayotgan insho yarim yo'lda uzilib qoladi.
graceful_timeout = 300

# Worker SONI ATAYLAB belgilanmadi — u Render muhitiga bog'liq (xotira/
# CPU) va start command'da berilgan bo'lishi mumkin.

# 2026-07-28: Kurslar blok formatida ZIP yuklaganda (courses/blok_views.py)
# real hodisa kuzatildi — bitta sahifani AI'ga yuborish ~2 daqiqa davom
# etadi. Standart `sync` worker turi bu vaqt ichida BUTUN jarayonni
# bloklaydi: bitta worker bo'lsa, boshqa hech qanday so'rov (jumladan
# Render'ning o'z holat tekshiruvi) javob ololmaydi. Render buni "servis
# javob bermayapti" deb, KONTEYNERNI QAYTA ISHGA TUSHIRDI — gunicorn
# logida hech qanday Python xatosi (traceback) yo'q edi, faqat
# "==> Running 'gunicorn ...'" qayta paydo bo'ldi (Render'ning tashqi
# xabari, bizning kodimiz emas).
#
# `gthread` worker turi — bir nechta OQIM (thread) bitta jarayon ichida.
# Xotira sarfi deyarli oshmaydi (oqimlar xotirani bo'lishadi, alohida
# `sync` worker esa BUTUN Django + kutubxonalarni QAYTADAN yuklardi).
# AI so'rovi TARMOQ orqali kutilayotganda Python GIL bo'shaydi, shuning
# uchun boshqa oqim (masalan holat tekshiruvi) shu vaqtda javob bera oladi.
worker_class = "gthread"
threads = 4
