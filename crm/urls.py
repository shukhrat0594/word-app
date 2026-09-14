"""CRM API yo'llari — hammasi `/api/crm/` prefiksi ostida.

Prefiks ATAYLAB alohida: mavjud `/api/...` yo'llari bilan hech qachon
aralashmaydi, ya'ni CRM olib tashlanganda LMS marshrutlariga tegilmaydi
(`config/urls.py` dan bitta qatorni o'chirish yetarli).
"""

from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    path("filiallar/", views.FiliallarView.as_view(), name="filiallar"),
    path("filiallar/<int:pk>/", views.FilialDetailView.as_view(), name="filial_detail"),

    path("kurs-narxlari/", views.KursNarxlariView.as_view(), name="kurs_narxlari"),

    path("guruhlar/", views.GuruhlarView.as_view(), name="guruhlar"),
    path("guruhlar/<int:pk>/moliya/", views.GuruhMoliyaView.as_view(), name="guruh_moliya"),
    path("guruhlar/<int:pk>/jadval/", views.GuruhJadvalView.as_view(), name="guruh_jadval"),
    path("guruhlar/<int:pk>/azoliklar/", views.GuruhAzoliklariView.as_view(), name="guruh_azoliklari"),

    path("azoliklar/<int:pk>/", views.AzolikView.as_view(), name="azolik"),

    path("hisoblar/", views.HisoblarView.as_view(), name="hisoblar"),
    path("hisoblar/<int:pk>/", views.HisobDetailView.as_view(), name="hisob_detail"),

    path("tolov/", views.TolovlarView.as_view(), name="tolovlar"),
    path("tolov/<int:pk>/", views.TolovDetailView.as_view(), name="tolov_detail"),

    path("talaba/<int:pk>/", views.TalabaView.as_view(), name="talaba"),

    path("hisobot/", views.HisobotView.as_view(), name="hisobot"),
    path("eksport/", views.EksportView.as_view(), name="eksport"),
    path("ogohlantirishlar/", views.OgohlantirishlarView.as_view(), name="ogohlantirishlar"),
]
