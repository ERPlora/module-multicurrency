"""Multi-currency views."""

from decimal import Decimal, InvalidOperation

from django.http import JsonResponse
from django.shortcuts import render as django_render
from django.views.decorators.http import require_POST, require_http_methods
from django.utils.translation import gettext as _
from django.utils import timezone
from django.contrib import messages

from apps.accounts.decorators import login_required
from apps.core.htmx import htmx_view
from apps.modules_runtime.navigation import with_module_nav

from .models import CurrencySettings, Currency, ExchangeRateHistory, CurrencyPayment
from .forms import CurrencyForm, CurrencySettingsForm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hub(request):
    return request.session.get('hub_id')


def _render_currency_list(request, hub):
    """Render the currencies list partial after a mutation."""
    currencies = Currency.objects.filter(
        hub_id=hub, is_deleted=False,
    ).order_by('sort_order', 'code')
    settings_obj = CurrencySettings.get_settings(hub)
    return django_render(request, 'multicurrency/partials/currencies_table.html', {
        'currencies': currencies,
        'settings': settings_obj,
    })


# ---------------------------------------------------------------------------
# Dashboard (Exchange Rates)
# ---------------------------------------------------------------------------

@login_required
@with_module_nav('multicurrency', 'dashboard')
@htmx_view('multicurrency/pages/dashboard.html', 'multicurrency/partials/dashboard_content.html')
def index(request):
    return _dashboard_context(request)


@login_required
@with_module_nav('multicurrency', 'dashboard')
@htmx_view('multicurrency/pages/dashboard.html', 'multicurrency/partials/dashboard_content.html')
def dashboard(request):
    return _dashboard_context(request)


def _dashboard_context(request):
    hub = _hub(request)
    settings_obj = CurrencySettings.get_settings(hub)
    currencies = Currency.objects.filter(
        hub_id=hub, is_deleted=False, is_active=True,
    ).order_by('sort_order', 'code')

    # Recent payments
    recent_payments = CurrencyPayment.objects.filter(
        hub_id=hub, is_deleted=False,
    ).select_related('currency').order_by('-payment_date')[:10]

    return {
        'settings': settings_obj,
        'currencies': currencies,
        'recent_payments': recent_payments,
    }


# ---------------------------------------------------------------------------
# Update Rates
# ---------------------------------------------------------------------------

@login_required
@require_POST
def update_rates(request):
    """Fetch latest rates from configured source."""
    hub = _hub(request)
    settings_obj = CurrencySettings.get_settings(hub)
    currencies = Currency.objects.filter(
        hub_id=hub, is_deleted=False, is_active=True,
    )

    if settings_obj.rate_source == 'manual':
        return JsonResponse({
            'ok': False,
            'error': _('Rate source is set to manual. Update rates manually.'),
        }, status=400)

    updated = 0
    errors = []

    if settings_obj.rate_source == 'ecb':
        try:
            import urllib.request
            import xml.etree.ElementTree as ET

            url = 'https://www.ecb.europa.eu/stats/eurofornex/eurofxref-daily.xml'
            with urllib.request.urlopen(url, timeout=10) as resp:
                tree = ET.parse(resp)

            ns = {'gesmes': 'http://www.gesmes.org/xml/2002-08-01',
                  'eurofxref': 'http://www.ecb.int/vocabulary/2002-08-01/eurofxref'}
            cubes = tree.findall('.//eurofxref:Cube[@currency]', ns)

            ecb_rates = {}
            for cube in cubes:
                ecb_rates[cube.attrib['currency']] = Decimal(cube.attrib['rate'])

            base = settings_obj.base_currency.upper()

            for currency in currencies:
                code = currency.code.upper()
                if code == base:
                    continue

                new_rate = None
                if base == 'EUR' and code in ecb_rates:
                    new_rate = ecb_rates[code]
                elif base in ecb_rates and code == 'EUR':
                    new_rate = Decimal('1') / ecb_rates[base]
                elif base in ecb_rates and code in ecb_rates:
                    # Cross rate via EUR
                    new_rate = ecb_rates[code] / ecb_rates[base]

                if new_rate is not None:
                    new_rate = new_rate.quantize(Decimal('0.000001'))
                    currency.exchange_rate = new_rate
                    currency.last_updated = timezone.now()
                    currency.save(update_fields=[
                        'exchange_rate', 'last_updated', 'updated_at',
                    ])
                    ExchangeRateHistory.objects.create(
                        hub_id=hub,
                        currency=currency,
                        rate=new_rate,
                        source='ecb',
                    )
                    updated += 1
                else:
                    errors.append(f'{code}: {_("Not available from ECB")}')

        except Exception as e:
            return JsonResponse({
                'ok': False,
                'error': _('Failed to fetch ECB rates: %(error)s') % {'error': str(e)},
            }, status=500)

    elif settings_obj.rate_source == 'exchangerate_api':
        if not settings_obj.api_key:
            return JsonResponse({
                'ok': False,
                'error': _('API key is required for ExchangeRate API'),
            }, status=400)

        try:
            import urllib.request
            import json

            base = settings_obj.base_currency.upper()
            url = f'https://v6.exchangerate-api.com/v6/{settings_obj.api_key}/latest/{base}'
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            if data.get('result') != 'success':
                return JsonResponse({
                    'ok': False,
                    'error': _('API returned error: %(error)s') % {
                        'error': data.get('error-type', 'unknown'),
                    },
                }, status=500)

            api_rates = data.get('conversion_rates', {})

            for currency in currencies:
                code = currency.code.upper()
                if code == base:
                    continue
                if code in api_rates:
                    new_rate = Decimal(str(api_rates[code])).quantize(Decimal('0.000001'))
                    currency.exchange_rate = new_rate
                    currency.last_updated = timezone.now()
                    currency.save(update_fields=[
                        'exchange_rate', 'last_updated', 'updated_at',
                    ])
                    ExchangeRateHistory.objects.create(
                        hub_id=hub,
                        currency=currency,
                        rate=new_rate,
                        source='exchangerate_api',
                    )
                    updated += 1
                else:
                    errors.append(f'{code}: {_("Not available from API")}')

        except Exception as e:
            return JsonResponse({
                'ok': False,
                'error': _('Failed to fetch API rates: %(error)s') % {'error': str(e)},
            }, status=500)

    result = {'ok': True, 'updated': updated}
    if errors:
        result['warnings'] = errors

    return JsonResponse(result)


