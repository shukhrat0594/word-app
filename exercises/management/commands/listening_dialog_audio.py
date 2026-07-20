"""Mavjud Listening audiolaridan dialog bo'lishi kerak bo'lganlarini Gemini
TTS orqali 2 ovozli (Speaker1/Speaker2) qilib qayta yozadi (2026-07-20).

word-app-backup'dan import qilingan 12 ta audio bitta ovozda edi — 9 tasi
aslida 2 kishilik suhbat (kutubxona, mehmonxona va h.k.), lekin bitta ovozda
gapiruvchilar farqlanmagan edi. Bu buyruq shu 9 tasini qayta yaratadi.

Bepul tarif juda cheklangan (RPD=10/kun) — RateLimitTugadi chiqsa to'xtaydi,
qolganini keyingi safar davom ettirish mumkin (idempotent — allaqachon
.wav fayli bor bo'lsa qayta yaratmaydi).
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from exercises.gemini_tts import RateLimitTugadi, audio_yarat

AUDIO_DIR = settings.BASE_DIR / "exercises" / "import_data" / "audio"

MODEL = "gemini-2.5-flash-preview-tts"
OVOZLAR = [("Speaker1", "Kore"), ("Speaker2", "Puck")]

DIALOGLAR = {
    "listening-01": """Speaker1: Good afternoon. I'd like to know more about borrowing books from this library. As a new student, how many books am I allowed to borrow at one time?
Speaker2: You can borrow up to eight books at once, and the loan period is three weeks for most items, though DVDs and equipment are limited to one week.
Speaker1: And what happens if I return something late?
Speaker2: There's a fine of twenty cents per day for regular books, but reference materials and rare books cannot be taken out of the building at all.
Speaker1: I see. Also, is there a photocopying service here?
Speaker2: Yes, on the ground floor near the main entrance. It costs ten cents per page in black and white, and thirty cents for color copies.
Speaker1: That's helpful, thank you. One last question, do I need to bring my student card every time?
Speaker2: Yes, you must show your student card each time you borrow or return items, otherwise we cannot process your request.""",
    "listening-02": """Speaker1: Hi, I'm calling about the gym membership options you offer. Could you explain the different plans?
