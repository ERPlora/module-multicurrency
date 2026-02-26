"""AI tools for the Multi-Currency module."""
from assistant.tools import AssistantTool, register_tool


@register_tool
class ListCurrencies(AssistantTool):
    name = "list_currencies"
    description = "List configured currencies with exchange rates."
    module_id = "multicurrency"
    required_permission = "multicurrency.view_currency"
    parameters = {
        "type": "object",
        "properties": {
            "active_only": {"type": "boolean", "description": "Only show active currencies"},
        },
        "required": [],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from multicurrency.models import Currency
        qs = Currency.objects.all().order_by('sort_order')
        if args.get('active_only', True):
            qs = qs.filter(is_active=True)
        return {
            "currencies": [
                {
                    "id": str(c.id),
                    "code": c.code,
                    "name": c.name,
                    "symbol": c.symbol,
                    "exchange_rate": str(c.exchange_rate),
                    "is_active": c.is_active,
                    "last_updated": str(c.last_updated) if c.last_updated else None,
                }
                for c in qs
            ]
        }


@register_tool
class ConvertCurrency(AssistantTool):
    name = "convert_currency"
    description = "Convert an amount between currencies using current exchange rates."
    module_id = "multicurrency"
    required_permission = "multicurrency.view_currency"
    parameters = {
        "type": "object",
        "properties": {
            "amount": {"type": "string", "description": "Amount to convert"},
            "from_currency": {"type": "string", "description": "Source currency code (e.g. EUR)"},
            "to_currency": {"type": "string", "description": "Target currency code (e.g. USD)"},
        },
        "required": ["amount", "from_currency", "to_currency"],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from decimal import Decimal
        from multicurrency.models import Currency
        amount = Decimal(args['amount'])
        from_curr = Currency.objects.get(code=args['from_currency'].upper())
        to_curr = Currency.objects.get(code=args['to_currency'].upper())
        # Convert via base currency (rate is relative to base)
        base_amount = amount / from_curr.exchange_rate if from_curr.exchange_rate else amount
        converted = base_amount * to_curr.exchange_rate
        return {
            "amount": str(amount),
            "from": from_curr.code,
            "to": to_curr.code,
            "converted": str(round(converted, to_curr.decimal_places)),
            "rate": str(to_curr.exchange_rate / from_curr.exchange_rate) if from_curr.exchange_rate else None,
        }
