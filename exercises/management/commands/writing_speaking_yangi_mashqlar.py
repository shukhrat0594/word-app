"""20 ta yangi Writing/Speaking mashqi (Task1 x5, Task2 x5, Part1 x5,
Part2/3 x5) — Shukhrat bilan kelishilgan (2026-07-20). Audio/TTS kerak
emas — bular faqat o'qish uchun namuna mavzular banki (Mashq.namuna_javob).

Idempotent — nomi bo'yicha mavjud bo'lsa qayta yaratilmaydi, hech qanday
tashqi API chaqirilmaydi (prod_boshlangich'da har deploy'da xavfsiz)."""

from django.core.management.base import BaseCommand

from accounts.models import Markaz
from exercises.models import Bolim, Mashq, Tur

# ---- Writing Task 1 (5) — ma'lumot jadval sifatida matn ichida (SVG grafiksiz) ----
TASK1 = [
    {
        "kategoriya": "internet-usage",
        "matn": """The line graph below shows the percentage of the population using the internet in four countries between 2000 and 2020. Summarise the information by selecting and reporting the main features, and make comparisons where relevant.

[Ma'lumot] Internetdan foydalanuvchilar ulushi (% aholi):
Yil | Sweden | Brazil | Kenya | Japan
2000 | 45% | 3% | 0% | 30%
2010 | 90% | 40% | 8% | 78%
2020 | 96% | 74% | 41% | 93%

[Struktura]
1-paragraf (Kirish): Grafik nimani tasvirlashini paraphrase qil.
2-paragraf (Overview): Eng katta o'sish qaysi mamlakatda bo'lganini umumlashtir.
3-paragraf: Ikki mamlakatni (Sweden, Japan) taqqoslab tasvirla.
4-paragraf: Qolgan ikkitasini (Brazil, Kenya) tasvirlab yakunla.

[Foydali iboralar]
rose steadily, surged from X% to Y%, nearly universal coverage, lagged behind, a dramatic increase, starting from a much lower base, remained considerably lower than, achieved near-universal access""",
        "namuna_javob": "The line graph illustrates the proportion of people with internet access in Sweden, Brazil, Kenya and Japan from 2000 to 2020.\n\nOverall, internet usage rose in all four countries over the period, with Sweden and Japan reaching near-universal coverage by 2020, while Brazil and Kenya, despite significant growth, remained considerably lower.\n\nIn 2000, Sweden had the highest rate at 45%, followed by Japan at 30%, whereas Brazil and Kenya lagged far behind with just 3% and 0% respectively. By 2020, Sweden and Japan had both surged to over 90%, achieving almost universal internet access among their populations.\n\nBrazil and Kenya also saw substantial growth, though starting from a much lower base. Brazil's figure rose from 3% to 74%, while Kenya, despite a dramatic increase to 41%, still trailed the other three nations by a wide margin.\n\nIn conclusion, while all four countries experienced considerable growth in internet usage, a clear gap remained between the more developed and developing nations by the end of the period.",
        "tur": Tur.TASK1,
    },
    {
        "kategoriya": "transport-usage",
        "matn": """The bar chart below shows the main method of transport used by commuters in three cities in 2022. Summarise the information by selecting and reporting the main features, and make comparisons where relevant.

[Ma'lumot] Asosiy transport turi (% ishchi/talabalar):
Shahar | Car | Bus | Bicycle | Walking
Amsterdam | 20% | 15% | 50% | 15%
Los Angeles | 75% | 15% | 3% | 7%
Tokyo | 12% | 48% | 10% | 30%

[Struktura]
1-paragraf (Kirish): Diagramma nimani taqqoslashini paraphrase qil.
2-paragraf (Overview): Har shahar uchun eng ustuvor transport turini umumlashtir.
3-paragraf: Amsterdam va Tokyo'ni taqqoslab tasvirla.
4-paragraf: Los Angeles'ni tasvirlab, umumiy farqni ta'kidlab yakunla.

[Foydali iboralar]
the dominant means of transport, accounted for the majority of, in stark contrast, relatively evenly distributed, relied heavily on, a marginal proportion, favoured by commuters, considerably higher than""",
        "namuna_javob": "The bar chart compares the main commuting methods used by residents of Amsterdam, Los Angeles and Tokyo in 2022.\n\nOverall, cycling was the dominant means of transport in Amsterdam, public buses were most favoured in Tokyo, while the car was overwhelmingly the preferred option in Los Angeles.\n\nIn Amsterdam, half of all commuters travelled by bicycle, considerably higher than the 15% who used cars or buses, with walking accounting for the remaining 15%. Tokyo presented a different pattern, with buses used by almost half of commuters, followed by walking at 30%, while cars and bicycles made up a relatively small proportion of journeys.\n\nLos Angeles stood in stark contrast to the other two cities, with three-quarters of commuters relying on cars, and all other methods accounting for a marginal proportion of trips, with cycling used by only 3% of the population.\n\nIn conclusion, while Amsterdam and Tokyo showed a more balanced or public-transport-oriented approach to commuting, Los Angeles relied heavily on private car usage.",
        "tur": Tur.TASK1,
    },
    {
        "kategoriya": "waste-composition",
        "matn": """The pie chart below shows the composition of household waste produced in a city in 2021. Summarise the information by selecting and reporting the main features, and make comparisons where relevant.

[Ma'lumot] Uy xo'jaligi chiqindilari tarkibi (2021):
Organic waste: 38%
Paper and cardboard: 22%
Plastic: 18%
Glass: 10%
Metal: 7%
Other: 5%

[Struktura]
1-paragraf (Kirish): Diagramma nimani tasvirlashini paraphrase qil.
2-paragraf (Overview): Eng katta va eng kichik ulushni umumlashtir.
3-paragraf: Eng katta uchta toifani (organic, paper, plastic) tasvirla.
4-paragraf: Qolganlarini (glass, metal, other) tasvirlab yakunla.

[Foydali iboralar]
made up the largest share of, accounted for just over/under X%, a relatively minor proportion, combined, these two categories, the smallest contributor, represented roughly a fifth of""",
        "namuna_javob": "The pie chart illustrates the different types of waste that made up household rubbish in a city during 2021.\n\nOverall, organic waste made up the largest share of household rubbish, while metal and other materials represented only a small fraction of the total.\n\nOrganic waste accounted for just over a third of all household waste, at 38%, making it by far the most significant category. Paper and cardboard represented roughly a fifth of the total, at 22%, while plastic made up a further 18%. Combined, these three categories accounted for nearly four-fifths of all household waste produced.\n\nThe remaining categories were considerably smaller. Glass accounted for a tenth of the total, at 10%, while metal made up just 7%. The smallest contributor was the miscellaneous 'other' category, at only 5% of total household waste.\n\nIn conclusion, organic material was clearly the most prominent component of household waste, while metal and other materials played only a minor role.",
        "tur": Tur.TASK1,
    },
    {
        "kategoriya": "exercise-hours",
        "matn": """The table below shows the average number of hours per week that people in three age groups spent exercising in 2020. Summarise the information by selecting and reporting the main features, and make comparisons where relevant.

[Ma'lumot] Haftalik mashq soatlari (2020):
Yosh guruhi | Yugurish | Sport zali | Jamoaviy sport
18-30 | 2.5 | 3.0 | 2.0
31-50 | 1.5 | 2.0 | 1.0
51+ | 1.0 | 0.5 | 0.5

[Struktura]
1-paragraf (Kirish): Jadval nimani taqqoslashini paraphrase qil.
2-paragraf (Overview): Yosh guruhi qanchalik faol ekanini umumlashtir.
3-paragraf: 18-30 va 31-50 guruhlarini taqqoslab tasvirla.
4-paragraf: 51+ guruhini tasvirlab, umumiy tendensiyani ta'kidlab yakunla.

[Foydali iboralar]
considerably more time than, a clear downward trend with age, spent an average of X hours on, twice as much time as, the least active group, notably lower figures across all categories""",
        "namuna_javob": "The table presents data on the average weekly hours spent on running, gym workouts and team sports by three age groups in 2020.\n\nOverall, there is a clear downward trend in exercise time as age increases, with the youngest group being the most active across all three activities.\n\nAdults aged 18 to 30 spent the most time exercising overall, dedicating three hours per week to gym workouts and two and a half hours to running, considerably more than the 31-50 age group, who managed two hours and one and a half hours respectively in these activities. Team sports followed a similar pattern, with the youngest group spending twice as much time, at two hours, compared with one hour for the middle age group.\n\nThe 51 and over age group was the least active overall, spending just one hour running and only half an hour each on gym workouts and team sports, notably lower figures across all categories compared with the younger groups.\n\nIn conclusion, physical activity levels declined steadily with age, with the youngest adults exercising considerably more than older age groups across all three activities.",
        "tur": Tur.TASK1,
    },
    {
        "kategoriya": "coffee-production",
        "matn": """The diagram below shows the process of coffee production, from harvesting to packaging. Summarise the information by selecting and reporting the main features, and make comparisons where relevant.

[Jarayon bosqichlari]
1. Coffee cherries are harvested by hand from coffee plants.
2. The cherries are sorted and the outer skin is removed.
3. The beans are washed and then dried in the sun for several days.
4. The dried beans are roasted at high temperatures.
5. The roasted beans are ground into powder.
6. The ground coffee is packaged and shipped to stores.

[Struktura]
1-paragraf (Kirish): Jarayon nima haqida ekanini paraphrase qil, nechta bosqich borligini ayt.
2-paragraf (Overview): Jarayon qayerdan boshlanib qayerda tugashini umumlashtir.
3-paragraf: Birinchi uchta bosqichni tartib bildiruvchi so'zlar bilan tasvirla.
4-paragraf: Qolgan uchta bosqichni tasvirlab, yakuniy natija bilan yakunla.

[Foydali iboralar]
the process begins with, following this, once the beans have been, subsequently, the penultimate stage involves, the process is completed when, prior to being shipped""",
        "namuna_javob": "The diagram illustrates the six stages involved in producing coffee, from the initial harvesting of cherries to the final packaging of ground coffee.\n\nOverall, the process is linear, beginning with the manual harvesting of coffee cherries on plantations and ending with packaged coffee ready for distribution to shops.\n\nThe process begins with workers harvesting ripe coffee cherries by hand from the coffee plants. Following this, the cherries are sorted, and their outer skins are removed to expose the beans inside. Subsequently, the beans undergo a washing stage before being spread out to dry in the sun for several days.\n\nOnce the beans have been thoroughly dried, they are roasted at high temperatures, a process which develops their characteristic flavour and aroma. The penultimate stage involves grinding the roasted beans into a fine powder. Finally, the ground coffee is packaged and shipped to stores, completing the production process.\n\nIn summary, coffee production involves a systematic sequence of harvesting, processing, roasting and packaging before it reaches consumers.",
        "tur": Tur.TASK1,
    },
]

