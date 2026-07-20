"""20 ta yangi Listening mashqi (5 tur x 4 tadan) — Shukhrat bilan kelishilgan
tarzda yozilgan, Gemini TTS orqali audio generatsiya qilinadi (2026-07-20).

Har bir tur bo'yicha 2 tasi gemini-2.5-flash-preview-tts, 2 tasi
gemini-3.1-flash-tts-preview bilan (jami 10/10). Bepul tarif juda cheklangan
(RPD=10/kun, HAR MODEL UCHUN ALOHIDA) — RateLimitTugadi chiqsa to'xtaydi,
idempotent (audio fayli allaqachon bor bo'lsa qayta yaratmaydi, Mashq
nomi bo'yicha ham qayta yaratilmaydi).

map_labelling turi uchun rasm PIL bilan shu yerda generatsiya qilinadi
(exercises/import_data/images/).
"""

import shutil

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image, ImageDraw, ImageFont

from accounts.models import Markaz
from exercises.gemini_tts import RateLimitTugadi, audio_yarat
from exercises.models import Bolim, Mashq, Tur

AUDIO_DIR = settings.BASE_DIR / "exercises" / "import_data" / "audio"
IMAGE_DIR = settings.BASE_DIR / "exercises" / "import_data" / "images"

M25 = "gemini-2.5-flash-preview-tts"
M31 = "gemini-3.1-flash-tts-preview"
OVOZLAR = [("Speaker1", "Kore"), ("Speaker2", "Puck")]


def _savol(savol, variantlar, togri):
    return {"savol": savol, "variantlar": variantlar, "togri": togri}


