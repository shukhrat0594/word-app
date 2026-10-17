from django.test import SimpleTestCase

from exercises.views import _togri_javoblar_matni


class TogriJavoblarMatniTest(SimpleTestCase):
    """Imtihon natijasida xato javob yonida ko'rsatiladigan to'g'ri javob."""

    def test_turli_kalitlar(self):
        savollar = [
            {"savol": "1", "togri": "TRUE"},
            {"savol": "2", "togri": ["film", " movie ", ""]},
            {"savol": "3", "togri": ""},
            {"savol": "4", "erkin": True, "togri": "x"},
            {"savol": "5"},
        ]
        self.assertEqual(
            _togri_javoblar_matni(savollar),
            [["TRUE"], ["film", "movie"], [], [], []],
        )