# ---- Writing Task 2 (5 essays) ----
TASK2 = [
    {
        "kategoriya": "technology-isolation",
        "matn": """Some people believe that modern technology, such as smartphones and social media, has made people more isolated from each other. To what extent do you agree or disagree?

[Struktura]
1-paragraf (Kirish): Mavzuni paraphrase qil va o'z pozitsiyangni bildir.
2-paragraf (Asosiy fikr 1): Texnologiya izolyatsiyaga olib kelishini misol bilan tushuntir.
3-paragraf (Asosiy fikr 2): Qarama-qarshi fikrni tan olib, texnologiya aloqani osonlashtirishini ham ko'rsat.
4-paragraf (Xulosa): Ikkala tomonni umumlashtirib, o'z pozitsiyangni tasdiqla.

[Foydali iboralar]
it is often argued that, face-to-face interaction, a double-edged sword, on the other hand, this argument overlooks the fact that, staying connected across long distances, at the expense of genuine relationships, in light of the above""",
        "namuna_javob": "It is often argued that smartphones and social media have led to greater social isolation, as people increasingly interact through screens rather than face-to-face. While I acknowledge some validity in this view, I believe technology is best understood as a double-edged sword rather than a purely isolating force.\n\nOn one hand, excessive use of technology can genuinely weaken personal relationships. It is common to see groups of friends sitting together in a cafe, each absorbed in their own phone rather than conversing with one another. This constant digital distraction can come at the expense of the deeper, more meaningful connections that face-to-face interaction tends to foster, potentially leaving people feeling lonelier despite being constantly 'connected' online.\n\nOn the other hand, this argument overlooks the fact that technology also enables people to maintain relationships that would otherwise be impossible to sustain. Video calls and messaging apps allow families separated by long distances, such as migrant workers or international students, to stay in close contact with loved ones in ways that were unimaginable a generation ago. For many, technology has therefore strengthened rather than weakened important relationships.\n\nIn light of the above, I believe technology itself is neutral; its effect on social isolation depends largely on how it is used. While overreliance on devices in social settings can genuinely harm relationships, thoughtful use of the same technology can just as easily bring people closer together.",
        "tur": Tur.TASK2,
    },
    {
        "kategoriya": "university-education-focus",
        "matn": """Some people think that universities should focus on providing students with job-related skills, while others believe universities should give students a broader general education. Discuss both views and give your own opinion.

[Struktura]
1-paragraf (Kirish): Mavzuni paraphrase qil, ikkala fikr muhokama qilinishini ayt.
2-paragraf (1-tomon): Kasbiy ko'nikmalarga e'tibor qaratish tarafdorlarining argumentlarini tushuntir.
3-paragraf (2-tomon): Keng ta'lim tarafdorlarining argumentlarini tushuntir.
4-paragraf (Xulosa): Ikkala fikrni umumlashtirib, o'z pozitsiyangni bildir.

[Foydali iboralar]
proponents of this view argue that, directly applicable to the workplace, equips students with, a well-rounded education, critical thinking and adaptability, a more balanced approach would be, in an ever-changing job market""",
        "namuna_javob": "There are differing opinions regarding whether universities should prioritise practical, job-related training or a broader academic education. This essay will discuss both perspectives before presenting my own view.\n\nProponents of a job-focused curriculum argue that university education should be directly applicable to the workplace. In their view, students who graduate with specific technical skills, such as coding, accounting or engineering techniques, are more employable and can contribute to the economy immediately upon graduation, rather than requiring extensive on-the-job training.\n\nOn the other hand, advocates of a broader general education contend that universities should equip students with critical thinking, communication and adaptability rather than narrow technical skills alone. They argue that in an ever-changing job market, where specific technical skills can quickly become outdated, a well-rounded education better prepares graduates to adapt to new roles and challenges throughout their careers.\n\nIn my view, a more balanced approach would serve students best. While practical skills are undoubtedly valuable for immediate employability, a purely vocational education risks leaving graduates unable to adapt when their industry changes. Universities should therefore aim to combine relevant practical training with the broader critical thinking skills that support long-term career success.",
        "tur": Tur.TASK2,
    },
    {
        "kategoriya": "traffic-congestion",
        "matn": """Traffic congestion is becoming a serious problem in many major cities. What do you think are the causes of this problem, and what solutions can you suggest?

[Struktura]
1-paragraf (Kirish): Muammoni paraphrase qil.
2-paragraf (Sabablar): Tirbandlikning asosiy sabablarini misol bilan tushuntir.
3-paragraf (Yechimlar): Amaliy yechimlarni taklif qil.
4-paragraf (Xulosa): Asosiy fikrlarni umumlashtirib yakunla.

[Foydali iboralar]
a growing number of, over-reliance on private vehicles, inadequate public transport infrastructure, one effective solution would be, incentivise the use of, alleviate the pressure on road networks, in the long run""",
        "namuna_javob": "Traffic congestion has become an increasingly pressing issue in cities across the world, causing significant delays, pollution and frustration for commuters. This essay will examine the main causes of this problem and propose some possible solutions.\n\nOne of the primary causes of traffic congestion is the growing number of private vehicles on the road, driven by rising incomes and the convenience that cars offer compared with public transport. In many cities, inadequate public transport infrastructure, such as unreliable bus services or limited metro coverage, forces residents to rely on their own vehicles, further worsening congestion during peak hours. Additionally, poor urban planning, including insufficient road capacity for growing populations, exacerbates the problem.\n\nTo address this issue, one effective solution would be for governments to invest heavily in public transport infrastructure, making it a genuinely convenient and affordable alternative to private cars. Cities could also incentivise the use of buses and trains through reduced fares or dedicated bus lanes, while introducing congestion charges for vehicles entering busy city centres during peak times. Encouraging remote working arrangements could also help alleviate the pressure on road networks during rush hour.\n\nIn conclusion, while traffic congestion stems from a combination of increased car ownership and insufficient public transport, a combination of infrastructure investment and demand-management policies could, in the long run, significantly reduce this growing urban problem.",
        "tur": Tur.TASK2,
    },
    {
        "kategoriya": "remote-work",
        "matn": """In recent years, an increasing number of people have started working from home rather than in an office. Discuss the advantages and disadvantages of this trend.

[Struktura]
1-paragraf (Kirish): Mavzuni paraphrase qil.
2-paragraf (Afzalliklar): Uydan ishlashning asosiy afzalliklarini tushuntir.
3-paragraf (Kamchiliklar): Asosiy kamchiliklarni tushuntir.
4-paragraf (Xulosa): Umumiy fikrni bildirib yakunla.

[Foydali iboralar]
a growing trend towards, greater flexibility over, eliminates the need for daily commuting, however, this arrangement also presents challenges, a lack of face-to-face interaction, blurring the boundary between work and home life, on balance""",
        "namuna_javob": "There has been a growing trend towards remote working in recent years, a shift accelerated by advances in technology and changing attitudes towards traditional office environments. This essay will consider both the benefits and drawbacks of this development.\n\nWorking from home offers several clear advantages. Employees enjoy greater flexibility over their schedules, allowing them to balance work with personal responsibilities such as childcare more easily. It also eliminates the need for daily commuting, saving both time and money while reducing the environmental impact associated with travel. Furthermore, many workers report higher productivity when working in a quiet home environment, free from the distractions of a busy office.\n\nHowever, this arrangement also presents significant challenges. A lack of face-to-face interaction with colleagues can lead to feelings of isolation and may hinder collaboration and the spontaneous exchange of ideas that often occurs in an office setting. Additionally, working from home risks blurring the boundary between work and home life, making it difficult for some employees to switch off and maintain a healthy work-life balance. Career progression can also suffer, as remote workers may become less visible to management compared with their office-based colleagues.\n\nOn balance, while remote working offers genuine benefits in terms of flexibility and reduced commuting, organisations must actively address the risks of isolation and blurred boundaries to ensure this trend benefits both employees and employers in the long term.",
        "tur": Tur.TASK2,
    },
    {
        "kategoriya": "foreign-language-age",
        "matn": """Some people believe that children should start learning a foreign language in primary school rather than waiting until secondary school. To what extent do you agree or disagree?

[Struktura]
1-paragraf (Kirish): Mavzuni paraphrase qil va pozitsiyangni bildir.
2-paragraf (Asosiy fikr 1): Erta boshlashning foydalarini misol bilan tushuntir.
3-paragraf (Asosiy fikr 2): Qarama-qarshi tashvishlarni tan olib, ularga javob ber.
4-paragraf (Xulosa): Pozitsiyangni yana bir bor tasdiqla.

[Foydali iboralar]
it is widely believed that, a critical period for language acquisition, absorb new sounds and grammar more naturally, some may argue that, overburdening young children, with appropriate teaching methods, far outweighs the potential drawbacks""",
        "namuna_javob": "It is widely believed that children should begin learning a foreign language in primary school rather than secondary school. I strongly agree with this view, as I believe early exposure to language learning offers substantial long-term benefits.\n\nOne of the main reasons for this is that young children are in a critical period for language acquisition, during which they can absorb new sounds, vocabulary and grammar more naturally than older learners. For example, children who begin learning a language before the age of ten often develop more authentic pronunciation and a more intuitive grasp of grammar than those who start as teenagers, since younger brains are particularly adept at picking up new linguistic patterns through exposure and repetition.\n\nSome may argue that introducing a foreign language too early risks overburdening young children who are still mastering their first language, or that it may cause confusion. However, this argument overlooks the fact that with appropriate teaching methods, such as songs, games and interactive activities, young children can learn a second language enjoyably and effectively, without any negative impact on their native language development. In fact, research suggests that bilingual children often develop stronger overall cognitive and problem-solving skills.\n\nIn conclusion, although there are some concerns about introducing foreign languages too early, I believe the long-term linguistic and cognitive benefits of early language learning far outweigh the potential drawbacks, and primary school is the ideal time to begin.",
        "tur": Tur.TASK2,
    },
]

