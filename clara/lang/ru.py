"""Russian language pack.

Reading ease uses the Oborneva (2006) adaptation of Flesch for Russian
(206.835 - 1.3*ASL - 60.1*ASW), which is the widely cited coefficient set.
No validated Russian grade-level formula ships yet, so grade_coeffs is None and
the grade metric is reported as null rather than a fabricated number — add one
via a pull request when a validated coefficient set is available.
"""
from __future__ import annotations

import re

from .base import LanguagePack

# Month names in nominative and genitive (dates read "31 января 2024").
_MONTHS = {
    "январь": 1, "января": 1, "февраль": 2, "февраля": 2, "март": 3, "марта": 3,
    "апрель": 4, "апреля": 4, "май": 5, "мая": 5, "июнь": 6, "июня": 6,
    "июль": 7, "июля": 7, "август": 8, "августа": 8, "сентябрь": 9, "сентября": 9,
    "октябрь": 10, "октября": 10, "ноябрь": 11, "ноября": 11, "декабрь": 12, "декабря": 12,
}

_STOP = {
    "и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то",
    "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же", "вы", "за",
    "бы", "по", "только", "ее", "мне", "было", "вот", "от", "меня", "нет", "о",
    "из", "ему", "когда", "даже", "ну", "ли", "если", "уже", "или", "ни", "быть",
    "был", "до", "вас", "вам", "там", "себя", "они", "тут", "где", "есть", "для",
    "мы", "тебя", "их", "чем", "была", "без", "чего", "раз", "тоже", "себе", "под",
    "будет", "тогда", "кто", "этот", "того", "потому", "этого", "какой",
    "здесь", "этом", "один", "мой", "тем", "чтобы", "нее", "были", "куда", "зачем",
    "всех", "можно", "при", "два", "об", "другой", "после", "над", "больше", "тот",
    "через", "эти", "нас", "про", "всего", "них", "какая", "много", "три", "эту",
    "перед", "иногда", "чуть", "том", "нельзя", "такой", "им", "более", "всегда",
    "всю", "между", "это", "эта",
}


class RussianPack(LanguagePack):
    code = "ru"
    name = "Russian"

    word_re = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)?")
    sent_re = re.compile(r"[.!?…]+")
    keyword_re = re.compile(r"[А-Яа-яЁё]{3,}")
    vowels = "аеёиоуыэюя"

    ease_coeffs = (206.835, 1.3, 60.1)  # Oborneva 2006
    grade_coeffs = None                 # no validated Russian grade formula yet

    months = _MONTHS
    negation = ["не", "нет", "ни", "нельзя", "без", "никогда", "никакой"]
    obligation = ["должен", "должна", "должно", "должны", "обязан", "обязана",
                  "обязаны", "необходимо", "требуется"]
    condition = ["если", "кроме", "за исключением", "в случае", "при условии"]
    stopwords = _STOP

    pictogram_lang = "ru"
    simplify_note = "Пиши ясным, простым русским языком. Ответ давай только на русском."
