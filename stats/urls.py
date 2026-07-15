from django.urls import path

from . import views

urlpatterns = [
    path("statistika/", views.MeningStatistikamView.as_view(), name="mening_statistikam"),
    path("farzandlar/", views.FarzandlarView.as_view(), name="farzandlar"),
    path(
        "farzandlar/<int:pk>/statistika/",
        views.FarzandStatistikasiView.as_view(),
        name="farzand_statistikasi",
    ),
]
