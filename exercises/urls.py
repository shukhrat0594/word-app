from django.urls import path

from . import views

urlpatterns = [
    path(
        "mashqlar-boshqaruv/",
        views.MashqBoshqaruvView.as_view(),
        name="mashq_boshqaruv",
    ),
    path(
        "mashqlar-boshqaruv/<int:pk>/",
        views.MashqBoshqaruvDetailView.as_view(),
        name="mashq_boshqaruv_detail",
    ),
    path("mashqlar/", views.MashqListView.as_view(), name="mashq_list"),
    path("mashqlar/<int:pk>/", views.MashqDetailView.as_view(), name="mashq_detail"),
    path("mashqlar/<int:pk>/audio/", views.MashqAudioView.as_view(), name="mashq_audio"),
    path("mashqlar/<int:pk>/rasm/", views.MashqRasmView.as_view(), name="mashq_rasm"),
    path(
        "mashqlar/<int:pk>/yechish/",
        views.MashqYechishView.as_view(),
        name="mashq_yechish",
    ),
    path("limit/", views.LimitHolatiView.as_view(), name="limit_holati"),
    path("limit/topup/", views.LimitTopUpView.as_view(), name="limit_topup"),
    path(
        "imtihon/testlar-boshqaruv/",
        views.ImtihonBoshqaruvView.as_view(),
        name="imtihon_boshqaruv",
    ),
    path(
        "imtihon/testlar-boshqaruv/<int:pk>/",
        views.ImtihonBoshqaruvDetailView.as_view(),
        name="imtihon_boshqaruv_detail",
    ),
    path(
        "imtihon/mashq-generatsiya/",
        views.MashqGeneratsiyaView.as_view(),
        name="imtihon_mashq_generatsiya",
    ),
    path(
        "imtihon/<int:pk>/listening-davom/",
        views.ListeningDavomEttirishView.as_view(),
        name="imtihon_listening_davom",
    ),
    path(
        "imtihon/papkalar/",
        views.TestPapkaBoshqaruvView.as_view(),
        name="imtihon_papkalar",
    ),
    path(
        "imtihon/papkalar/<int:pk>/",
        views.TestPapkaDetailView.as_view(),
        name="imtihon_papka_detail",
    ),
    path(
        "imtihon/papkalar/<int:pk>/mock-yaratish/",
        views.PapkadanMockYaratishView.as_view(),
        name="imtihon_papka_mock_yaratish",
    ),
    path(
        "imtihon/testlar-boshqaruv-zip/",
        views.ImtihonZipBoshqaruvView.as_view(),
        name="imtihon_boshqaruv_zip",
    ),
    path(
        "imtihon/testlar-boshqaruv-pdf/",
        views.ImtihonPdfBoshqaruvView.as_view(),
        name="imtihon_boshqaruv_pdf",
    ),
    path(
        "imtihon/qism-boshqaruv/<int:pk>/",
        views.TestQismiFayllarBoshqaruvView.as_view(),
        name="imtihon_qism_boshqaruv",
    ),
    path(
        "imtihon/qism-boshqaruv/<int:pk>/pozitsiya-aniqla/",
        views.QismPozitsiyaAniqlashView.as_view(),
        name="imtihon_qism_pozitsiya_aniqla",
    ),
    path("imtihon/testlar/", views.ImtihonListView.as_view(), name="imtihon_list"),
    path("imtihon/testlar/<int:pk>/", views.ImtihonDetailView.as_view(), name="imtihon_detail"),
    path(
        "imtihon/testlar/<int:pk>/yechish/",
        views.ImtihonYechishView.as_view(),
        name="imtihon_yechish",
    ),
    path(
        "imtihon/testlar/<int:pk>/yozgap-tekshirish/",
        views.ImtihonYozGapTekshirishView.as_view(),
        name="imtihon_yozgap_tekshirish",
    ),
    path("imtihon/qism/<int:pk>/audio/", views.TestQismAudioView.as_view(), name="imtihon_qism_audio"),
    path("imtihon/qism/<int:pk>/rasm/", views.TestQismRasmView.as_view(), name="imtihon_qism_rasm"),
    path("imtihon-mock/", views.ImtihonMockRoyxatiView.as_view(), name="imtihon_mock_royxat"),
    path("imtihon-mock/yaratish/", views.ImtihonMockYaratishView.as_view(), name="imtihon_mock_yaratish"),
    path("imtihon-mock/<int:pk>/", views.ImtihonMockDetailView.as_view(), name="imtihon_mock_detail"),
    path(
        "imtihon-mock/<int:pk>/boshlash/",
        views.ImtihonMockBoshlashView.as_view(),
        name="imtihon_mock_boshlash",
    ),
    path(
        "imtihon-mock/yechim/<int:pk>/",
        views.ImtihonMockYechimView.as_view(),
        name="imtihon_mock_yechim",
    ),
]