# ---- 1. Multiple Choice (4) ----
MULTIPLE_CHOICE = [
    {
        "fayl": "mc-01-doctor",
        "model": M25,
        "dialog": True,
        "name": "Doctor's Appointment",
        "transkript": """Speaker1: Good morning, Riverside Medical Clinic, how can I help you?
Speaker2: Hi, I'd like to book an appointment with Doctor Adams.
Speaker1: I'm afraid Doctor Adams is fully booked this week. Would you like to see Doctor Chen instead?
Speaker2: That's fine. Do you have anything available tomorrow?
Speaker1: Yes, we have a slot at eleven fifteen in the morning, or three thirty in the afternoon.
Speaker2: I'll take the morning slot, please.
Speaker1: Great, and is this for a general check-up or something specific?
Speaker2: I've had a sore throat for about a week, so I'd like it checked.
Speaker1: Understood. Please arrive fifteen minutes early to complete a short form.
Speaker2: Will do. Thank you very much.""",
        "savollar": [
            _savol("Which doctor will the caller see?", ["Doctor Adams", "Doctor Chen", "Doctor Lee", "Doctor Kim"], "Doctor Chen"),
            _savol("What time is the appointment?", ["11:15 am", "3:30 pm", "9:00 am", "1:00 pm"], "11:15 am"),
            _savol("Why does the caller need an appointment?", ["Annual check-up", "Sore throat", "Broken arm", "Eye test"], "Sore throat"),
            _savol("How early should the caller arrive?", ["Five minutes", "Ten minutes", "Fifteen minutes", "Thirty minutes"], "Fifteen minutes"),
        ],
    },
    {
        "fayl": "mc-02-car-rental",
        "model": M31,
        "dialog": True,
        "name": "Car Rental",
        "transkript": """Speaker1: Good afternoon, Sunshine Car Rentals, how can I assist you today?
Speaker2: Hi, I'd like to rent a car for a week starting this Friday.
Speaker1: Certainly. We have a compact car for thirty-five dollars a day, or an SUV for fifty-five dollars a day.
Speaker2: I'll go with the SUV, please.
Speaker1: Great choice. Would you like to add insurance coverage for an extra twelve dollars a day?
Speaker2: Yes, I think that's a good idea.
Speaker1: Understood. And will you be returning the car to this same branch?
Speaker2: No, actually I'll be dropping it off at the airport branch.
Speaker1: That's fine, though there's a twenty-dollar one-way fee for that.
Speaker2: That's okay, I'll accept that.
Speaker1: Perfect. Please bring your driving licence and a credit card when you collect the car.""",
        "savollar": [
            _savol("Which vehicle does the customer choose?", ["Compact car", "SUV", "Van", "Motorbike"], "SUV"),
            _savol("How much is the daily insurance cost?", ["$12", "$20", "$35", "$55"], "$12"),
            _savol("Where will the car be returned?", ["Same branch", "Airport branch", "City center branch", "Train station"], "Airport branch"),
            _savol("What should the customer bring when collecting the car?", ["Passport only", "Driving licence and credit card", "Cash only", "Insurance certificate"], "Driving licence and credit card"),
        ],
    },
    {
        "fayl": "mc-03-job-feedback",
        "model": M25,
        "dialog": True,
        "name": "Job Interview Feedback",
        "transkript": """Speaker1: Hi, this is Rachel from Bright Star Recruitment, calling about your interview.
Speaker2: Oh hi, thanks for calling. How did it go?
Speaker1: The manager was very impressed with your communication skills.
Speaker2: That's great to hear.
Speaker1: However, they felt your experience with data analysis software was a little limited.
Speaker2: I see. Is there anything I can do?
Speaker1: They've suggested a short online course, and they'd like to interview you again in three weeks.
Speaker2: That sounds fair. What time would work for the second interview?
Speaker1: They suggested Thursday at ten in the morning.
Speaker2: That works well for me.
Speaker1: Wonderful, I'll confirm that and send you the details by email.""",
        "savollar": [
            _savol("What impressed the manager?", ["Technical skills", "Communication skills", "Punctuality", "Previous experience"], "Communication skills"),
            _savol("What area needs improvement?", ["Teamwork", "Data analysis software", "Time management", "Writing skills"], "Data analysis software"),
            _savol("When is the second interview?", ["Monday", "Tuesday", "Wednesday", "Thursday"], "Thursday"),
            _savol("How will the details be sent?", ["By phone", "By email", "By post", "In person"], "By email"),
        ],
    },
    {
        "fayl": "mc-04-internet",
        "model": M31,
        "dialog": True,
        "name": "Internet Service Setup",
        "transkript": """Speaker1: Thank you for calling FastNet Support, how can I help?
Speaker2: Hi, my internet connection has been really slow since yesterday.
Speaker1: I'm sorry to hear that. Could you tell me which package you're subscribed to?
Speaker2: I believe it's the Standard package.
Speaker1: I see. That package offers speeds up to fifty megabits per second. Let me run a quick check on the line.
Speaker2: Sure, go ahead.
Speaker1: It looks like there's a fault on the line in your area, affecting several customers.
Speaker2: Oh, that explains it. When will it be fixed?
Speaker1: Our engineers expect to resolve it by six o'clock this evening.
Speaker2: Okay, thank you. Will I get any compensation for this?
Speaker1: Yes, we'll apply a ten percent discount to your next bill automatically.""",
        "savollar": [
            _savol("What package is the customer subscribed to?", ["Basic", "Standard", "Premium", "Ultra"], "Standard"),
            _savol("What is the maximum speed of this package?", ["20 Mbps", "50 Mbps", "100 Mbps", "200 Mbps"], "50 Mbps"),
            _savol("What caused the problem?", ["Customer's router", "A fault on the line", "Payment issue", "Weather damage"], "A fault on the line"),
            _savol("What compensation will the customer receive?", ["Free month", "10% discount", "New router", "Refund"], "10% discount"),
        ],
    },
]

