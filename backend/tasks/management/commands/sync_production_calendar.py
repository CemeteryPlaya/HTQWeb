import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from tasks.models import ProductionDay
from tasks.utils.calendar import generate_calendar_days

class Command(BaseCommand):
    help = 'Sync production calendar for a specified year based on RK rules'

    def add_arguments(self, parser):
        parser.add_argument('year', type=int, help='The year to sync (e.g. 2026)')
        parser.add_argument('--workdays', type=int, choices=[5, 6], default=5, help='5 or 6 day working week (default 5)')

    def handle(self, *args, **options):
        year = options['year']
        six_day_week = (options['workdays'] == 6)
        
        self.stdout.write(f"Generating calendar for {year} (working days: {options['workdays']})...")
        
        days_data = generate_calendar_days(year, six_day_week=six_day_week)
        
        with transaction.atomic():
            # Находим предыдущий счетчик (от конца прошлого года)
            last_day_prev_year = ProductionDay.objects.filter(date=datetime.date(year - 1, 12, 31)).first()
            if last_day_prev_year:
                working_days_counter = last_day_prev_year.working_days_since_epoch
            else:
                self.stdout.write(self.style.WARNING(f"Could not find ProductionDay for {year - 1}-12-31. Starting from 0 or closest found."))
                closest_prev = ProductionDay.objects.filter(date__lt=datetime.date(year, 1, 1)).order_by('-date').first()
                if closest_prev:
                    working_days_counter = closest_prev.working_days_since_epoch
                    self.stdout.write(self.style.WARNING(f"Falling back to closest previous day: {closest_prev.date} (counter: {working_days_counter})."))
                else:
                    working_days_counter = 0

            # Синхронизируем дни указанного года
            for day_info in days_data:
                d = day_info['date']
                d_type = day_info['day_type']
                
                # Инкремент для рабочих дней
                if d_type in [ProductionDay.DayType.WORKING, ProductionDay.DayType.SHORT]:
                    working_days_counter += 1
                
                ProductionDay.objects.update_or_create(
                    date=d,
                    defaults={
                        'day_type': d_type,
                        'working_days_since_epoch': working_days_counter
                    }
                )
                
            # Пересчет для последующих годов в базе, если они есть
            # Это крайне важно, чтобы дедлайны были валидны за пределы текущего года
            future_days = ProductionDay.objects.filter(date__gt=datetime.date(year, 12, 31)).order_by('date')
            if future_days.exists():
                self.stdout.write("Recalculating cumulative sums for future years in DB...")
                for f_day in future_days:
                    if f_day.day_type in [ProductionDay.DayType.WORKING, ProductionDay.DayType.SHORT]:
                        working_days_counter += 1
                    
                    if f_day.working_days_since_epoch != working_days_counter:
                        f_day.working_days_since_epoch = working_days_counter
                        f_day.save(update_fields=['working_days_since_epoch'])
                        
        self.stdout.write(self.style.SUCCESS(f"Successfully synced calendar for {year}. Total days processed: {len(days_data)}"))
