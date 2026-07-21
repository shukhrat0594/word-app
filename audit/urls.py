from django.urls import path

from .views import AuditFiltrlarView, AuditHisobotView

urlpatterns = [
    path("audit/", AuditHisobotView.as_view(), name="audit_hisobot"),
    path("audit/filtrlar/", AuditFiltrlarView.as_view(), name="audit_filtrlar"),
]
