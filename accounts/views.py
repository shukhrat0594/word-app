from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


class GoogleLoginView(APIView):
    """Talaba Google ID token yuboradi -> tekshiriladi -> JWT qaytariladi.

    Markaz biriktirilmaydi (markaz=None) -- buni keyinroq Markaz admin
    Guruhga qo'shganda avtomatik oladi (academics.Guruh signali).
    """

    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("id_token")
        if not token:
            return Response({"detail": "id_token majburiy"}, status=400)

        try:
            idinfo = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
            )
        except ValueError:
            return Response({"detail": "id_token yaroqsiz"}, status=401)

        email = idinfo["email"]
        user, created = User.objects.get_or_create(
            username=email,
            defaults={
                "email": email,
                "role": User.Role.STUDENT,
                "first_name": idinfo.get("given_name", ""),
                "last_name": idinfo.get("family_name", ""),
            },
        )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "created": created,
                "markaz_biriktirilgan": user.markaz_id is not None,
            }
        )