# ---- Speaking Part 1 (5 topics x 4 savol) ----
PART1 = [
    {
        "kategoriya": "food-and-cooking",
        "savollar": [
            ("Do you enjoy cooking?", "I do, actually — I find it quite relaxing after a long day, especially when I'm trying out a new recipe."),
            ("What kind of food do you like to eat?", "I have quite a varied diet, but if I had to choose, I'd say I have a real soft spot for spicy dishes, especially anything with plenty of chilli."),
            ("Did you learn to cook from anyone?", "Yes, mostly from my mother — she taught me the basics when I was a teenager, and I've been building on that ever since."),
            ("Do you prefer eating at home or in restaurants?", "I'd say it depends on the occasion, but generally I prefer eating at home since it's healthier and much easier on the wallet."),
        ],
        "iboralar": ["a soft spot for", "on the wallet", "from scratch", "an acquired taste", "to whip up a meal", "comfort food", "a well-balanced diet", "to experiment with recipes"],
    },
    {
        "kategoriya": "weather",
        "savollar": [
            ("What's the weather like in your country?", "It varies quite a bit depending on the season, but generally we get hot, dry summers and fairly cold, wet winters."),
            ("What's your favourite type of weather?", "I'd have to say mild, sunny days in spring — not too hot, not too cold, just perfect for being outdoors."),
            ("Does the weather affect your mood?", "Definitely — I tend to feel much more energetic and positive on bright, sunny days compared to grey, overcast ones."),
            ("How do you usually check the weather forecast?", "I mostly just check an app on my phone in the morning before deciding what to wear."),
        ],
        "iboralar": ["mild weather", "overcast skies", "a scorching hot day", "bone-chillingly cold", "unpredictable weather", "to brighten someone's mood", "a weather app", "seasonal changes"],
    },
    {
        "kategoriya": "music",
        "savollar": [
            ("What kind of music do you like?", "I mostly listen to pop and acoustic music, though I do enjoy the occasional classical piece when I need to concentrate."),
            ("Do you play any musical instruments?", "I used to play the guitar when I was younger, but I haven't picked it up in years, unfortunately."),
            ("When do you usually listen to music?", "Mostly while commuting or doing chores around the house — it helps the time pass more quickly."),
            ("Has your taste in music changed over the years?", "Yes, quite a lot actually — I used to only listen to whatever was popular, but now I have a much broader taste."),
        ],
        "iboralar": ["a broad taste in music", "to pick up an instrument", "background music", "a catchy tune", "to unwind", "live performance", "a die-hard fan", "genre-bending"],
    },
    {
        "kategoriya": "shopping",
        "savollar": [
            ("Do you enjoy shopping?", "It really depends on what I'm shopping for — grocery shopping feels like a chore, but shopping for clothes can be quite enjoyable."),
            ("Do you prefer shopping online or in physical stores?", "I'd say online, mainly for the convenience — I can compare prices easily and avoid crowded shops."),
            ("Who do you usually go shopping with?", "Usually by myself, to be honest, since I can move at my own pace and don't have to compromise on what to buy."),
            ("What was the last thing you bought?", "Just yesterday I bought a new pair of running shoes, since my old ones were completely worn out."),
        ],
        "iboralar": ["a bargain hunter", "to browse", "window shopping", "to splash out on something", "a shopping spree", "worn out", "hard on the wallet", "convenience of online shopping"],
    },
    {
        "kategoriya": "public-transport",
        "savollar": [
            ("How do you usually get to work or school?", "I usually take the bus, since it's the most convenient option from where I live."),
            ("Is public transport popular in your country?", "It's fairly popular in big cities, though in smaller towns most people still rely on their own cars."),
            ("What do you think could be improved about public transport in your city?", "I think the frequency of buses during off-peak hours could definitely be improved, since waiting times can be quite long."),
            ("Do you prefer travelling by bus, train or car?", "I'd say train, if it's available — it's usually faster and I can relax or read during the journey."),
        ],
        "iboralar": ["a convenient option", "to rely on", "off-peak hours", "rush hour", "to be stuck in traffic", "an efficient network", "overcrowded", "a reliable service"],
    },
]

