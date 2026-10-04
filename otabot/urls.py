"""`/api/crm/otabot/...` — CRM'dagi "Ota-ona boti" bo'limi uchun."""

from django.urls import path

from . import views

app_name = "otabot"

urlpatterns = [
    path("sorovlar/", views.SorovlarView.as_view(), name="sorovlar"),
    path("sorovlar/<int:pk>/hal/", views.SorovHalView.as_view(), name="sorov_hal"),
    path("talaba-qidiruv/", views.TalabaQidiruvView.as_view(), name="talaba_qidiruv"),
    path("abonentlar/", views.AbonentlarView.as_view(), name="abonentlar"),
    path("boglanishlar/<int:pk>/uzish/", views.BoglanishUzishView.as_view(), name="boglanish_uzish"),
    path("sozlama/", views.SozlamaView.as_view(), name="sozlama"),
]
