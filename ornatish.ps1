# Loyihani yangi kompyuterda ishga tayyorlash (2026-09-05).
#
# YANGI kompyuterda, ko'chirilgan papka ichida ishga tushiriladi:
#     .\ornatish.ps1
#
# Nima qiladi:
#   1. Git / Python 3.14 / Node.js bor-yo'qligini tekshiradi, yo'q
#      bo'lsa winget orqali o'rnatadi
#   2. venv yaratib, Python paketlarini o'rnatadi
#   3. frontend paketlarini o'rnatadi (npm)
#   4. Bazani tekshiradi (migratsiya)
#   5. Nima qilish kerakligini yozib beradi
#
# Bayroqlar:
#   -KontentAsboblarisiz   PDF/DOCX asboblarini o'rnatmaydi (tezroq)
#   -OrnatmasdanTekshir    hech narsa o'rnatmaydi, faqat holatni ko'rsatadi

param(
    [switch]$KontentAsboblarisiz,
    [switch]$OrnatmasdanTekshir
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Sarlavha($matn) {
    Write-Host ""
    Write-Host "  == $matn" -ForegroundColor Cyan
}
function Yaxshi($matn) { Write-Host "     [OK]   $matn" -ForegroundColor Green }
function Yomon($matn)  { Write-Host "     [XATO] $matn" -ForegroundColor Red }
function Izoh($matn)   { Write-Host "     $matn" -ForegroundColor DarkGray }

# ─────────────────────────────────────────────────────────────────────
Sarlavha "1/5  Kerakli dasturlar"

function Bormi($buyruq) {
    $null = Get-Command $buyruq -ErrorAction SilentlyContinue
    return $?
}

# winget'siz avtomatik o'rnatib bo'lmaydi - qo'lda yo'l ko'rsatamiz.
$wingetBor = Bormi "winget"
if (-not $wingetBor) {
    Izoh "winget topilmadi - dasturlarni qo'lda o'rnatish kerak bo'ladi."
}

# Eng kam versiyalar tekshirilgan (2026-09-05): Django 6.0 va numpy
# `Requires-Python >=3.12`; frontend/package.json `engines.node >=20`.
# Dastur BOR, lekin ESKI bo'lsa ham yangisi o'rnatiladi — aks holda
# `pip install` yarim yo'lda tushunarsiz xato bilan yiqilardi.
$Dasturlar = @(
    @{ Buyruq = "git";    Id = "Git.Git";            Nomi = "Git";      EngKam = $null },
    @{ Buyruq = "python"; Id = "Python.Python.3.14"; Nomi = "Python";   EngKam = [version]"3.12" },
    @{ Buyruq = "node";   Id = "OpenJS.NodeJS";      Nomi = "Node.js";  EngKam = [version]"20.0" }
)

function VersiyaOl($buyruq) {
    try {
        $xom = (& $buyruq --version 2>&1 | Select-Object -First 1) -join " "
        if ($xom -match "(\d+)\.(\d+)(\.(\d+))?") {
            return @{ Matn = $xom.Trim(); Raqam = [version]"$($Matches[1]).$($Matches[2])" }
        }
        return @{ Matn = $xom.Trim(); Raqam = $null }
    } catch {
        return $null
    }
}

$ornatildi = $false
foreach ($d in $Dasturlar) {
    if (Bormi $d.Buyruq) {
        $v = VersiyaOl $d.Buyruq
        if (-not $d.EngKam) {
            Yaxshi "$($d.Nomi) - $($v.Matn)"
            continue
        }
        if ($v.Raqam -and $v.Raqam -ge $d.EngKam) {
            Yaxshi "$($d.Nomi) - $($v.Matn)"
            continue
        }
        if (-not $v.Raqam) {
            # Yangi Windows'da `python` - Microsoft Store'ning BO'SH
            # yorlig'i bo'lishi mumkin: buyruq "bor" ko'rinadi, lekin
            # versiya qaytarmaydi (bosilganda Store ochiladi). Buni
            # "yaxshi" deb o'tkazib yuborsak, keyingi qadamda venv
            # yaratilmay, tushunarsiz xato chiqardi.
            Yomon "$($d.Nomi) - versiya aniqlanmadi (Store yorlig'i bo'lishi mumkin)"
        } else {
            Yomon "$($d.Nomi) - $($v.Matn), eng kami $($d.EngKam) kerak"
        }
        if ($OrnatmasdanTekshir) { continue }
        Izoh "Yangi versiya o'rnatilmoqda..."
    }
    if ($OrnatmasdanTekshir) { Yomon "$($d.Nomi) yo'q"; continue }
    if (-not $wingetBor) {
        Yomon "$($d.Nomi) yo'q - qo'lda o'rnating (winget ham yo'q)"
        continue
    }
    Izoh "$($d.Nomi) o'rnatilmoqda (winget)..."
    winget install --id $d.Id --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -eq 0) { Yaxshi "$($d.Nomi) o'rnatildi"; $ornatildi = $true }
    else { Yomon "$($d.Nomi) o'rnatilmadi (winget kodi $LASTEXITCODE)" }
}