# ---- 2. Matching (4) ----
MATCHING = [
    {
        "fayl": "match-01-departments",
        "model": M31,
        "dialog": False,
        "name": "University Departments",
        "transkript": "Let me tell you which department each of our new professors will be joining. Professor Kim, who specializes in molecular biology, will be joining the Science department. Professor Alvarez, an expert in ancient civilizations, will be joining the History department. Professor Novak, who has years of experience in software development, will be joining the Computer Science department. Professor Bennett, who focuses on macroeconomics, will be joining the Economics department.",
        "items": ["Professor Kim", "Professor Alvarez", "Professor Novak", "Professor Bennett"],
        "options": ["Science", "History", "Computer Science", "Economics", "Mathematics"],
        "mapping": {"Professor Kim": "Science", "Professor Alvarez": "History", "Professor Novak": "Computer Science", "Professor Bennett": "Economics"},
    },
    {
        "fayl": "match-02-office",
        "model": M25,
        "dialog": False,
        "name": "Office Room Directory",
        "transkript": "Welcome to Meridian Tower. Let me explain where each department is located. The Human Resources department is on the third floor. The Marketing team works on the fifth floor. The IT support desk is located in the basement. And the Finance department can be found on the seventh floor.",
        "items": ["Human Resources", "Marketing", "IT support", "Finance"],
        "options": ["Third floor", "Fifth floor", "Basement", "Seventh floor", "Ground floor"],
        "mapping": {"Human Resources": "Third floor", "Marketing": "Fifth floor", "IT support": "Basement", "Finance": "Seventh floor"},
    },
    {
        "fayl": "match-03-schedule",
        "model": M31,
        "dialog": False,
        "name": "Weekly Class Schedule",
        "transkript": "Let me go through this week's evening class schedule. The Pottery class takes place on Monday evenings. The Yoga class is held on Wednesday evenings. Beginner Spanish is taught on Thursday evenings. And the Photography class runs on Saturday mornings.",
        "items": ["Pottery class", "Yoga class", "Beginner Spanish", "Photography class"],
        "options": ["Monday evening", "Wednesday evening", "Thursday evening", "Saturday morning", "Sunday afternoon"],
        "mapping": {"Pottery class": "Monday evening", "Yoga class": "Wednesday evening", "Beginner Spanish": "Thursday evening", "Photography class": "Saturday morning"},
    },
    {
        "fayl": "match-04-volunteers",
        "model": M25,
        "dialog": False,
        "name": "Volunteer Roles",
        "transkript": "For this weekend's charity event, here's who's doing what. Maria will be in charge of registering guests at the front desk. James will be managing the food and drinks table. Sophie will be looking after the children's activity area. And David will be responsible for collecting donations.",
        "items": ["Maria", "James", "Sophie", "David"],
        "options": ["Registering guests", "Managing food and drinks", "Children's activity area", "Collecting donations", "Parking cars"],
        "mapping": {"Maria": "Registering guests", "James": "Managing food and drinks", "Sophie": "Children's activity area", "David": "Collecting donations"},
    },
]

# ---- 3. Map Labelling (4) ----
MAP_LABELLING = [
    {
        "fayl": "map-01-community",
        "model": M25,
        "dialog": False,
        "name": "Community Center Floor Plan",
        "transkript": "Let me guide you around the Greenfield Community Center. As you enter through the main entrance, the reception desk, marked A, is straight ahead of you. To your left is the large hall, marked B, used for events and meetings. Just past the hall is the cafe, marked C, where you can get drinks and snacks. On the right-hand side of the building is the library corner, marked D. And at the very back of the building, you'll find the art studio, marked E.",
        "sarlavha": "Greenfield Community Center",
        "nuqtalar": {"A": "Reception desk", "B": "Large hall", "C": "Cafe", "D": "Library corner", "E": "Art studio"},
    },
    {
        "fayl": "map-02-park",
        "model": M31,
        "dialog": False,
        "name": "Town Park Map",
        "transkript": "Welcome to Elmwood Park. Let's look at where everything is. Right by the main gate is the playground, marked A. Walking along the path, you'll reach the pond, marked B, on your left. Continuing further, there's a picnic area, marked C, shaded by large trees. To the north of the pond is the sports field, marked D. And near the eastern exit, you'll find the flower garden, marked E.",
        "sarlavha": "Elmwood Park",
        "nuqtalar": {"A": "Playground", "B": "Pond", "C": "Picnic area", "D": "Sports field", "E": "Flower garden"},
    },
    {
        "fayl": "map-03-mall",
        "model": M25,
        "dialog": False,
        "name": "Shopping Mall Directory",
        "transkript": "Welcome to Riverside Mall. Here's a quick guide to the ground floor. Directly opposite the main entrance is the information desk, marked A. To the left, you'll find the electronics store, marked B. Next to that is the food court, marked C, which has several restaurants. On the right side of the mall is the clothing store, marked D. And near the escalators is the cinema entrance, marked E.",
        "sarlavha": "Riverside Mall — Ground Floor",
        "nuqtalar": {"A": "Information desk", "B": "Electronics store", "C": "Food court", "D": "Clothing store", "E": "Cinema entrance"},
    },
    {
        "fayl": "map-04-campus",
        "model": M31,
        "dialog": False,
        "name": "University Campus Map",
        "transkript": "Let me show you around the university campus. As you come through the main gate, the administration building, marked A, is on your right. Walking straight ahead, you'll reach the library, marked B. To the left of the library is the science building, marked C. Behind the library is the student cafeteria, marked D. And at the far end of campus is the sports center, marked E.",
        "sarlavha": "University Campus",
        "nuqtalar": {"A": "Administration building", "B": "Library", "C": "Science building", "D": "Student cafeteria", "E": "Sports center"},
    },
]