# ---------------------------------------------------------------------------
# Currencies CRUD
# ---------------------------------------------------------------------------

@login_required
@with_module_nav('multicurrency', 'currencies')
@htmx_view('multicurrency/pages/currencies.html', 'multicurrency/partials/currencies_content.html')
def currencies(request):
    hub = _hub(request)
    currency_list = Currency.objects.filter(
        hub_id=hub, is_deleted=False,
    ).order_by('sort_order', 'code')
    settings_obj = CurrencySettings.get_settings(hub)

    return {
        'currencies': currency_list,
        'settings': settings_obj,
    }


@login_required
@with_module_nav('multicurrency', 'currencies')
@htmx_view('multicurrency/pages/currency_form.html', 'multicurrency/partials/currency_form_content.html')
def currency_create(request):
    hub = _hub(request)

    if request.method == 'POST':
        form = CurrencyForm(request.POST)
        if form.is_valid():
            currency = form.save(commit=False)
            currency.hub_id = hub
            currency.code = currency.code.upper()
            currency.last_updated = timezone.now()
            currency.save()

            # Record initial rate in history
            ExchangeRateHistory.objects.create(
                hub_id=hub,
                currency=currency,
                rate=currency.exchange_rate,
                source='manual',
            )

            messages.success(request, _('Currency created successfully'))
            return JsonResponse({'ok': True, 'id': str(currency.pk)})
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    return {'form': CurrencyForm()}


@login_required
@with_module_nav('multicurrency', 'currencies')
@htmx_view('multicurrency/pages/currency_form.html', 'multicurrency/partials/currency_form_content.html')
def currency_edit(request, pk):
    hub = _hub(request)
    currency = Currency.objects.filter(
        pk=pk, hub_id=hub, is_deleted=False,
    ).first()

    if not currency:
        return {'error': _('Currency not found')}

    if request.method == 'POST':
        old_rate = currency.exchange_rate
        form = CurrencyForm(request.POST, instance=currency)
        if form.is_valid():
            currency = form.save(commit=False)
            currency.code = currency.code.upper()

            # Record rate change in history if rate changed
            new_rate = currency.exchange_rate
            if old_rate != new_rate:
                currency.last_updated = timezone.now()
                ExchangeRateHistory.objects.create(
                    hub_id=hub,
                    currency=currency,
                    rate=new_rate,
                    source='manual',
                )

            currency.save()
            messages.success(request, _('Currency updated successfully'))
            return JsonResponse({'ok': True})
        return JsonResponse({'ok': False, 'errors': form.errors}, status=400)

    return {'form': CurrencyForm(instance=currency), 'currency': currency}


@login_required
@require_POST
def currency_delete(request, pk):
    hub = _hub(request)
    currency = Currency.objects.filter(
        pk=pk, hub_id=hub, is_deleted=False,
    ).first()

    if not currency:
        return JsonResponse({'ok': False, 'error': _('Currency not found')}, status=404)

    # Check for existing payments
    has_payments = CurrencyPayment.objects.filter(
        currency=currency, is_deleted=False,
    ).exists()
    if has_payments:
        return JsonResponse({
            'ok': False,
            'error': _('Cannot delete currency with existing payments'),
        }, status=400)

    currency.is_deleted = True
    currency.deleted_at = timezone.now()
    currency.save(update_fields=['is_deleted', 'deleted_at', 'updated_at'])
    messages.success(request, _('Currency deleted successfully'))

    return _render_currency_list(request, hub)


