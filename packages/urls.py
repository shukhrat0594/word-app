from django.urls import path

from . import views

urlpatterns = [
    path("paketlar/", views.PaketKatalogView.as_view(), name="paket_katalog"),
    path("paketlar/xarid/", views.PaketXaridView.as_view(), name="paket_xarid"),
    path("paketlar/mening/", views.MeningPaketlarimView.as_view(), name="mening_paketlarim"),
]