# ---- 4. Fill in the Blanks (4) ----
FILL_BLANKS = [
    {
        "fayl": "fb-01-insurance",
        "model": M31,
        "dialog": True,
        "name": "Car Insurance Application",
        "transkript": """Speaker1: Good morning, I'd like to get a quote for car insurance.
Speaker2: Of course, could I take your full name first?
Speaker1: Yes, it's Daniel Foster.
Speaker2: Thank you, Mr. Foster. And what's the make and model of your car?
Speaker1: It's a Toyota Corolla.
Speaker2: What year was it manufactured?
Speaker1: It's a twenty twenty-one model.
Speaker2: And how many years of driving experience do you have?
Speaker1: I've been driving for six years.
Speaker2: Great. Lastly, where is the car usually parked overnight?
Speaker1: In a private garage at my house.""",
        "savollar": [
            _savol("Full name:", [], "Daniel Foster"),
            _savol("Car model:", [], "Toyota Corolla"),
            _savol("Year manufactured:", [], "2021"),
            _savol("Driving experience:", [], "six years"),
            _savol("Overnight parking:", [], "private garage"),
        ],
    },
    {
        "fayl": "fb-02-delivery",
        "model": M25,
        "dialog": True,
        "name": "Package Delivery Note",
        "transkript": """Speaker1: Hello, this is QuickShip calling about your delivery.
Speaker2: Hi, yes, I've been expecting a package.
Speaker1: I just need to confirm a few details. Can I confirm the recipient's name?
Speaker2: Yes, it's Grace Miller.
Speaker1: And the delivery address?
Speaker2: Forty-two Baker Street.
Speaker1: What time would be best for delivery tomorrow?
Speaker2: Anytime after two in the afternoon would be great.
Speaker1: Understood. And is there a safe place to leave the package if you're not home?
Speaker2: Yes, you can leave it with my neighbour at number forty-four.""",
        "savollar": [
            _savol("Recipient name:", [], "Grace Miller"),
            _savol("Delivery address:", [], "42 Baker Street"),
            _savol("Preferred time:", [], "after 2 pm"),
            _savol("Safe place:", [], "neighbour at number 44"),
        ],
    },
    {
        "fayl": "fb-03-membership",
        "model": M31,
        "dialog": True,
        "name": "Membership Renewal Form",
        "transkript": """Speaker1: Hi, I'd like to renew my membership at the sports club.
Speaker2: Sure, can I take your membership number?
Speaker1: It's SC dash four four seven two.
Speaker2: Thank you. And which plan would you like to renew, monthly or annual?
Speaker1: I'll go with the annual plan this time.
Speaker2: Great choice, that saves you money. And how would you like to pay?
Speaker1: By credit card, please.
Speaker2: No problem. Finally, would you like to add a family member to your membership?
Speaker1: Yes, please add my son, Oliver.""",
        "savollar": [
            _savol("Membership number:", [], "SC-4472"),
            _savol("Plan type:", [], "annual"),
            _savol("Payment method:", [], "credit card"),
            _savol("Additional member:", [], "Oliver"),
        ],
    },
    {
        "fayl": "fb-04-itinerary",
        "model": M25,
        "dialog": False,
        "name": "Travel Itinerary Notes",
        "transkript": "Let me go over your travel itinerary for next week. Your flight departs from Terminal Two at nine forty-five in the morning. You'll be flying with Blue Sky Airlines, flight number BS one one eight. Upon arrival, a taxi will take you directly to the Grand Palace Hotel. Your return flight is scheduled for the following Friday at six thirty in the evening.",
        "savollar": [
            _savol("Departure terminal:", [], "Terminal Two"),
            _savol("Airline:", [], "Blue Sky Airlines"),
            _savol("Flight number:", [], "BS 118"),
            _savol("Hotel name:", [], "Grand Palace Hotel"),
            _savol("Return day:", [], "Friday"),
        ],
    },
]

