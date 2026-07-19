from django.urls import path

from . import views

urlpatterns = [
    path("guruhlar/", views.GuruhlarView.as_view(), name="guruhlar"),
    path("guruhlar/<int:pk>/", views.GuruhDetailView.as_view(), name="guruh_detail"),
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
