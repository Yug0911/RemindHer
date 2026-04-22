from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from .models import Reminder, InventoryItem


@shared_task
def check_reminders():
    now = timezone.now()
    due = Reminder.objects.filter(
        is_completed=False, is_snoozed=False,
        reminder_date=now.date(), reminder_time__lte=now.time()
    )
    for r in due:
        print(f"[DUE] {r.user.email}: {r.task}")
        if r.reminder_type == 'once':
            r.is_completed = True
            r.save()


@shared_task
def check_inventory_alerts():
    today = timezone.now().date()
    expiring = InventoryItem.objects.filter(
        expiration_date__gte=today,
        expiration_date__lte=today + timezone.timedelta(days=3)
    ).select_related('user')
    for item in expiring:
        print(f"[EXPIRY] {item.user.email}: {item.name} expires {item.expiration_date}")