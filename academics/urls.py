from django.urls import path

from . import views

urlpatterns = [
    path("guruhlar/", views.GuruhlarView.as_view(), name="guruhlar"),
    path("guruh-fanlari/", views.GuruhFanlarView.as_view(), name="guruh_fanlari"),
    path("guruhlar/<int:pk>/", views.GuruhDetailView.as_view(), name="guruh_detail"),
    path(
        "guruhlar/<int:pk>/azolik/<int:talaba_id>/",
        views.GuruhAzoligiDetailView.as_view(),
        name="guruh_azoligi_detail",
    ),
    path(
        "markaz-azolari/",
        views.MarkazAzolariView.as_view(),
        name="markaz_azolari",
    ),
    path("davomat/", views.DavomatView.as_view(), name="davomat"),
    path(
        "davomat-hisoboti/",
        views.DavomatHisobotView.as_view(),
        name="davomat_hisoboti",
    ),
]
