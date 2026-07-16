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
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from accounts.views import GoogleLoginView, ProfilView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/google/', GoogleLoginView.as_view(), name='google_login'),
    path('api/profil/', ProfilView.as_view(), name='profil'),
    path('api/', include('exercises.urls')),
    path('api/', include('assessment.urls')),
    path('api/', include('stats.urls')),
    path('api/', include('gamification.urls')),
    path('api/', include('packages.urls')),
    # B3.2: media'dan FAQAT markaz logolari ochiq (brending — maxfiy emas).
    # Audio fayllar bu yo'l orqali BERILMAYDI — ular faqat autentifikatsiyalangan
    # stream endpointlar orqali (exercises.MashqAudioView).
    re_path(
        r'^media/(?P<path>markaz_logos/.*)$',
        media_serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]
