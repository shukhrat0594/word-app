from django.urls import path

from . import views

urlpatterns = [
    path(
        "writing/tekshirish/",
        views.WritingTekshirishView.as_view(),
        name="writing_tekshirish",
    ),
    path("writing/tarix/", views.WritingTarixView.as_view(), name="writing_tarix"),
    path(
        "speaking/matn/",
        views.SpeakingMatnView.as_view(),
        name="speaking_matn",
    ),
    path("speaking/tarix/", views.SpeakingTarixView.as_view(), name="speaking_tarix"),
]
