// Listening trainer (2026-11-12, TZ 712) uchun diktant matnlari.
//
// TZ "dailydictation.com saytidan kontentni olib joylashtir" degan edi.
// O'sha saytning audio va matnlari uning mulki (mualliflik huquqi), shuning
// uchun ular KO'CHIRILMADI — format (qisqa darslar, gapma-gap diktant,
// darajalar) o'sha saytdagidek, lekin gaplar shu yerda yangidan yozilgan.
// Ovozni brauzer o'zi o'qiydi (Web Speech API), alohida audio fayl yo'q.
//
// Yangi dars qo'shish: tegishli darajaning `darslar` ro'yxatiga
// { nom, gaplar: [...] } qo'shish kifoya.
export const DARAJALAR = [
  {
    kalit: "A1",
    nom: "A1 — Beginner",
    darslar: [
      {
        nom: "My family",
        gaplar: [
          "My name is Anna.",
          "I live with my parents and my little brother.",
          "My father is a doctor.",
          "My mother works at a school.",
          "My brother is seven years old.",
          "We have a small cat called Tom.",
        ],
      },
      {
        nom: "My day",
        gaplar: [
          "I get up at seven o'clock.",
          "I have breakfast with my family.",
          "I go to school by bus.",
          "Lessons start at eight thirty.",
          "In the evening I do my homework.",
          "I go to bed at ten.",
        ],
      },
      {
        nom: "At the shop",
        gaplar: [
          "Can I help you?",
          "I want two apples and some bread.",
          "How much is this milk?",
          "It is one dollar.",
          "Here is your change.",
          "Thank you, have a nice day.",
        ],
      },
    ],
  },
  {
    kalit: "A2",
    nom: "A2 — Elementary",
    darslar: [
      {
        nom: "Last weekend",
        gaplar: [
          "Last Saturday I visited my grandparents.",
          "They live in a small village near the river.",
          "We had lunch in the garden.",
          "My grandmother made a delicious soup.",
          "In the afternoon we went for a walk.",
          "I came back home late in the evening.",
        ],
      },
      {
        nom: "The weather",
        gaplar: [
          "It is very cold today.",
          "Yesterday it was sunny and warm.",
          "Tomorrow it is going to rain.",
          "Don't forget to take your umbrella.",
          "I like spring more than winter.",
          "In summer we often swim in the lake.",
        ],
      },
      {
        nom: "At the restaurant",
        gaplar: [
          "Could we have a table for two, please?",
          "Are you ready to order?",
          "I'd like the chicken with rice.",
          "Would you like something to drink?",
          "Just a glass of water, please.",
          "Can we have the bill, please?",
        ],
      },
    ],
  },
  {
    kalit: "B1",
    nom: "B1 — Intermediate",
    darslar: [
      {
        nom: "Learning English",
        gaplar: [
          "I have been learning English for three years.",
          "At first, listening was the hardest part for me.",
          "Native speakers seemed to talk very fast.",
          "Then I started watching films with subtitles.",
          "Now I can understand most of what people say.",
          "My next goal is to pass the IELTS exam.",
        ],
      },
      {
        nom: "A job interview",
        gaplar: [
          "Thank you for coming in today.",
          "Could you tell me a little about yourself?",
          "I graduated from university two years ago.",
          "Since then I have worked as a sales assistant.",
          "I'm looking for a job where I can use my languages.",
          "We will let you know our decision by Friday.",
        ],
      },
      {
        nom: "Travelling by train",
        gaplar: [
          "The train to Samarkand leaves at nine fifteen.",
          "Passengers should arrive at least twenty minutes early.",
          "Please keep your ticket until the end of the journey.",
          "The journey takes about two hours.",
          "There is a café in the middle of the train.",
          "We apologise for the short delay.",
        ],
      },
    ],
  },
  {
    kalit: "B2",
    nom: "B2 — Upper-intermediate",
    darslar: [
      {
        nom: "Technology and us",
        gaplar: [
          "Smartphones have completely changed the way we communicate.",
          "Many people check their phones before they even get out of bed.",
          "Some experts believe this habit can affect our concentration.",
          "On the other hand, technology makes learning more accessible.",
          "Online courses allow students to study at their own pace.",
          "The key is to use these tools wisely rather than avoid them.",
        ],
      },
      {
        nom: "City life",
        gaplar: [
          "More than half of the world's population now lives in cities.",
          "Urban areas offer better access to jobs and education.",
          "However, traffic and pollution are growing problems.",
          "Several cities have introduced car-free zones in the centre.",
          "Public transport needs to be cheap and reliable to attract people.",
          "Planners are also trying to create more green spaces.",
        ],
      },
      {
        nom: "Healthy habits",
        gaplar: [
          "Getting enough sleep is just as important as eating well.",
          "Most adults need between seven and nine hours a night.",
          "Regular exercise reduces stress and improves your mood.",
          "You don't have to join a gym to stay active.",
          "Even a thirty-minute walk every day makes a difference.",
          "Small changes are easier to maintain than dramatic ones.",
        ],
      },
    ],
  },
];
