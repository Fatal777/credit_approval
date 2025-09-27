from django.core.management.base import BaseCommand
from loans.tasks import ingest_all_data


class Command(BaseCommand):
    help = 'Ingest customer and loan data from Excel files using background workers'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data ingestion...'))
        
        # Trigger the background task
        result = ingest_all_data.delay()
        
        self.stdout.write(
            self.style.SUCCESS(f'Data ingestion task started with ID: {result.id}')
        )
        self.stdout.write(
            self.style.WARNING('Check Celery worker logs for progress and results.')
        )
