import datetime
from typing import List, Dict, Any
from tasks.calendar_config import HolidayType, KZ_FIXED_HOLIDAYS, KZ_FLOATING_HOLIDAYS
from tasks.models import ProductionDay

def is_weekend(date: datetime.date, six_day_week: bool = False) -> bool:
    """Определяет, является ли день стандартным выходным в зависимости от типа недели."""
    # 5: Суббота, 6: Воскресенье
    if six_day_week:
        return date.weekday() == 6
    return date.weekday() >= 5

def generate_calendar_days(year: int, six_day_week: bool = False) -> List[Dict[str, Any]]:
    """
    Генерирует список объектов с информацией о типе каждого дня в году, 
    учитывая правила переноса праздников РК:
    - Гос. праздники при совпадении с выходными переносятся на следующий раб. день.
    - Религиозные праздники не переносятся.
    """
    days = []
    
    # Сначала соберем все "чистые" праздники (без переносов)
    holiday_map = {} # date -> (HolidayType, name)
    
    for month, day, h_type, name in KZ_FIXED_HOLIDAYS:
        try:
            d = datetime.date(year, month, day)
            holiday_map[d] = (h_type, name)
        except ValueError:
            pass # Если вдруг 29 февраля в не високосный год и тп.
            
    if year in KZ_FLOATING_HOLIDAYS:
        for d, h_type, name in KZ_FLOATING_HOLIDAYS[year]:
            holiday_map[d] = (h_type, name)
            
    transferred_to = {} # Date when a transfer happens -> Date of the origin holiday
    
    # 1. Рассчитываем переносы
    sorted_holidays = sorted(holiday_map.keys())
    
    def get_next_working_day(start_date: datetime.date) -> datetime.date:
        """Ищет следующий рабочий день для переноса выходного."""
        curr = start_date + datetime.timedelta(days=1)
        # Следующий день не должен быть выходным, не должен быть другим праздником, 
        # и на него не должен быть уже запланирован другой перенос
        while is_weekend(curr, six_day_week) or curr in holiday_map or curr in transferred_to:
            curr += datetime.timedelta(days=1)
        return curr

    for d in sorted_holidays:
        h_type, name = holiday_map[d]
        # Если ГОС. праздник выпадает на выходной — переносим на первый рабочий
        if h_type == HolidayType.STATE and is_weekend(d, six_day_week):
            next_wd = get_next_working_day(d)
            transferred_to[next_wd] = d

    # 2. Формируем календарь на весь год
    start_date = datetime.date(year, 1, 1)
    end_date = datetime.date(year, 12, 31)
    curr_date = start_date
    
    while curr_date <= end_date:
        if curr_date in holiday_map:
            # На текущую дату выпадает праздник
            days.append({
                "date": curr_date,
                "day_type": ProductionDay.DayType.HOLIDAY,
                "is_transfer": False,
                "note": holiday_map[curr_date][1]
            })
        elif curr_date in transferred_to:
            # На текущую дату выпал перенос выходного
            origin = transferred_to[curr_date]
            origins_name = holiday_map[origin][1]
            days.append({
                "date": curr_date,
                "day_type": ProductionDay.DayType.HOLIDAY,
                "is_transfer": True,
                "note": f"Перенос выходного с {origin.strftime('%d.%m')} ({origins_name})"
            })
        elif is_weekend(curr_date, six_day_week):
            # Обычный выходной день
            days.append({
                "date": curr_date,
                "day_type": ProductionDay.DayType.WEEKEND,
                "is_transfer": False,
                "note": ""
            })
        else:
            # Обычный рабочий день
            days.append({
                "date": curr_date,
                "day_type": ProductionDay.DayType.WORKING,
                "is_transfer": False,
                "note": ""
            })
            
        curr_date += datetime.timedelta(days=1)
        
    return days