@login_required
@require_POST
def currency_toggle(request, pk):
    """Toggle a currency active/inactive status."""
    hub = _hub(request)
    currency = Currency.objects.filter(
        pk=pk, hub_id=hub, is_deleted=False,
    ).first()

    if not currency:
        return JsonResponse({'ok': False, 'error': _('Currency not found')}, status=404)

    currency.is_active = not currency.is_active
    currency.save(update_fields=['is_active', 'updated_at'])

    status = _('activated') if currency.is_active else _('deactivated')
    messages.success(request, _('Currency %(status)s successfully') % {'status': status})
    return _render_currency_list(request, hub)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@login_required
@with_module_nav('multicurrency', 'history')
@htmx_view('multicurrency/pages/history.html', 'multicurrency/partials/history_content.html')
def history(request):
    hub = _hub(request)

    # Filter by currency if specified
    currency_filter = request.GET.get('currency', '')
    qs = ExchangeRateHistory.objects.filter(
        hub_id=hub, is_deleted=False,
    ).select_related('currency').order_by('-recorded_at')

    if currency_filter:
        qs = qs.filter(currency__code=currency_filter)

    # Available currencies for filter dropdown
    available_currencies = Currency.objects.filter(
        hub_id=hub, is_deleted=False,
    ).order_by('code').values_list('code', flat=True)

    return {
        'history': qs[:100],
        'currency_filter': currency_filter,
        'available_currencies': list(available_currencies),
    }


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

@login_required
@require_http_methods(['GET'])
def api_convert(request):
    """API to convert amount: ?from=USD&to=EUR&amount=100"""
    hub = _hub(request)
    from_code = request.GET.get('from', '').upper()
    to_code = request.GET.get('to', '').upper()
    amount_str = request.GET.get('amount', '0')

    try:
        amount = Decimal(amount_str)
    except (InvalidOperation, ValueError):
        return JsonResponse({'ok': False, 'error': _('Invalid amount')}, status=400)

    if not from_code or not to_code:
        return JsonResponse({'ok': False, 'error': _('Missing from/to parameters')}, status=400)

    settings_obj = CurrencySettings.get_settings(hub)
    base = settings_obj.base_currency.upper()

    # Get currencies
    from_currency = None
    to_currency = None

    if from_code != base:
        from_currency = Currency.objects.filter(
            hub_id=hub, code=from_code, is_active=True, is_deleted=False,
        ).first()
        if not from_currency:
            return JsonResponse({
                'ok': False,
                'error': _('Currency %(code)s not found') % {'code': from_code},
            }, status=404)

    if to_code != base:
        to_currency = Currency.objects.filter(
            hub_id=hub, code=to_code, is_active=True, is_deleted=False,
        ).first()
        if not to_currency:
            return JsonResponse({
                'ok': False,
                'error': _('Currency %(code)s not found') % {'code': to_code},
            }, status=404)

    # Convert: from -> base -> to
    if from_currency:
        base_amount = from_currency.convert_to_base(amount)
    else:
        base_amount = amount

    if to_currency:
        result = to_currency.convert_from_base(base_amount)
    else:
        result = base_amount

    return JsonResponse({
        'ok': True,
        'from': from_code,
        'to': to_code,
        'amount': str(amount),
        'result': str(result),
        'rate': str(
            (to_currency.exchange_rate if to_currency else Decimal('1'))
            / (from_currency.exchange_rate if from_currency else Decimal('1'))
        ),
    })


@login_required
@require_http_methods(['GET'])
def api_rates(request):
    """API returning current rates as JSON (for POS frontend)."""
    hub = _hub(request)
    settings_obj = CurrencySettings.get_settings(hub)
    currencies_qs = Currency.objects.filter(
        hub_id=hub, is_deleted=False, is_active=True,
    ).order_by('sort_order', 'code')

    rates = []
    for c in currencies_qs:
        rates.append({
            'code': c.code,
            'name': c.name,
            'symbol': c.symbol,
            'exchange_rate': str(c.exchange_rate),
            'decimal_places': c.decimal_places,
            'last_updated': c.last_updated.isoformat() if c.last_updated else None,
        })

    return JsonResponse({
        'ok': True,
        'base_currency': settings_obj.base_currency,
        'rates': rates,
    })


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

@login_required
@with_module_nav('multicurrency', 'settings')
@htmx_view('multicurrency/pages/settings.html', 'multicurrency/partials/settings_content.html')
def settings_view(request):
    hub = _hub(request)
    settings_obj = CurrencySettings.get_settings(hub)
    form = CurrencySettingsForm(instance=settings_obj)
    return {'form': form, 'settings': settings_obj}


@login_required
@require_POST
def settings_save(request):
    hub = _hub(request)
    settings_obj = CurrencySettings.get_settings(hub)
    form = CurrencySettingsForm(request.POST, instance=settings_obj)
    if form.is_valid():
        form.save()
        messages.success(request, _('Settings saved successfully'))
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False, 'errors': form.errors}, status=400)
