from django.urls import path

from . import views

urlpatterns = [
    path("kurslar/daraxt/", views.KursDaraxtiView.as_view(), name="kurslar_daraxt"),
    path("kurslar/<int:pk>/fayl/", views.KursFaylView.as_view(), name="kurslar_fayl"),
    path(
        "kurslar/<int:pk>/fayl-boshqaruv/",
        views.KursTugunFaylBoshqaruvView.as_view(),
        name="kurslar_fayl_boshqaruv",
    ),
    path(
        "kurslar/<int:pk>/tugallandi/",
        views.KursTugunTugallandiView.as_view(),
        name="kurslar_tugallandi",
    ),
    path(
        "kurslar/<int:pk>/mashq-boshqaruv/",
        views.KursMashqBoshqaruvView.as_view(),
        name="kurslar_mashq_boshqaruv",
    ),
    path(
        "kurslar/<int:pk>/mashqlar/",
        views.KursMashqRoyxatiView.as_view(),
        name="kurslar_mashqlar",
    ),
    path(
        "kurslar/mashq/<int:pk>/",
        views.KursMashqDetailBoshqaruvView.as_view(),
        name="kurslar_mashq_detail",
    ),
    path(
        "kurslar/mashq/<int:pk>/rasm/",
        views.KursMashqRasmView.as_view(),
        name="kurslar_mashq_rasm",
    ),
    path(
        "kurslar/mashq/<int:pk>/rasm-boshqaruv/",
        views.KursMashqRasmBoshqaruvView.as_view(),
        name="kurslar_mashq_rasm_boshqaruv",
    ),
    path(
        "kurslar/mashq/<int:pk>/audio/",
        views.KursMashqAudioView.as_view(),
        name="kurslar_mashq_audio",
    ),
    path(
        "kurslar/mashq/<int:pk>/audio-boshqaruv/",
        views.KursMashqAudioBoshqaruvView.as_view(),
        name="kurslar_mashq_audio_boshqaruv",
    ),
    path(
        "kurslar/<int:pk>/audio-zip/",
        views.KursMashqAudioZipBoshqaruvView.as_view(),
        name="kurslar_audio_zip",
    ),
    path(
        "kurslar/mashq/<int:pk>/yechish/",
        views.KursMashqYechishView.as_view(),
        name="kurslar_mashq_yechish",
    ),
]
