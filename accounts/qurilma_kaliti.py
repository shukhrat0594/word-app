"""Qurilma kaliti (passkey, WebAuthn) — 2026-10-29.

Kalit sayt (frontend) domeniga bog'lanadi: so'rovdagi `Origin` `settings.WEBAUTHN_ORIGINS`
ro'yxatida bo'lishi kerak va kalit domeni (rp_id) shu manzildan olinadi. Bosqichlar
orasidagi holat (tasodifiy savol) serverda saqlanmaydi — imzolangan «chipta»da yuradi.
Bitta savolga ikki marta javob berib bo'lmaydi (kesh, `_bir_marta`)."""

from urllib.parse import urlparse

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url, options_to_json_dict
from webauthn.helpers.exceptions import InvalidAuthenticationResponse, InvalidRegistrationResponse
from webauthn.helpers.structs import (
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

CHIPTA_TUZI = "qurilma-kaliti"
CHIPTA_MUDDATI = 300  # soniya
_KUTISH_MS = 120000


class KalitXatosi(ValueError):
    """Kalit bosqichini bajarib bo'lmadi — matni foydalanuvchiga ko'rsatiladi."""


def manzil(request):
    """So'rov kelgan sayt manzili, agar u yerda kalit ishlatish mumkin bo'lsa; aks holda None."""
    origin = (request.headers.get("Origin") or "").rstrip("/")
    return origin if origin in settings.WEBAUTHN_ORIGINS else None


def _rp(origin):
    return urlparse(origin).hostname


def chipta_yasa(**qiymat):
    return signing.dumps(qiymat, salt=CHIPTA_TUZI)


def chipta_och(chipta):
    try:
        return signing.loads(str(chipta or ""), salt=CHIPTA_TUZI, max_age=CHIPTA_MUDDATI)
    except signing.BadSignature as e:  # muddati o'tgani ham shu
        raise KalitXatosi("Tasdiqlash vaqti tugadi — qayta kiring") from e


def _bir_marta(savol):
    if not cache.add(f"qurilma-kaliti:{savol}", 1, CHIPTA_MUDDATI * 2):
        raise KalitXatosi("Bu tasdiq allaqachon ishlatilgan — qayta kiring")


def javob_kalit_idsi(javob):
    kalit_id = javob.get("rawId") or javob.get("id") if isinstance(javob, dict) else None
    return kalit_id if isinstance(kalit_id, str) else ""


def tasdiqlash_sorovi(origin, kalit_idlar):
    """Kirishda: shu brauzerda shu odamning kaliti bormi — telefon qulfi bilan tasdiqlash.
    Qaytaradi: (savol, brauzerga beriladigan sozlamalar)."""
    sozlama = generate_authentication_options(
        rp_id=_rp(origin),
        allow_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(k)) for k in kalit_idlar],
        user_verification=UserVerificationRequirement.REQUIRED,
        timeout=_KUTISH_MS,
    )
    return bytes_to_base64url(sozlama.challenge), options_to_json_dict(sozlama)


def tasdiqni_tekshir(javob, savol, origin, ochiq_kalit, hisoblagich):
    """Qaytaradi: kalitning yangi hisoblagichi. Yaroqsiz bo'lsa — `KalitXatosi`."""
    _bir_marta(savol)
    try:
        natija = verify_authentication_response(
            credential=javob, expected_challenge=base64url_to_bytes(savol), expected_rp_id=_rp(origin),
            expected_origin=origin, credential_public_key=ochiq_kalit,
            credential_current_sign_count=hisoblagich, require_user_verification=True,
        )
    except (InvalidAuthenticationResponse, ValueError, KeyError, TypeError) as e:
        raise KalitXatosi("Qurilma kaliti tasdiqlanmadi") from e
    return natija.new_sign_count


def yaratish_sorovi(origin, user, mavjud_idlar):
    """Kirgandan keyin: «Bu qurilmani eslab qolish» — telefonda yangi kalit yaratish."""
    sozlama = generate_registration_options(
        rp_id=_rp(origin),
        rp_name="Utmost",
        user_name=user.username,
        user_id=f"utmost-{user.pk}".encode(),
        user_display_name=(user.get_full_name() or user.username).strip(),
        exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(k)) for k in mavjud_idlar],
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        timeout=_KUTISH_MS,
    )
    return bytes_to_base64url(sozlama.challenge), options_to_json_dict(sozlama)


def yaratishni_tekshir(javob, savol, origin):
    """Qaytaradi: (kalit_id base64url, ochiq kalit, hisoblagich)."""
    _bir_marta(savol)
    try:
        natija = verify_registration_response(
            credential=javob, expected_challenge=base64url_to_bytes(savol), expected_rp_id=_rp(origin),
            expected_origin=origin, require_user_verification=True,
        )
    except (InvalidRegistrationResponse, ValueError, KeyError, TypeError) as e:
        raise KalitXatosi("Qurilma kaliti saqlanmadi") from e
    return bytes_to_base64url(natija.credential_id), natija.credential_public_key, natija.sign_count
