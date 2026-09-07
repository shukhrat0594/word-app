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
    path(
        "speaking/audio/",
        views.SpeakingAudioView.as_view(),
        name="speaking_audio",
    ),
    path(
        "speaking/transkripsiya/",
        views.SpeakingTranskripsiyaView.as_view(),
        name="speaking_transkripsiya",
    ),
    path("speaking/tarix/", views.SpeakingTarixView.as_view(), name="speaking_tarix"),
    # Speaking yozuvining audiosi — autentifikatsiyalangan oqim (B3.2,
    # 2026-09-07). Avval tarix javobida xom /media/ havolasi qaytardi.
    path(
        "speaking/tekshiruv/<int:pk>/audio/",
        views.SpeakingAudioFaylView.as_view(),
        name="speaking_tekshiruv_audio",
    ),
    path("tarix/", views.TarixView.as_view(), name="tarix"),
]
