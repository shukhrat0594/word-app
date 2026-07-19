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
]
