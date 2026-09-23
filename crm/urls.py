"""CRM API yo'llari — hammasi `/api/crm/` prefiksi ostida.

Prefiks ATAYLAB alohida: mavjud `/api/...` yo'llari bilan hech qachon
aralashmaydi, ya'ni CRM olib tashlanganda LMS marshrutlariga tegilmaydi
(`config/urls.py` dan bitta qatorni o'chirish yetarli).
"""

from django.urls import path

from . import boshqaruv, views

app_name = "crm"

urlpatterns = [
    path("filiallar/", views.FiliallarView.as_view(), name="filiallar"),
    path("filiallar/<int:pk>/", views.FilialDetailView.as_view(), name="filial_detail"),

    path("kurs-narxlari/", views.KursNarxlariView.as_view(), name="kurs_narxlari"),

    path("xonalar/", views.XonalarView.as_view(), name="xonalar"),
    path("xonalar/<int:pk>/", views.XonaDetailView.as_view(), name="xona_detail"),
    path("jadval/", views.JadvalSetkaView.as_view(), name="jadval"),

    path("guruhlar/", views.GuruhlarView.as_view(), name="guruhlar"),
    path("guruhlar/<int:pk>/moliya/", views.GuruhMoliyaView.as_view(), name="guruh_moliya"),
    path("guruhlar/<int:pk>/jadval/", views.GuruhJadvalView.as_view(), name="guruh_jadval"),
    path("guruhlar/<int:pk>/azoliklar/", views.GuruhAzoliklariView.as_view(), name="guruh_azoliklari"),
    # Davomat (2026-09-23, video-TZ) — CRM'dan ham BELGILANADI, yozuv
    # o'sha LMS `Davomat` jadvaliga tushadi (bitta manba). Natijalar —
    # faqat o'qish (mashqlar LMS'da yechiladi).
    path("guruhlar/<int:pk>/davomat/", boshqaruv.GuruhDavomatView.as_view(), name="guruh_davomat"),
    path("guruhlar/<int:pk>/natijalar/", views.GuruhNatijalarView.as_view(), name="guruh_natijalar"),

    path("azoliklar/<int:pk>/", views.AzolikView.as_view(), name="azolik"),

    path("eslatmalar/", views.EslatmalarView.as_view(), name="eslatmalar"),
    path("eslatmalar/<int:pk>/", views.EslatmaDetailView.as_view(), name="eslatma_detail"),

    path("hisoblar/", views.HisoblarView.as_view(), name="hisoblar"),
    path("hisoblar/<int:pk>/", views.HisobDetailView.as_view(), name="hisob_detail"),

    path("tolov/", views.TolovlarView.as_view(), name="tolovlar"),
    path("tolov/<int:pk>/", views.TolovDetailView.as_view(), name="tolov_detail"),

    path("talabalar/", views.TalabalarView.as_view(), name="talabalar"),
    path("talaba/<int:pk>/", views.TalabaView.as_view(), name="talaba"),

    path("hisobot/", views.HisobotView.as_view(), name="hisobot"),
    path("hisobot/dinamika/", views.HisobotDinamikaView.as_view(), name="hisobot_dinamika"),
    path("eksport/", views.EksportView.as_view(), name="eksport"),
    path("ogohlantirishlar/", views.OgohlantirishlarView.as_view(), name="ogohlantirishlar"),

    # ── Video-TZ (2026-09-23): CRM asosiy manba ──────────────────────
    path("men/", boshqaruv.MenView.as_view(), name="men"),
    path("korsatkichlar/", boshqaruv.KorsatkichlarView.as_view(), name="korsatkichlar"),

    path("rollar/", boshqaruv.RollarView.as_view(), name="rollar"),
    path("rollar/<int:pk>/", boshqaruv.RolDetailView.as_view(), name="rol_detail"),
    path("xodimlar/", boshqaruv.XodimlarView.as_view(), name="xodimlar"),
    path("xodimlar/<int:pk>/", boshqaruv.XodimDetailView.as_view(), name="xodim_detail"),

    path("lid-bolimlar/", boshqaruv.LidBolimlarView.as_view(), name="lid_bolimlar"),
    path("lid-bolimlar/<int:pk>/", boshqaruv.LidBolimDetailView.as_view(), name="lid_bolim_detail"),
    path("lidlar/", boshqaruv.LidlarView.as_view(), name="lidlar"),
    path("lidlar/guruhga/", boshqaruv.LidGuruhgaView.as_view(), name="lid_guruhga"),
    path("lidlar/eksport/", boshqaruv.LidlarEksportView.as_view(), name="lidlar_eksport"),
    path("lidlar/<int:pk>/", boshqaruv.LidDetailView.as_view(), name="lid_detail"),

    path("talaba-yaratish/", boshqaruv.TalabaYaratishView.as_view(), name="talaba_yaratish"),
    path("talaba-qidiruv/", boshqaruv.TalabaQidiruvView.as_view(), name="talaba_qidiruv"),
    path("talaba/<int:pk>/crm/", boshqaruv.TalabaCrmView.as_view(), name="talaba_crm"),
    path("talaba/<int:pk>/sayt-hisobi/", boshqaruv.TalabaSaytHisobiView.as_view(), name="talaba_sayt_hisobi"),

    path("guruh-yaratish/", boshqaruv.GuruhYaratishView.as_view(), name="guruh_yaratish"),
    path("guruhlar/<int:pk>/boshqaruv/", boshqaruv.GuruhBoshqaruvView.as_view(), name="guruh_boshqaruv"),
    path("guruhlar/<int:pk>/talabalar/", boshqaruv.GuruhTalabalariView.as_view(), name="guruh_talabalari"),
    path("guruhlar/<int:pk>/dars-ozgarishlari/", boshqaruv.DarsOzgarishlariView.as_view(), name="dars_ozgarishlari"),
    path("dars-ozgarishlari/<int:pk>/", boshqaruv.DarsOzgarishDetailView.as_view(), name="dars_ozgarish_detail"),
    path("guruhlar/<int:pk>/chegirmalar/", boshqaruv.GuruhChegirmalariView.as_view(), name="guruh_chegirmalari"),
    path("chegirmalar/<int:pk>/", boshqaruv.ChegirmaDetailView.as_view(), name="chegirma_detail"),
    path("guruhlar/<int:pk>/baholar/", boshqaruv.GuruhBaholariView.as_view(), name="guruh_baholari"),
    path("eslatmalar/muddatli/", boshqaruv.MuddatliEslatmalarView.as_view(), name="muddatli_eslatmalar"),
]
