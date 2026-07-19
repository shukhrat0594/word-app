def owner_mi(user):
    """Platforma egasi (Django superuser) — markazga bog'liq bo'lmagan holda
    barcha markazlardagi hamma narsani ko'rish/boshqarish huquqiga ega.

    Konvensiya: markazga bog'liq (markaz_id bo'yicha filtrlaydigan) har qanday
    yangi view shu tekshiruvni ENG BOSHIDA qo'llashi kerak — shunda yangi
    markaz qo'shilganda ham owner avtomatik ko'radi, alohida sozlash shart
    emas.
    """
    return user.is_superuser


def birlamchi_owner_mi(user):
    """Asosiy (birinchi bo'lib yaratilgan) owner — eng kichik id'ga ega
    superuser. Alohida maydon kerak emas: owner'lar ko'pi bilan 2 ta bo'lgani
    uchun bu doim aniq va o'zgarmas.

    Faqat asosiy owner boshqa owner'ning rolini o'zgartira oladi — ikkinchi
    (keyinroq qo'shilgan) owner asosiy owner'ni pastga tushira olmaydi.
    """
    if not user.is_superuser:
        return False
    from .models import User

    birinchi = User.objects.filter(is_superuser=True).order_by("id").first()
    return birinchi is not None and birinchi.pk == user.pk
