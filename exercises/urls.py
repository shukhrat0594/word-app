from django.urls import path

from . import views

urlpatterns = [
    path("mashqlar/", views.MashqListView.as_view(), name="mashq_list"),
    path("mashqlar/<int:pk>/", views.MashqDetailView.as_view(), name="mashq_detail"),
    path(
        "mashqlar/<int:pk>/yechish/",
        views.MashqYechishView.as_view(),
        name="mashq_yechish",
    ),
    path("limit/", views.LimitHolatiView.as_view(), name="limit_holati"),
    path("limit/topup/", views.LimitTopUpView.as_view(), name="limit_topup"),
]
