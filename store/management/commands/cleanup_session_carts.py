from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from store.models import Cart


class Command(BaseCommand):
    help = 'Clean up orphaned session carts older than specified days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Delete session carts older than this many days (default: 7)'
        )

    def handle(self, *args, **options):
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Delete session carts (user=None) older than cutoff date
        deleted_count = Cart.objects.filter(
            user=None,
            created_at__lt=cutoff_date
        ).delete()[0]
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully deleted {deleted_count} orphaned session carts older than {days} days'
            )
        )