# ---- Speaking Part 2/3 (5) ----
PART2_3 = [
    {
        "kategoriya": "clothing-item",
        "cue_card": "Describe a piece of clothing you like to wear.\nYou should say:\n- what it is\n- where you got it\n- when you wear it\nand explain why you like wearing it.",
        "struktura": [
            "Kirish: kiyim nima ekanini umumiy tasvirlang",
            "Asosiy qism 1: uni qayerdan va qachon olganingiz",
            "Asosiy qism 2: uni qachon kiyishingiz",
            "Asosiy qism 3: nega yoqtirishingiz sabablari",
        ],
        "iboralar": ["a wardrobe staple", "goes with everything", "true to size", "hard-wearing", "a hand-me-down", "off the peg", "a signature piece", "second-hand"],
        "namuna_javob": "I'd like to talk about a denim jacket that I bought about two years ago from a small vintage shop in my city. I remember trying it on almost as a joke, but it fit so well that I ended up buying it on the spot.\n\nI tend to wear it mostly in autumn and spring, when the weather is too cool for just a t-shirt but not cold enough for a heavy coat. It's become something of a wardrobe staple for me, since it goes with almost everything, whether I'm dressing casually for a walk with friends or trying to look slightly smarter for a casual dinner out.\n\nWhat I like most about it is that it's hard-wearing and only seems to look better with age, unlike a lot of cheaper clothes that fall apart after a few washes. It also has a slightly worn, vintage look that I really love, and since it's second-hand, I like knowing that it's a bit more sustainable than buying something brand new.",
        "part3_savollar": [
            ("Do you think fashion is important to young people nowadays?", "I think it is, particularly because of social media — young people are constantly exposed to trends and often feel pressure to keep up with what's popular."),
            ("How has clothing changed in your country over the past few decades?", "Clothing has become a lot more casual and international, to be honest — traditional styles are still worn on special occasions, but everyday clothing now looks quite similar to what you'd see anywhere else in the world."),
            ("Do you think people should buy fewer clothes for environmental reasons?", "I do think so — fast fashion has a huge environmental impact, so buying fewer, higher-quality items that last longer would make a real difference."),
            ("Is it important to wear formal clothes at work?", "I think it depends on the industry — in more traditional fields like law or banking it's still expected, but many workplaces have become far more relaxed about dress codes."),
        ],
    },
    {
        "kategoriya": "helped-someone",
        "cue_card": "Describe a time you helped someone.\nYou should say:\n- who you helped\n- what the situation was\n- how you helped them\nand explain how you felt afterwards.",
        "struktura": [
            "Kirish: kimga yordam berganingizni ayting",
            "Asosiy qism 1: vaziyat qanday bo'lgani",
            "Asosiy qism 2: qanday yordam berganingiz",
            "Asosiy qism 3: keyin qanday his qilganingiz",
        ],
        "iboralar": ["to lend a hand", "in a difficult spot", "went out of my way", "a weight off their shoulders", "a rewarding experience", "to step in", "out of the goodness of my heart", "made a real difference"],
        "namuna_javob": "I'd like to talk about a time I helped an elderly neighbour of mine, Mrs. Carter, who lives just down the street from me. One winter, I noticed that she hadn't cleared the heavy snow from her driveway, and I later found out she'd hurt her back and simply wasn't able to do it herself.\n\nWithout really thinking twice, I went out of my way to clear the snow from both her driveway and the pathway leading to her front door, which took me about an hour. I also offered to pick up some groceries for her that afternoon, since I was heading to the shop anyway and knew she couldn't easily get out in that weather.\n\nAfterwards, I honestly felt really good about it — it was a rewarding experience to know that I'd made a real difference to someone who was clearly struggling, and it was clear from her reaction that it was a weight off her shoulders. It reminded me how such a small gesture can genuinely mean a lot to someone else.",
        "part3_savollar": [
            ("Why do you think some people are more willing to help others than others?", "I think it often comes down to upbringing — people raised in communities where helping neighbours is the norm tend to carry that habit into adulthood."),
            ("Should schools teach children to help others?", "Definitely — I think values like kindness and community spirit are just as important as academic subjects, and schools are well placed to instil them early on."),
            ("Do you think technology has made people less willing to help each other in person?", "In some ways, yes — people are so absorbed in their phones nowadays that they sometimes don't even notice when someone nearby needs help."),
            ("Is it better to help strangers or people you know?", "I don't think it should be either-or, but I'd say helping strangers can sometimes have an even bigger impact, since they often have no one else to turn to."),
        ],
    },
    {
        "kategoriya": "important-decision",
        "cue_card": "Describe an important decision you made.\nYou should say:\n- what the decision was\n- when you made it\n- what factors you considered\nand explain how it affected your life.",
        "struktura": [
            "Kirish: qaror nima haqida bo'lganini ayting",
            "Asosiy qism 1: qachon qaror qabul qilganingiz",
            "Asosiy qism 2: qanday omillarni hisobga olganingiz",
            "Asosiy qism 3: bu hayotingizga qanday ta'sir qilgani",
        ],
        "iboralar": ["a turning point", "weighed up the pros and cons", "took the plunge", "a leap of faith", "in hindsight", "a life-changing decision", "mixed feelings", "paid off in the end"],
        "namuna_javob": "One important decision I made was to move to a different city for university rather than staying close to home, which I decided on about five years ago, right after finishing school.\n\nBefore making the decision, I weighed up the pros and cons quite carefully. On one hand, staying close to home meant I could keep living with my family and save money, but on the other hand, the university in the other city offered a much stronger program in the subject I wanted to study. In the end, I took the plunge and decided that the quality of education was more important than convenience.\n\nLooking back, this decision genuinely turned out to be a turning point in my life. Moving away forced me to become far more independent and taught me practical skills like managing my own finances and cooking for myself, things I probably wouldn't have learned as quickly if I'd stayed at home. Although I had mixed feelings about leaving my family at the time, in hindsight, I believe it paid off in the end, both academically and personally.",
        "part3_savollar": [
            ("Do you think young people today find it harder to make important decisions than in the past?", "I think in some ways it's harder, simply because there are so many more options available now, which can make decision-making feel overwhelming."),
            ("Should parents be involved in their children's major life decisions?", "I think parents can offer useful advice based on experience, but ultimately the decision should rest with the individual, especially once they're an adult."),
            ("What kind of decisions do people often regret?", "I think people often regret decisions made purely out of fear or pressure from others, rather than ones based on their own genuine judgement."),
            ("Is it better to make decisions quickly or take a long time to decide?", "I think it depends on the significance of the decision — small everyday choices can be made quickly, but life-changing decisions deserve careful, unhurried consideration."),
        ],
    },
    {
        "kategoriya": "place-to-visit",
        "cue_card": "Describe a place you would like to visit in the future.\nYou should say:\n- where it is\n- how you learned about it\n- what you would do there\nand explain why you want to visit this place.",
        "struktura": [
            "Kirish: joy qayerda ekanini ayting",
            "Asosiy qism 1: bu joy haqida qanday bilganingiz",
            "Asosiy qism 2: u yerda nima qilmoqchi ekaningiz",
            "Asosiy qism 3: nega aynan shu joyni tanlaganingiz",
        ],
        "iboralar": ["off the beaten track", "a bucket-list destination", "breathtaking scenery", "steeped in history", "to immerse myself in", "a once-in-a-lifetime experience", "a hidden gem", "vibrant culture"],
        "namuna_javob": "A place I would really love to visit in the future is New Zealand, particularly the South Island, which I first learned about through a series of nature documentaries a couple of years ago.\n\nI came across the documentaries almost by accident while browsing online, and I was completely captivated by the breathtaking scenery, from snow-capped mountains to crystal-clear lakes. Since then, I've done quite a bit of research and discovered that it's also steeped in fascinating Maori history and culture, which only made me want to visit even more.\n\nIf I were to go, I would love to spend time hiking through the national parks and perhaps trying some adventure activities like kayaking, since the landscape seems perfect for that kind of outdoor experience. I'd also want to immerse myself in the local culture by visiting a few Maori cultural sites and trying traditional food.\n\nThe main reason I want to visit is that it feels like a once-in-a-lifetime experience — the combination of stunning natural beauty and rich culture is quite rare to find in a single destination, and it's definitely at the top of my travel bucket list.",
        "part3_savollar": [
            ("Why do you think people want to travel to far-away places?", "I think people are drawn to novelty and new experiences — travelling to unfamiliar places broadens our perspective in a way that staying home simply cannot."),
            ("Do you think tourism can have a negative impact on a country?", "It definitely can — overtourism can put a real strain on local infrastructure and the environment, especially in smaller or more fragile destinations."),
            ("Has technology changed the way people plan their travels?", "Absolutely — nowadays people can research destinations, book flights and read reviews all through their phones, which has made planning far more convenient than it used to be."),
            ("Do you think it's better to travel alone or with other people?", "I think both have their advantages — travelling alone offers more freedom and independence, while travelling with others means you have someone to share the experience with."),
        ],
    },
    {
        "kategoriya": "childhood-skill",
        "cue_card": "Describe a skill you learned as a child.\nYou should say:\n- what the skill was\n- who taught you\n- how long it took to learn\nand explain how this skill has been useful to you.",
        "struktura": [
            "Kirish: ko'nikma nima ekanini ayting",
            "Asosiy qism 1: kim o'rgatgani",
            "Asosiy qism 2: qancha vaqt ketgani",
            "Asosiy qism 3: bu ko'nikma qanday foydali bo'lgani",
        ],
        "iboralar": ["picked it up quickly", "second nature", "practice makes perfect", "a steep learning curve", "hands-on experience", "come in handy", "a valuable life skill", "trial and error"],
        "namuna_javob": "One skill I learned as a child was how to swim, which my father taught me when I was around six years old at our local swimming pool.\n\nIt didn't come easily at first — I remember being quite afraid of the water initially, and it took roughly six months of weekly lessons before I felt genuinely confident swimming on my own. My father was incredibly patient throughout the process, gradually building up my confidence through simple exercises before I eventually learned proper strokes through a fair amount of trial and error.\n\nLooking back, learning to swim has proven to be an incredibly valuable life skill. Beyond simply being an important safety skill, it's also become one of my favourite ways to stay fit as an adult, and it's something that has genuinely come in handy on numerous occasions, whether on beach holidays or during summer trips to lakes with friends. It's also given me the confidence to try other water-based activities, like snorkelling, which I probably wouldn't have attempted otherwise.",
        "part3_savollar": [
            ("What skills do you think children should learn at a young age?", "I think practical skills like swimming, cooking and basic financial literacy are essential, since they have lifelong benefits beyond just academic knowledge."),
            ("Is it easier for children or adults to learn new skills?", "Generally speaking, children tend to pick up new skills more quickly, particularly physical or language-related ones, since their brains are especially adaptable at that age."),
            ("Do you think parents or schools should be responsible for teaching life skills?", "I think it should really be a shared responsibility — parents can teach everyday practical skills at home, while schools can reinforce them in a more structured way."),
            ("How important is it to keep learning new skills as an adult?", "I think it's extremely important, both for personal growth and for staying adaptable in an ever-changing job market where new skills are constantly in demand."),
        ],
    },
]


