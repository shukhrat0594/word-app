def owner_mi(user):
    """Platforma egasi (Django superuser) — markazga bog'liq bo'lmagan holda
    barcha markazlardagi hamma narsani ko'rish/boshqarish huquqiga ega.

    Konvensiya: markazga bog'liq (markaz_id bo'yicha filtrlaydigan) har qanday
    yangi view shu tekshiruvni ENG BOSHIDA qo'llashi kerak — shunda yangi
    markaz qo'shilganda ham owner avtomatik ko'radi, alohida sozlash shart
    emas.
    """
    return user.is_superuser


def natijalarni_korish_ruxsati(koruvchi, talaba):
    """Talabaning natijalarini (ball, matn, Speaking audiosi) kim ko'ra
    oladi: o'zi, owner/admin, o'z guruhidagi o'qituvchi, o'z farzandi
    uchun ota-ona.

    2026-09-07: bu qoida avval `FoydalanuvchiNatijalariView` ichida
    qotib qolgan edi. Speaking audiosi uchun autentifikatsiyalangan
    endpoint qo'shilganda ikkinchi nusxa kerak bo'ldi — ikki nusxa esa
    vaqt o'tib bir-biridan uzoqlashadi (birida ruxsat toraysa,
    ikkinchisida ochiq qolib ketardi). Shuning uchun bitta joyda.

    `_rasm_korish_ruxsati` (accounts/views.py) bilan ATAYLAB
    birlashtirilmadi: u profil rasmi uchun va qoidasi kengroq —
    klassdoshlar ham bir-birining rasmini ko'radi. Natija esa
    shaxsiyroq, klassdoshga ochiq emas.
    """
    if koruvchi.pk == talaba.pk:
        return True
    if owner_mi(koruvchi):
        return True

    from .models import User

    if koruvchi.role == User.Role.ADMIN:
        return True
    if koruvchi.role == User.Role.TEACHER:
        from academics.models import Guruh

        return Guruh.objects.filter(oqituvchi=koruvchi, talabalar=talaba).exists()
    if koruvchi.role == User.Role.PARENT:
        return talaba.ota_ona_id == koruvchi.pk
    return False


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
