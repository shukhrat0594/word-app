# Loyihani boshqa kompyuterga ko'chirishga tayyorlash (2026-09-05).
#
# ESKI kompyuterda ishga tushiriladi. Butun loyiha papkasini tashqi
# diskka nusxalaydi, lekin QAYTA O'RNATILADIGAN narsalarni tashlab
# ketadi (venv ~324 MB, node_modules ~94 MB, __pycache__) — ular yangi
# kompyuterda `ornatish.ps1` orqali o'zi quriladi va boshqa Python
# versiyasida eskisi baribir ishlamaydi.
#
# Ishlatish:
#     .\kochirish_tayyorla.ps1 -Manzil E:\LMS-kochirish
#     .\kochirish_tayyorla.ps1 -Manzil E:\LMS-kochirish -KitoblarSiz
#
# DIQQAT: `.env` fayl ham nusxalanadi — ichida API kalitlar va
# SECRET_KEY bor. Tashqi diskni boshqa odamga bermang.

param(
    [Parameter(Mandatory = $true)]
    [string]$Manzil,

    # Kitob PDF'lari va ish artefaktlarisiz (~14 GB tejaladi)
    [switch]$KitoblarSiz,

    # Hech narsa nusxalamaydi — faqat NIMA nusxalanishini ko'rsatadi.
    # Haqiqiy ko'chirishdan oldin tekshirib olish uchun.
    [switch]$Sinov
)

$ErrorActionPreference = "Stop"
$Manba = $PSScriptRoot

Write-Host ""
Write-Host "  Manba : $Manba"
Write-Host "  Manzil: $Manzil"
Write-Host ""

if (-not $Sinov -and -not (Test-Path $Manzil)) {
    New-Item -ItemType Directory -Path $Manzil -Force | Out-Null
    Write-Host "  Papka yaratildi." -ForegroundColor DarkGray
}

# Nusxalanmaydigan papkalar. venv va node_modules ATAYLAB tashlanadi:
# ular platformaga bog'liq, yangi mashinada qaytadan quriladi.
$OtkazibYuborish = @("venv", "node_modules", "__pycache__", ".pytest_cache", "staticfiles")
if ($KitoblarSiz) {
    $OtkazibYuborish += @("Cambridge IELTS library", "Headway", "tmp")
}

$RcArgs = @(
    $Manba, $Manzil,
    "/E",            # bo'sh papkalar bilan birga butun daraxt
    "/XD"
) + $OtkazibYuborish + @(
    "/XF", "*.pyc", "*.pyo",
    "/R:2", "/W:2",  # xatoda 2 marta urinish, 2 sekund kutish
    "/NFL", "/NDL",  # har faylni ro'yxatlamasin - chiqish o'qilishi uchun
    "/NP",           # foizli progress bar yozuvni buzadi
    "/TEE"
)

if ($Sinov) {
    # /L — robocopy'ning o'z "faqat ro'yxatla" rejimi: bironta ham
    # fayl yozilmaydi, lekin hisob-kitob haqiqiy nusxalashdagidek.
    Write-Host "  SINOV rejimi — hech narsa nusxalanmaydi." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Tashlab ketiladi: $($OtkazibYuborish -join ', ')" -ForegroundColor DarkGray
    Write-Host ""
    robocopy @RcArgs "/L" | Select-Object -Last 12
    Write-Host ""
    Write-Host "  Haqiqiy ko'chirish uchun -Sinov ni olib tashlang." -ForegroundColor Yellow
    Write-Host ""
    exit 0
}

Write-Host "  Nusxalanmoqda... (18 GB uchun 10-30 daqiqa, diskka bog'liq)" -ForegroundColor Cyan
Write-Host ""
$boshlandi = Get-Date
robocopy @RcArgs
$kod = $LASTEXITCODE
$vaqt = (Get-Date) - $boshlandi