# ---- 5. Short Answer (4) ----
SHORT_ANSWER = [
    {
        "fayl": "sa-01-recycling",
        "model": M31,
        "dialog": False,
        "name": "Recycling Guidelines",
        "transkript": "I'd like to remind everyone about our recycling rules. Paper and cardboard should go into the blue bin. Glass bottles and jars belong in the green bin. Plastic containers must be rinsed before being placed in the yellow bin. Food waste should go into the brown compost bin, and general rubbish that can't be recycled goes into the black bin. Collection day for all bins is every Tuesday morning.",
        "savollar": [
            _savol("What color bin is for glass?", [], "green"),
            _savol("What must be done to plastic containers before recycling?", [], "rinsed"),
            _savol("What day is collection?", [], "Tuesday"),
            _savol("What color bin is for food waste?", [], "brown"),
        ],
    },
    {
        "fayl": "sa-02-weather",
        "model": M25,
        "dialog": False,
        "name": "Weather Forecast",
        "transkript": "Good morning, here's today's weather forecast. It will be cloudy in the morning with temperatures around fourteen degrees. By midday, we expect some sunshine with temperatures rising to nineteen degrees. However, there's a chance of light rain in the evening, so it's a good idea to carry an umbrella. Winds will be light throughout the day, coming from the west.",
        "savollar": [
            _savol("What's the temperature at midday?", [], "nineteen degrees"),
            _savol("What's expected in the evening?", [], "light rain"),
            _savol("What should people carry?", [], "an umbrella"),
            _savol("Which direction is the wind coming from?", [], "west"),
        ],
    },
    {
        "fayl": "sa-03-lostfound",
        "model": M31,
        "dialog": True,
        "name": "Lost and Found",
        "transkript": """Speaker1: Hi, I think I left my umbrella on the bus yesterday.
Speaker2: I can check our lost property records. What color was it?
Speaker1: It was black with a wooden handle.
Speaker2: And which bus route were you on?
Speaker1: The number twelve, heading downtown.
Speaker2: What time approximately?
Speaker1: Around five in the evening.
Speaker2: Let me check... yes, we do have a black umbrella here matching that description.""",
        "savollar": [
            _savol("What color was the umbrella?", [], "black"),
            _savol("What was special about the handle?", [], "wooden"),
            _savol("Which bus route?", [], "number twelve"),
            _savol("What time was it?", [], "five in the evening"),
        ],
    },
    {
        "fayl": "sa-04-recipe",
        "model": M25,
        "dialog": False,
        "name": "Cooking Recipe Instructions",
        "transkript": "Today I'll show you how to make a simple vegetable soup. First, chop two onions and one carrot into small pieces. Heat some oil in a large pot and cook the vegetables for five minutes. Next, add four cups of vegetable stock and bring it to a boil. Let it simmer for twenty minutes, then season with salt and pepper before serving.",
        "savollar": [
            _savol("How many onions are needed?", [], "two"),
            _savol("How long should the vegetables cook initially?", [], "five minutes"),
            _savol("How many cups of vegetable stock are added?", [], "four"),
            _savol("How long should the soup simmer?", [], "twenty minutes"),
        ],
    },
]


def _map_rasm_yasa(fayl_nomi, sarlavha, nuqtalar):
    """map_labelling uchun sodda sxematik rasm (PNG) chizadi."""
    yol = IMAGE_DIR / f"{fayl_nomi}.png"
    if yol.exists():
        return yol
    img = Image.new("RGB", (700, 450), "#FAF9F6")
    draw = ImageDraw.Draw(img)
    try:
        font_katta = ImageFont.truetype("arial.ttf", 20)
        font_kichik = ImageFont.truetype("arial.ttf", 15)
    except OSError:
        font_katta = ImageFont.load_default()
        font_kichik = ImageFont.load_default()

    draw.rectangle([20, 20, 680, 430], outline="#2B2A28", width=3)
    draw.text((350, 40), sarlavha, fill="#2B2A28", font=font_katta, anchor="mm")

    joylashuv = [(150, 130), (500, 130), (150, 260), (500, 260), (325, 370)]
    for (harf, nom), (x, y) in zip(nuqtalar.items(), joylashuv):
        draw.ellipse([x - 25, y - 25, x + 25, y + 25], outline="#E6BE00", width=4)
        draw.text((x, y), harf, fill="#2B2A28", font=font_katta, anchor="mm")
        draw.text((x, y + 40), nom, fill="#6B6862", font=font_kichik, anchor="mm")

    img.save(yol)
    return yol


