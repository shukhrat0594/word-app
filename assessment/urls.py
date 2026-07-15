from django.urls import path

from . import views

urlpatterns = [
    path(
        "writing/tekshirish/",
        views.WritingTekshirishView.as_view(),
        name="writing_tekshirish",
    ),
    path("writing/tarix/", views.WritingTarixView.as_view(), name="writing_tarix"),
]