if ($ornatildi) {
    Write-Host ""
    Write-Host "  Yangi dastur o'rnatildi. PowerShell'ni YOPIB, qaytadan" -ForegroundColor Yellow
    Write-Host "  oching va shu skriptni yana bir marta ishga tushiring" -ForegroundColor Yellow
    Write-Host "  (PATH yangilanishi uchun)." -ForegroundColor Yellow
    Write-Host ""
    exit 0
}

if ($OrnatmasdanTekshir) { Izoh "Tekshiruv rejimi - to'xtatildi."; exit 0 }

# ─────────────────────────────────────────────────────────────────────
Sarlavha "2/5  Python muhiti (venv)"

if (-not (Test-Path "venv")) {
    Izoh "venv yaratilmoqda..."
    python -m venv venv
    Yaxshi "venv yaratildi"
} else {
    Yaxshi "venv allaqachon bor"
}

$Py = ".\venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { Yomon "venv buzuq - 'venv' papkasini o'chirib qayta urinib ko'ring"; exit 1 }

Izoh "pip yangilanmoqda..."
& $Py -m pip install --upgrade pip --quiet

Izoh "Paketlar o'rnatilmoqda (requirements.txt, 52 ta)..."
& $Py -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) { Yomon "pip install muvaffaqiyatsiz"; exit 1 }
Yaxshi "Ilova paketlari o'rnatildi"

if (-not $KontentAsboblarisiz -and (Test-Path "requirements-kontent.txt")) {
    Izoh "Kontent asboblari o'rnatilmoqda (PDF/DOCX/OCR)..."
    & $Py -m pip install -r requirements-kontent.txt --quiet
    if ($LASTEXITCODE -eq 0) { Yaxshi "Kontent asboblari o'rnatildi" }
    else { Izoh "Kontent asboblari o'rnatilmadi - ilova baribir ishlaydi" }
}

# ─────────────────────────────────────────────────────────────────────
Sarlavha "3/5  Frontend (npm)"

if (Test-Path "frontend\package.json") {
    Izoh "npm install..."
    Push-Location frontend
    npm install --no-fund --no-audit
    $npmKod = $LASTEXITCODE
    Pop-Location
    if ($npmKod -eq 0) { Yaxshi "Frontend paketlari o'rnatildi" }
    else { Yomon "npm install muvaffaqiyatsiz (kod $npmKod)"; exit 1 }
} else {
    Yomon "frontend\package.json topilmadi"
    exit 1
}

# ─────────────────────────────────────────────────────────────────────
Sarlavha "4/5  Sozlama va baza"

if (Test-Path ".env") {
    Yaxshi ".env joyida"
    # Kalitlarning QIYMATI ko'rsatilmaydi - faqat bor-yo'qligi.
    $env_matn = Get-Content ".env" -Raw
    foreach ($k in @("SECRET_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY")) {
        if ($env_matn -match "(?m)^\s*$k\s*=\s*\S") { Yaxshi "  $k - to'ldirilgan" }
        else { Yomon "  $k - BO'SH yoki yo'q" }
    }
} else {
    Yomon ".env YO'Q - eski kompyuterdan nusxalang (git orqali kelmaydi!)"
    Izoh "Namuna uchun: .env.example"
    exit 1
}

if (Test-Path "db.sqlite3") {
    $mb = [math]::Round((Get-Item "db.sqlite3").Length / 1MB, 1)
    Yaxshi "db.sqlite3 joyida ($mb MB)"
} else {
    Yomon "db.sqlite3 YO'Q - baza bo'sh boshlanadi"
}

if (Test-Path "media") {
    $n = @(Get-ChildItem "media" -Recurse -File -ErrorAction SilentlyContinue).Count
    Yaxshi "media/ joyida ($n fayl)"
} else {
    Yomon "media/ YO'Q - rasm va audiolar ko'rinmaydi"
}

Izoh "Migratsiyalar tekshirilmoqda..."
& $Py manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { Yomon "migrate muvaffaqiyatsiz"; exit 1 }
Yaxshi "Baza tayyor"

# ─────────────────────────────────────────────────────────────────────
Sarlavha "5/5  Tayyor"

Write-Host ""
Write-Host "  Ishga tushirish - IKKITA alohida PowerShell oynasida:" -ForegroundColor Green
Write-Host ""
Write-Host "    1-oyna (backend):"
Write-Host "       .\venv\Scripts\python.exe manage.py runserver 8000" -ForegroundColor White
Write-Host ""
Write-Host "    2-oyna (frontend):"
Write-Host "       npm run dev --prefix frontend" -ForegroundColor White
Write-Host ""
Write-Host "    Brauzerda: http://localhost:3000"
Write-Host ""
Izoh "OCR kerak bo'lsa (pytesseract) alohida dastur ham kerak:"
Izoh "   winget install --id UB-Mannheim.TesseractOCR"
Write-Host ""
