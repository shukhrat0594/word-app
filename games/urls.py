from django.urls import path

from . import views

urlpatterns = [
    path("oyinlar/sozlar/", views.SozlarView.as_view(), name="oyin_sozlar"),
    path("oyinlar/darajalar/", views.DarajalarView.as_view(), name="oyin_darajalar"),
    path(
        "oyinlar/grammatika-mavzulari/",
        views.GrammatikaMavzulariView.as_view(),
        name="grammatika_mavzulari",
    ),
    path(
        "oyinlar/grammatika/",
        views.GrammatikaSavollariView.as_view(),
        name="grammatika_savollari",
    ),
    path(
        "oyinlar/grammatika/tekshirish/",
        views.GrammatikaTekshirishView.as_view(),
        name="grammatika_tekshirish",
    ),
]
