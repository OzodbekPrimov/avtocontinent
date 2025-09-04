from ..models import ExchangeRate

def get_latest_exchange_rate():
    """
    Returns the latest active exchange rate or None if not found
    """
    try:
        rate = ExchangeRate.objects.filter(is_active=True).order_by('-created_at').first()
        return float(rate.usd_to_uzs) if rate else None
    except (AttributeError, ValueError, ExchangeRate.DoesNotExist):
        return None