class Command(BaseCommand):
    help = "20 ta yangi Listening mashqini (5 tur x 4) Gemini TTS bilan yaratadi"

    def handle(self, *args, **options):
        markaz = Markaz.objects.first()
        if not markaz:
            self.stdout.write(self.style.ERROR("Markaz topilmadi"))
            return

        yaratildi = 0
        tugagan_modellar = set()

        vazifalar = (
            [(m, Tur.MULTIPLE_CHOICE, m["savollar"], None) for m in MULTIPLE_CHOICE]
            + [
                (m, Tur.MATCHING, [_savol(item, m["options"], m["mapping"][item]) for item in m["items"]], None)
                for m in MATCHING
            ]
            + [
                (
                    m, Tur.MAP_LABELLING,
                    [_savol(f"Nima {harf} bilan belgilangan?", list(m["nuqtalar"].values()), nom) for harf, nom in m["nuqtalar"].items()],
                    _map_rasm_yasa(m["fayl"], m["sarlavha"], m["nuqtalar"]),
                )
                for m in MAP_LABELLING
            ]
            + [(m, Tur.FILL_BLANKS, m["savollar"], None) for m in FILL_BLANKS]
            + [(m, Tur.SHORT_ANSWER, m["savollar"], None) for m in SHORT_ANSWER]
        )

        for m, tur, savollar, rasm_yol in vazifalar:
            if m["model"] in tugagan_modellar:
                self.stdout.write(f"{m['fayl']}: {m['model']} limiti tugagan, o'tkazib yuborildi")
                continue
            ok = self._audio_va_mashq(markaz, m, tur, savollar, rasm_yol=rasm_yol)
            if ok is None:
                tugagan_modellar.add(m["model"])
                continue
            yaratildi += int(ok)

        if tugagan_modellar:
            self.stdout.write(self.style.WARNING(f"Limit tugagan modellar: {', '.join(tugagan_modellar)}"))
        self.stdout.write(self.style.SUCCESS(f"Jami yaratildi: {yaratildi}"))

    def _audio_va_mashq(self, markaz, m, tur, savollar, rasm_yol=None):
        """Audio (agar yo'q bo'lsa) generatsiya qiladi, HAR DOIM MEDIA_ROOT'ga
        qayta nusxalaydi (ephemeral disk himoyasi — wordapp_import'dagi bilan
        bir xil naqsh), so'ng Mashq yaratadi (yoki mavjudining audio/rasm
        yo'lini yangilaydi).

        Qaytaradi: True (yangi yaratildi), False (allaqachon bor/yangilandi),
        None (limit tugadi)."""
        name = f"[Yangi] {m['name']}"
        wav_yol = AUDIO_DIR / f"{m['fayl']}.wav"
        if not wav_yol.exists():
            try:
                speakerlar = OVOZLAR if m["dialog"] else None
                wav_bytes = audio_yarat(m["transkript"], m["model"], speakerlar=speakerlar)
            except RateLimitTugadi as e:
                self.stdout.write(self.style.WARNING(f"{m['fayl']}: limit tugadi — {e}"))
                return None
            wav_yol.write_bytes(wav_bytes)
            self.stdout.write(self.style.SUCCESS(f"{m['fayl']}: audio yaratildi ({len(wav_bytes)} bayt)"))

        nishab = settings.MEDIA_ROOT / "mashqlar" / "audio" / f"{m['fayl']}.wav"
        nishab.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wav_yol, nishab)
        nisbiy_audio = f"mashqlar/audio/{m['fayl']}.wav"

        nisbiy_rasm = None
        if rasm_yol:
            nishab_rasm = settings.MEDIA_ROOT / "mashqlar" / "rasm" / rasm_yol.name
            nishab_rasm.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(rasm_yol, nishab_rasm)
            nisbiy_rasm = f"mashqlar/rasm/{rasm_yol.name}"

        mashq = Mashq.objects.filter(markaz=markaz, name=name, bolim=Bolim.LISTENING, tur=tur).first()
        if mashq:
            yangilandi = False
            if mashq.audio_fayl.name != nisbiy_audio:
                mashq.audio_fayl.name = nisbiy_audio
                yangilandi = True
            if nisbiy_rasm and mashq.rasm.name != nisbiy_rasm:
                mashq.rasm.name = nisbiy_rasm
                yangilandi = True
            if yangilandi:
                mashq.save()
            self.stdout.write(f"{m['fayl']}: mashq allaqachon bor")
            return False

        mashq = Mashq(
            markaz=markaz, name=name, bolim=Bolim.LISTENING, tur=tur, korinish="public",
            matn=m["transkript"], savollar=savollar, audio_fayl=nisbiy_audio,
        )
        if nisbiy_rasm:
            mashq.rasm = nisbiy_rasm
        mashq.full_clean()
        mashq.save()
        self.stdout.write(self.style.SUCCESS(f"{m['fayl']}: Mashq yaratildi (id={mashq.id})"))
        return True
