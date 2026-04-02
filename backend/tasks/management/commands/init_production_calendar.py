import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from tasks.models import ProductionDay

class Command(BaseCommand):
    help = 'Populate production calendar with initial data (standard weekends)'

    def add_arguments(self, parser):
        parser.add_argument('--years', type=int, default=2)

    def handle(self, *args, **options):
        years = options['years']
        start_date = datetime.date(2025, 1, 1)
        end_date = start_date + datetime.timedelta(days=365 * years)
        
        self.stdout.write(f"Populating calendar from {start_date} to {end_date}...")
        
        current_date = start_date
        working_days_counter = 0
        
        # Determine the initial working_days_since_epoch 
        # (Could be 0 if starting from fresh epoch)
        
        batch = []
        while current_date <= end_date:
            # Simple weekend logic: Saturday (5) and Sunday (6)
            is_weekend = current_date.weekday() >= 5
            day_type = ProductionDay.DayType.WEEKEND if is_weekend else ProductionDay.DayType.WORKING
            
            if day_type in [ProductionDay.DayType.WORKING, ProductionDay.DayType.SHORT]:
                working_days_counter += 1
                
            batch.append(ProductionDay(
                date=current_date,
                day_type=day_type,
                working_days_since_epoch=working_days_counter
            ))
            
            if len(batch) >= 1000:
                ProductionDay.objects.bulk_create(batch, ignore_conflicts=True)
                batch = []
                
            current_date += datetime.timedelta(days=1)
            
        if batch:
            ProductionDay.objects.bulk_create(batch, ignore_conflicts=True)
            
        self.stdout.write(self.style.SUCCESS(f"Successfully populated {working_days_counter} working days."))
