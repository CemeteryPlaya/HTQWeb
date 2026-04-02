import datetime
from enum import Enum

class HolidayType(Enum):
    STATE = 'state'
    RELIGIOUS = 'religious'

# Фиксированные праздники в РК (Месяц, День, Тип, Название)
KZ_FIXED_HOLIDAYS = [
    (1, 1, HolidayType.STATE, "Новый год"),
    (1, 2, HolidayType.STATE, "Новый год"),
    (1, 7, HolidayType.RELIGIOUS, "Православное Рождество"),
    (3, 8, HolidayType.STATE, "Международный женский день"),
    (3, 21, HolidayType.STATE, "Наурыз мейрамы"),
    (3, 22, HolidayType.STATE, "Наурыз мейрамы"),
    (3, 23, HolidayType.STATE, "Наурыз мейрамы"),
    (5, 1, HolidayType.STATE, "Праздник единства народа Казахстана"),
    (5, 7, HolidayType.STATE, "День защитника Отечества"),
    (5, 9, HolidayType.STATE, "День Победы"),
    (7, 6, HolidayType.STATE, "День Столицы"),
    (8, 30, HolidayType.STATE, "День Конституции РК"),
    (10, 25, HolidayType.STATE, "День Республики"),
    (12, 16, HolidayType.STATE, "День Независимости"),
]

# Плавающие праздники (например, Курбан-айт) (Год -> Список дат)
KZ_FLOATING_HOLIDAYS = {
    2026: [
        (datetime.date(2026, 5, 27), HolidayType.RELIGIOUS, "Курбан-айт"),
    ]
}
