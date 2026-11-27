from django.urls import path

from . import head_teacher, views

urlpatterns = [
    # Matn-TZ 779: Head Teacher dashboard (academics/head_teacher.py)
    path("head-teacher/filtrlar/", head_teacher.FiltrlarView.as_view(), name="ht_filtrlar"),
    path("head-teacher/dashboard/", head_teacher.DashboardView.as_view(), name="ht_dashboard"),
    path("head-teacher/guruhlar/", head_teacher.GuruhlarView.as_view(), name="ht_guruhlar"),
    path("head-teacher/talabalar/", head_teacher.TalabalarView.as_view(), name="ht_talabalar"),
    path("head-teacher/talabalar/<int:pk>/", head_teacher.TalabaProfilView.as_view(), name="ht_talaba"),
    path("head-teacher/punktuallik/", head_teacher.PunktuallikView.as_view(), name="ht_punktuallik"),
    path(
        "head-teacher/punktuallik/<int:pk>/",
        head_teacher.PunktuallikDetailView.as_view(),
        name="ht_punktuallik_detail",
    ),
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
