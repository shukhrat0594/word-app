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
        "imtihon/qism-boshqaruv/<int:pk>/",
        views.TestQismiAudioBoshqaruvView.as_view(),
        name="imtihon_qism_boshqaruv",
    ),
    path("imtihon/testlar/", views.ImtihonListView.as_view(), name="imtihon_list"),
    path("imtihon/testlar/<int:pk>/", views.ImtihonDetailView.as_view(), name="imtihon_detail"),
    path(
        "imtihon/testlar/<int:pk>/yechish/",
        views.ImtihonYechishView.as_view(),
        name="imtihon_yechish",
    ),
    path("imtihon/qism/<int:pk>/audio/", views.TestQismAudioView.as_view(), name="imtihon_qism_audio"),
]
