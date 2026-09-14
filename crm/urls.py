"""CRM API yo'llari — hammasi `/api/crm/` prefiksi ostida.

Prefiks ATAYLAB alohida: mavjud `/api/...` yo'llari bilan hech qachon
aralashmaydi, ya'ni CRM olib tashlanganda LMS marshrutlariga tegilmaydi
(`config/urls.py` dan bitta qatorni o'chirish yetarli).
"""

from django.urls import path

app_name = "crm"

urlpatterns: list[path] = [
    # View'lar keyingi qadamda qo'shiladi (TZ 5-band).
]
