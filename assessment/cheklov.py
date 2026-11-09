"""AI endpointlari uchun cheklovlar (2026-11-09).

Nega kerak: Writing/Speaking/Trainer/Grammar Coach so'rovlari platforma kaliti bilan
to'lanadi, lekin ularda faqat umumiy "daqiqasiga 300 so'rov" cheklovi bor edi — bitta
hisob soatiga minglab pullik AI chaqiruvi yubora olardi. Audio va rasm hajmi ham
cheklanmagan, fayl esa butunlay xotiraga o'qiladi (kichik serverda xotira tugashi).

Chegara `settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["ai"]`da (muhit
o'zgaruvchisi `AI_SOROV_LIMITI`, standart soatiga 120). Owner'ga cheklov yo'q.
"""

from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

AUDIO_MAKS_HAJM = 25 * 1024 * 1024  # 25 MB — brauzerda yozilgan javob odatda 1-5 MB
RASM_MAKS_HAJM = 8 * 1024 * 1024    # 8 MB — Writing Task 1 grafigi


class AiSorovCheklovi(UserRateThrottle):
    scope = "ai"

    def allow_request(self, request, view):
        from accounts.authentication import asl_owner_mi

        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and asl_owner_mi(user):
            return True
        return super().allow_request(request, view)


class AiCheklovli:
    """AI chaqiradigan view'lar uchun aralashma: umumiy cheklov + AI cheklovi."""

    throttle_classes = [UserRateThrottle, AiSorovCheklovi]

    def throttled(self, request, wait):
        daqiqa = max(1, round((wait or 60) / 60))
        raise Throttled(detail=(
            f"AI so'rovlari chegarasiga yetdingiz — taxminan {daqiqa} daqiqadan keyin "
            f"qayta urinib ko'ring."
        ))


def audio_xatosi(fayl):
    """Audio juda katta bo'lsa — 400 javob, aks holda None."""
    if fayl is not None and fayl.size > AUDIO_MAKS_HAJM:
        return Response(
            {"detail": f"Audio hajmi {AUDIO_MAKS_HAJM // (1024 * 1024)} MB dan oshmasin"}, status=400
        )
    return None