# Robocopy 0-7 = muvaffaqiyat (8 va undan yuqori = haqiqiy xato).
if ($kod -ge 8) {
    Write-Host ""
    Write-Host "  XATO: robocopy $kod kodi bilan tugadi." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "  Nusxalash tugadi ($([int]$vaqt.TotalMinutes) daqiqa)." -ForegroundColor Green
Write-Host ""

# ── Bazani XAVFSIZ qayta nusxalash ───────────────────────────────────
# db.sqlite3 WAL rejimida: so'nggi yozuvlar asosiy faylda EMAS, yonidagi
# `-wal` faylida turadi. Robocopy ikkalasini turli lahzalarda nusxalashi
# mumkin - natijada chala yoki buzuq baza. SQLite'ning o'z `backup()`
# API'si esa tranzaksiyalarni hisobga oladi va server ishlab turganda
# ham BUTUN, izchil nusxa beradi. Shuning uchun robocopy nusxasini shu
# yerda ustidan yozamiz.
$Py = Join-Path $Manba "venv\Scripts\python.exe"
$dbManba = Join-Path $Manba "db.sqlite3"
$dbManzil = Join-Path $Manzil "db.sqlite3"

if ((Test-Path $Py) -and (Test-Path $dbManba)) {
    Write-Host "  Baza xavfsiz nusxalanmoqda (SQLite backup API)..." -ForegroundColor Cyan
    $kodPy = @"
import sqlite3, sys
manba, manzil = sys.argv[1], sys.argv[2]
src = sqlite3.connect(f'file:{manba}?mode=ro', uri=True)
dst = sqlite3.connect(manzil)
with dst:
    src.backup(dst)
natija = dst.execute('PRAGMA integrity_check').fetchone()[0]
jadval = dst.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
src.close(); dst.close()
print(f'{natija}|{jadval}')
"@
    $vaqtinchalik = Join-Path $env:TEMP "lms_db_backup.py"
    [System.IO.File]::WriteAllText($vaqtinchalik, $kodPy, [System.Text.UTF8Encoding]::new($false))
    $javob = & $Py $vaqtinchalik $dbManba $dbManzil 2>&1
    Remove-Item $vaqtinchalik -ErrorAction SilentlyContinue

    if ($LASTEXITCODE -eq 0 -and $javob -match "^ok\|(\d+)$") {
        Write-Host "     [OK]   Baza butun - integrity_check ok, $($Matches[1]) ta jadval" -ForegroundColor Green
    } else {
        Write-Host "     [XATO] Baza nusxalanmadi: $javob" -ForegroundColor Red
        Write-Host "            Serverlarni to'xtatib, qaytadan urinib ko'ring." -ForegroundColor Red
        exit 1
    }
    # `-wal`/`-shm` ESKI mashinaning ish fayllari - yangi nusxada
    # kerak emas va faqat chalkashtiradi (backup ularni asosiy faylga
    # allaqachon singdirdi).
    foreach ($q in "db.sqlite3-wal", "db.sqlite3-shm") {
        $y = Join-Path $Manzil $q
        if (Test-Path $y) { Remove-Item $y -Force }
    }
    Write-Host ""
} elseif (Test-Path $dbManba) {
    Write-Host "  DIQQAT: venv topilmadi, baza oddiy nusxalandi." -ForegroundColor Yellow
    Write-Host "          Serverlar ishlab turgan bo'lsa baza chala bo'lishi mumkin." -ForegroundColor Yellow
    Write-Host ""
}

# ── Tekshiruv: eng muhim, git'da YO'Q narsalar joyidami ──────────────
Write-Host "  Tekshiruv:"
$xato = $false
$muhim = @{
    ".env"                                  = "API kalitlar va SECRET_KEY"
    "db.sqlite3"                            = "butun baza"
    "media"                                 = "rasm va audio fayllar"
    "requirements.txt"                      = "Python paketlari"
    "ornatish.ps1"                          = "o'rnatish skripti"
}
foreach ($k in $muhim.Keys | Sort-Object) {
    $yol = Join-Path $Manzil $k
    if (Test-Path $yol) {
        Write-Host ("    [OK]   {0,-20} - {1}" -f $k, $muhim[$k]) -ForegroundColor Green
    } else {
        Write-Host ("    [YO'Q] {0,-20} - {1}" -f $k, $muhim[$k]) -ForegroundColor Red
        $xato = $true
    }
}

# Headway Unit skriptlari - `.gitignore` da, ya'ni GitHub'dan KELMAYDI.
$hw = @(Get-ChildItem (Join-Path $Manzil "courses\management\commands") -Filter "headway_*unit*.py" -ErrorAction SilentlyContinue).Count
if ($hw -gt 0) {
    Write-Host ("    [OK]   {0,-20} - {1} ta fayl (git'da yo'q!)" -f "headway_*unit*.py", $hw) -ForegroundColor Green
} else {
    Write-Host ("    [YO'Q] {0,-20} - Unit kontent skriptlari" -f "headway_*unit*.py") -ForegroundColor Red
    $xato = $true
}

$hajm = (Get-ChildItem $Manzil -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum / 1GB
Write-Host ""
Write-Host ("  Jami: {0:N1} GB" -f $hajm)
Write-Host ""

if ($xato) {
    Write-Host "  DIQQAT: yuqoridagi YO'Q bandlarni tekshiring." -ForegroundColor Red
    exit 1
}

Write-Host "  Tayyor. Yangi kompyuterda:" -ForegroundColor Green
Write-Host "    1. Shu papkani diskka nusxalang (masalan D:\LMS)"
Write-Host "    2. PowerShell'da o'sha papkaga kiring"
Write-Host "    3. .\ornatish.ps1"
Write-Host ""
