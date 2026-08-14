"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve as media_serve
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.backup_views import BackupdanTiklashView, BackupYuklabOlishView
from accounts.views import (
    BildirishnomalarView,
    FoydalanuvchilarView,
    FoydalanuvchiOchirishView,
    FoydalanuvchiParolTiklashView,
    FoydalanuvchiFarzandlarView,
    FoydalanuvchiNatijalariView,
    FoydalanuvchiPanellarView,
    FoydalanuvchiRasmView,
    QurilmaTiklashView,
    QurilmaLimitiView,
    ProfilTahrirlashView,
    FoydalanuvchiRolView,
    FoydalanuvchiYaratishView,
    GoogleLoginView,
    MarkazAdminTayinlashView,
    MarkazlarView,
    MarkazRadEtishView,
    MarkazSorovView,
    IjtimoiyHavolalarView,
    KorishRejimiView,
    MarkazSozlamaView,
    MarkazTasdiqlashView,
    OddiyStudentgaOtkazishView,
    ParolOzgartirishView,
    ProfilView,
    SaytHolatiView,
    TalabaDetailView,
    TalabalarExcelImportView,
    TalabalarView,
    XodimDetailView,
    XodimLoginView,
    XodimlarExcelImportView,
    XodimlarView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', XodimLoginView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/google/', GoogleLoginView.as_view(), name='google_login'),
    path('api/profil/', ProfilView.as_view(), name='profil'),
    path('api/profil/parol/', ParolOzgartirishView.as_view(), name='parol_ozgartirish'),
    path('api/profil/tahrirlash/', ProfilTahrirlashView.as_view(), name='profil_tahrirlash'),
    path('api/profil/korish-rejimi/', KorishRejimiView.as_view(), name='korish_rejimi'),
    path('api/markazlar/', MarkazlarView.as_view(), name='markazlar'),
    path(
        'api/markazlar/<int:pk>/admin-tayinlash/',
        MarkazAdminTayinlashView.as_view(),
        name='markaz_admin_tayinlash',
    ),
    path(
        'api/markazlar/<int:pk>/tasdiqlash/',
        MarkazTasdiqlashView.as_view(),
        name='markaz_tasdiqlash',
    ),
    path(
        'api/markazlar/<int:pk>/rad-etish/',
        MarkazRadEtishView.as_view(),
        name='markaz_rad_etish',
    ),
    path('api/markaz-sorovi/', MarkazSorovView.as_view(), name='markaz_sorovi'),
    path('api/markaz-sozlama/', MarkazSozlamaView.as_view(), name='markaz_sozlama'),
    path('api/sayt-holati/', SaytHolatiView.as_view(), name='sayt_holati'),
    path('api/backup/yuklab-olish/', BackupYuklabOlishView.as_view(), name='backup_yuklab_olish'),
    path('api/backup/tiklash/', BackupdanTiklashView.as_view(), name='backup_tiklash'),
    # Ochiq — login talab qilinmaydi (pastki panel har sahifada, jumladan
    # kirish ekranida ham ko'rinadi).
    path('api/ijtimoiy/', IjtimoiyHavolalarView.as_view(), name='ijtimoiy_havolalar'),
    path('api/xodimlar/', XodimlarView.as_view(), name='xodimlar'),
    path('api/xodimlar/<int:pk>/', XodimDetailView.as_view(), name='xodim_detail'),
    path('api/xodimlar/excel-import/', XodimlarExcelImportView.as_view(), name='xodimlar_excel_import'),
    path('api/talabalar/', TalabalarView.as_view(), name='talabalar'),
    path('api/talabalar/<int:pk>/', TalabaDetailView.as_view(), name='talaba_detail'),
    path('api/talabalar/excel-import/', TalabalarExcelImportView.as_view(), name='talabalar_excel_import'),
    path('api/foydalanuvchilar/', FoydalanuvchilarView.as_view(), name='foydalanuvchilar'),
    path(
        'api/foydalanuvchilar/yaratish/',
        FoydalanuvchiYaratishView.as_view(),
        name='foydalanuvchi_yaratish',
    ),
    path(
        'api/foydalanuvchilar/<int:pk>/parol/',
        FoydalanuvchiParolTiklashView.as_view(),
        name='foydalanuvchi_parol',
    ),
    path(
        'api/foydalanuvchilar/<int:pk>/studentga-otkazish/',
        OddiyStudentgaOtkazishView.as_view(),
        name='foydalanuvchi_studentga_otkazish',
    ),
    path(
        'api/foydalanuvchilar/<int:pk>/ochirish/',
        FoydalanuvchiOchirishView.as_view(),
        name='foydalanuvchi_ochirish',
    ),
    path(
        'api/foydalanuvchilar/<int:pk>/rol/',
        FoydalanuvchiRolView.as_view(),
        name='foydalanuvchi_rol',
    ),
    path(
        'api/foydalanuvchilar/<int:pk>/panellar/',
        FoydalanuvchiPanellarView.as_view(),
        name='foydalanuvchi_panellar',
    ),
    path(
        'api/bildirishnomalar/',
        BildirishnomalarView.as_view(),
        name='bildirishnomalar',
    ),
    path(
        'api/foydalanuvchilar/<int:pk>/natijalar/',
        FoydalanuvchiNatijalariView.as_view(),
        name='foydalanuvchi_natijalar',
    ),
    path(
        'api/foydalanuvchilar/<int:pk>/farzandlar/',
        FoydalanuvchiFarzandlarView.as_view(),
        name='foydalanuvchi_farzandlar',
    ),
    path(
        'api/foydalanuvchilar/<int:pk>/rasm/',
        FoydalanuvchiRasmView.as_view(),
        name='foydalanuvchi_rasm',
    ),
    path(
        'api/foydalanuvchilar/<int:pk>/qurilma-tiklash/',
        QurilmaTiklashView.as_view(),
        name='foydalanuvchi_qurilma_tiklash',
    ),
    path(
        'api/foydalanuvchilar/<int:pk>/qurilma-limit/',
        QurilmaLimitiView.as_view(),
        name='foydalanuvchi_qurilma_limit',
    ),
    path('api/', include('academics.urls')),
    path('api/', include('exercises.urls')),
    path('api/', include('assessment.urls')),
    path('api/', include('stats.urls')),
    path('api/', include('gamification.urls')),
    path('api/', include('games.urls')),
    path('api/', include('audit.urls')),
    path('api/', include('courses.urls')),
    # B3.2: media'dan FAQAT markaz logolari ochiq (brending — maxfiy emas).
    # Audio fayllar bu yo'l orqali BERILMAYDI — ular faqat autentifikatsiyalangan
    # stream endpointlar orqali (exercises.MashqAudioView).
    re_path(
        r'^media/(?P<path>markaz_logos/.*)$',
        media_serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]