class Command(BaseCommand):
    help = "20 ta yangi Writing/Speaking namuna mavzusini yaratadi (audio/API kerak emas)"

    def handle(self, *args, **options):
        markaz = Markaz.objects.first()
        if not markaz:
            self.stdout.write(self.style.ERROR("Markaz topilmadi"))
            return

        yaratildi = 0
        for item in TASK1:
            yaratildi += int(self._yarat(
                markaz, f"[Yangi] Writing — {item['kategoriya']}", Bolim.WRITING, item["tur"],
                item["matn"], item["namuna_javob"],
            ))
        for item in TASK2:
            yaratildi += int(self._yarat(
                markaz, f"[Yangi] Writing — {item['kategoriya']}", Bolim.WRITING, item["tur"],
                item["matn"], item["namuna_javob"],
            ))
        for item in PART1:
            matn = f"Mavzu: {item['kategoriya']}\n\n" + "\n".join(
                f"{i + 1}. {q}" for i, (q, _) in enumerate(item["savollar"])
            )
            namuna = "\n\n".join(f"{i + 1}. {a}" for i, (_, a) in enumerate(item["savollar"]))
            namuna += "\n\n[Foydali iboralar]\n" + ", ".join(item["iboralar"])
            yaratildi += int(self._yarat(
                markaz, f"[Yangi] Speaking Part 1 — {item['kategoriya']}", Bolim.SPEAKING, Tur.PART1,
                matn, namuna,
            ))
        for item in PART2_3:
            matn = item["cue_card"] + "\n\n[Struktura]\n" + "\n".join(item["struktura"])
            matn += "\n\n[Part 3 savollari]\n" + "\n".join(f"- {q}" for q, _ in item["part3_savollar"])
            namuna = item["namuna_javob"] + "\n\n[Foydali iboralar]\n" + ", ".join(item["iboralar"])
            namuna += "\n\n[Part 3 namuna javoblari]\n" + "\n\n".join(
                f"{q}\n{a}" for q, a in item["part3_savollar"]
            )
            yaratildi += int(self._yarat(
                markaz, f"[Yangi] Speaking Part 2/3 — {item['kategoriya']}", Bolim.SPEAKING, Tur.PART2,
                matn, namuna,
            ))

        self.stdout.write(self.style.SUCCESS(f"Jami yaratildi: {yaratildi}"))

    def _yarat(self, markaz, name, bolim, tur, matn, namuna_javob):
        if Mashq.objects.filter(markaz=markaz, name=name, bolim=bolim, tur=tur).exists():
            self.stdout.write(f"{name}: allaqachon bor")
            return False
        mashq = Mashq(
            markaz=markaz, name=name, bolim=bolim, tur=tur, korinish="public",
            matn=matn, namuna_javob=namuna_javob,
        )
        mashq.full_clean()
        mashq.save()
        self.stdout.write(self.style.SUCCESS(f"{name}: yaratildi (id={mashq.id})"))
        return True
