from django.urls import path

from . import views

urlpatterns = [
    path("gamifikatsiya/", views.GamifikatsiyaView.as_view(), name="gamifikatsiya"),
    path("leaderboard/", views.LeaderboardView.as_view(), name="leaderboard"),
]
