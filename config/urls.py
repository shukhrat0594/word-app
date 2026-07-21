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

from accounts.views import (
    FoydalanuvchilarView,
    FoydalanuvchiOchirishView,
    FoydalanuvchiParolTiklashView,
    FoydalanuvchiRolView,
    FoydalanuvchiYaratishView,
    GoogleLoginView,
    MarkazAdminTayinlashView,
    MarkazlarView,
    MarkazRadEtishView,
    MarkazSorovView,
    MarkazSozlamaView,
    MarkazTasdiqlashView,
    NarxlarView,
    OddiyStudentgaOtkazishView,
    ParolOzgartirishView,
    ProfilView,
    XodimLoginView,
    XodimlarView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', XodimLoginView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/google/', GoogleLoginView.as_view(), name='google_login'),
    path('api/profil/', ProfilView.as_view(), name='profil'),
    path('api/profil/parol/', ParolOzgartirishView.as_view(), name='parol_ozgartirish'),
    path('api/narxlar/', NarxlarView.as_view(), name='narxlar'),
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
    path('api/xodimlar/', XodimlarView.as_view(), name='xodimlar'),
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
    path('api/', include('academics.urls')),
    path('api/', include('exercises.urls')),
    path('api/', include('assessment.urls')),
    path('api/', include('stats.urls')),
    path('api/', include('gamification.urls')),
    path('api/', include('packages.urls')),
    path('api/', include('games.urls')),
    path('api/', include('audit.urls')),
    # B3.2: media'dan FAQAT markaz logolari ochiq (brending — maxfiy emas).
    # Audio fayllar bu yo'l orqali BERILMAYDI — ular faqat autentifikatsiyalangan
    # stream endpointlar orqali (exercises.MashqAudioView).
    re_path(
        r'^media/(?P<path>markaz_logos/.*)$',
        media_serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]
