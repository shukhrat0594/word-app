from django.urls import path

from . import views

urlpatterns = [
    path("statistika/", views.MeningStatistikamView.as_view(), name="mening_statistikam"),
]
