def owner_mi(user):
    """Platforma egasi (Django superuser) — markazga bog'liq bo'lmagan holda
    barcha markazlardagi hamma narsani ko'rish/boshqarish huquqiga ega.

    Konvensiya: markazga bog'liq (markaz_id bo'yicha filtrlaydigan) har qanday
    yangi view shu tekshiruvni ENG BOSHIDA qo'llashi kerak — shunda yangi
    markaz qo'shilganda ham owner avtomatik ko'radi, alohida sozlash shart
    emas.
    """
    return user.is_superuser