Speaker2: Of course. We have three plans: the Basic plan at twenty-five dollars a month gives you access to the gym floor only. The Standard plan, at forty dollars, includes the gym floor plus all group fitness classes. The Premium plan is sixty-five dollars a month and includes everything in Standard plus unlimited access to the swimming pool and sauna.
Speaker1: That's useful. Is there a joining fee?
Speaker2: Yes, there's a one-time joining fee of thirty dollars for all plans, but this is often waived during promotional periods.
Speaker1: And can I freeze my membership if I travel?
Speaker2: Absolutely. You can freeze your membership for up to two months per year at no extra cost, as long as you notify us at least a week in advance.
Speaker1: Great, and what are your opening hours?
Speaker2: We're open from six in the morning until eleven at night on weekdays, and from eight until eight on weekends.""",
    "listening-05": """Speaker1: Good morning, Lakeside Hotel, how can I help you?
Speaker2: Hi, I'd like to book a room for next weekend.
Speaker1: Certainly, can I take your name please?
Speaker2: Yes, it's Michael Turner. That's T-U-R-N-E-R.
Speaker1: Thank you, Mr. Turner. And what dates would you like to stay?
Speaker2: We'd like to check in on Friday the fourteenth and check out on Sunday the sixteenth, so that's two nights.
Speaker1: Perfect, and how many guests will be staying?
Speaker2: There will be two adults and one child.
Speaker1: Great, would you prefer a room with a city view or a lake view?
Speaker2: A lake view, please, if that's available.
Speaker1: It is. That will be a Deluxe Double Room with a lake view for one hundred and eighty dollars per night. Could I get a contact number in case we need to reach you?
Speaker2: Sure, it's zero seven seven, four one two, six six zero five.
Speaker1: Thank you very much, Mr. Turner. We look forward to welcoming you.""",
    "listening-06": """Speaker1: Hello, I'd like to register for one of your evening courses.
Speaker2: Of course, which course are you interested in?
Speaker1: I saw the Introduction to Photography course listed online.
Speaker2: Great choice. That course runs every Tuesday evening from six to eight, starting on the third of March and running for eight weeks.
Speaker1: And how much does it cost?
Speaker2: The full course fee is one hundred and twenty dollars, but there's a ten percent discount if you pay before the end of this month.
Speaker1: That sounds good. What do I need to bring to the first class?
Speaker2: Just a notebook and, if you have one, your own camera, though we do have a few cameras available to borrow if needed. Can I get your name and email address to complete the registration?
Speaker1: Yes, it's Elena Petrova, and my email is elena dot petrova at mailbox dot com.
Speaker2: Perfect, you're now registered for the course starting March third.""",
    "listening-07": """Speaker1: So, can you tell me a bit about your typical weekday morning?
Speaker2: Sure. I usually wake up at six thirty, and the first thing I do is go for a short run around the park near my house, about twenty minutes.
Speaker1: That's a great way to start the day. What do you have for breakfast?
Speaker2: Just something simple, usually oatmeal with fruit and a cup of green tea.
Speaker1: And how do you get to work?
Speaker2: I take the bus, it's about a thirty-five minute journey, and I usually read on the way.
Speaker1: Do you have a favorite part of the day?
Speaker2: Definitely the evening, when I get to relax and read for pleasure, usually a novel, before going to bed around ten thirty.""",
    "listening-08": """Speaker1: I heard you're planning a trip this summer. Where are you thinking of going?
Speaker2: Yes, my partner and I are planning to visit Portugal, specifically Lisbon and Porto.
Speaker1: How long will you be there?
Speaker2: We're planning a ten-day trip, split evenly between the two cities.
Speaker1: How are you getting there?
Speaker2: We found a direct flight, so it should take about four hours from here.
Speaker1: Are you staying in hotels?
Speaker2: Actually, we booked an apartment through a rental website, it's usually cheaper and gives us more space than a hotel room.
Speaker1: Sounds like a great trip. Any specific places you want to visit?
Speaker2: Yes, we really want to see the old bookshop in Porto and take a boat tour along the river.""",
    "listening-09": """Speaker1: Good morning, welcome to Skyline Airlines, how can I help you today?
Speaker2: Hi, I'd like to check in for my flight to Manchester.
Speaker1: Certainly, could I see your passport and booking reference please?
Speaker2: Yes, here you go.
Speaker1: Thank you. I can see you're on flight SK 204, departing at two forty-five this afternoon. Would you like a window or an aisle seat?
Speaker2: An aisle seat would be great, if possible.
Speaker1: No problem, I've given you seat fourteen C. How many bags will you be checking in today?
Speaker2: Just the one suitcase.
Speaker1: That's fine, the weight limit is twenty-three kilograms, and yours is well within that. Your boarding gate is gate sixteen, and boarding begins one hour before departure. Please make sure you arrive at the gate at least thirty minutes before boarding starts. Thank you, and have a pleasant flight.""",
    "listening-11": """Speaker1: Good evening, The Olive Tree restaurant, how can I help you?
Speaker2: Hi, I'd like to make a reservation for Saturday evening.
Speaker1: Of course, what time would you like to come?
Speaker2: Around seven thirty, if that's possible.
Speaker1: Let me check, yes, seven thirty works well. And how many people will be in your party?
Speaker2: There will be four of us.
Speaker1: Great, could I take a name for the booking?
Speaker2: Yes, it's under the name Robertson.
Speaker1: And do you have any dietary requirements we should know about?
Speaker2: Yes, one of our guests is vegetarian.
Speaker1: Noted, we'll make sure to have some vegetarian options ready. Finally, could I get a contact number?
Speaker2: Sure, it's zero nine one, five five zero, two two three three.
Speaker1: Perfect, we look forward to seeing you at seven thirty on Saturday.""",
    "listening-12": """Speaker1: Do you have any pets?
Speaker2: Yes, I have a small dog called Max, he's a golden retriever.
Speaker1: How long have you had him?
Speaker2: We got him about two years ago, when he was just a puppy.
Speaker1: What's he like?
Speaker2: He's very friendly and energetic, he loves playing in the garden and going for long walks.
Speaker1: Where do you usually take him for walks?
Speaker2: There's a big park near our house, we go there most evenings after dinner.""",
}


class Command(BaseCommand):
    help = "Dialog bo'lishi kerak bo'lgan Listening audiolarini Gemini TTS bilan qayta yozadi"

    def add_arguments(self, parser):
        parser.add_argument("--model", default=MODEL, help="gemini-2.5-flash-preview-tts yoki gemini-3.1-flash-tts-preview")

    def handle(self, *args, **options):
        model = options["model"]
        yaratildi = 0
        for item_id, matn in DIALOGLAR.items():
            wav_yol = AUDIO_DIR / f"{item_id}.wav"
            if wav_yol.exists():
                self.stdout.write(f"{item_id}: allaqachon .wav bor, o'tkazib yuborildi")
                continue
            try:
                wav_bytes = audio_yarat(matn, model, speakerlar=OVOZLAR)
            except RateLimitTugadi as e:
                self.stdout.write(self.style.WARNING(f"Bepul limit tugadi, to'xtatildi: {e}"))
                break
            wav_yol.write_bytes(wav_bytes)
            eski_mp3 = AUDIO_DIR / f"{item_id}.mp3"
            if eski_mp3.exists():
                eski_mp3.unlink()
            yaratildi += 1
            self.stdout.write(self.style.SUCCESS(f"{item_id}: yaratildi ({len(wav_bytes)} bayt)"))

        self.stdout.write(self.style.SUCCESS(f"Jami yaratildi: {yaratildi}/{len(DIALOGLAR)}"))
