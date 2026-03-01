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


@register_tool
class AddCurrency(AssistantTool):
    name = "add_currency"
    description = "Add a new currency with exchange rate."
    module_id = "multicurrency"
    required_permission = "multicurrency.add_currency"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Currency code (e.g. USD, GBP)"},
            "name": {"type": "string", "description": "Currency name"},
            "symbol": {"type": "string", "description": "Currency symbol (e.g. $, £)"},
            "exchange_rate": {"type": "string", "description": "Exchange rate relative to base currency"},
            "decimal_places": {"type": "integer", "description": "Decimal places (default: 2)"},
        },
        "required": ["code", "name", "symbol", "exchange_rate"],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from decimal import Decimal
        from multicurrency.models import Currency
        c = Currency.objects.create(
            code=args['code'].upper(),
            name=args['name'],
            symbol=args['symbol'],
            exchange_rate=Decimal(args['exchange_rate']),
            decimal_places=args.get('decimal_places', 2),
            is_active=True,
        )
        return {"id": str(c.id), "code": c.code, "name": c.name, "created": True}


@register_tool
class UpdateExchangeRate(AssistantTool):
    name = "update_exchange_rate"
    description = "Update the exchange rate for a currency."
    module_id = "multicurrency"
    required_permission = "multicurrency.change_currency"
    requires_confirmation = True
    parameters = {
        "type": "object",
        "properties": {
            "currency_code": {"type": "string", "description": "Currency code (e.g. USD)"},
            "exchange_rate": {"type": "string", "description": "New exchange rate"},
        },
        "required": ["currency_code", "exchange_rate"],
        "additionalProperties": False,
    }

    def execute(self, args, request):
        from decimal import Decimal
        from django.utils import timezone
        from multicurrency.models import Currency
        c = Currency.objects.get(code=args['currency_code'].upper())
        old_rate = c.exchange_rate
        c.exchange_rate = Decimal(args['exchange_rate'])
        c.last_updated = timezone.now()
        c.save(update_fields=['exchange_rate', 'last_updated'])
        # Add history record
        try:
            from multicurrency.models import ExchangeRateHistory
            ExchangeRateHistory.objects.create(
                currency=c, rate=c.exchange_rate, source='manual',
            )
        except Exception:
            pass
        return {
            "code": c.code, "old_rate": str(old_rate),
            "new_rate": str(c.exchange_rate), "updated": True,
        }
