from django.urls import path

from .views import AuditFiltrlarView, AuditHisobotView, FoydalanuvchilarStatistikaView

urlpatterns = [
    path("audit/", AuditHisobotView.as_view(), name="audit_hisobot"),
    path("audit/filtrlar/", AuditFiltrlarView.as_view(), name="audit_filtrlar"),
    path(
        "statistika/foydalanuvchilar/",
        FoydalanuvchilarStatistikaView.as_view(),
        name="foydalanuvchilar_statistika",
    ),
]
