from django import template
from decimal import Decimal, ROUND_HALF_UP

register = template.Library()

@register.filter
def to_pi(euros, eur_per_pi):
    try:
        euros = Decimal(str(euros))
        eur_per_pi = Decimal(str(eur_per_pi))
        if eur_per_pi <= 0:
            return ""
        return (euros / eur_per_pi).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    except Exception:
        return ""
