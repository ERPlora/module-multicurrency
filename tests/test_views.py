"""
Integration tests for Multi-currency views.
"""

import json
import uuid
import pytest
from decimal import Decimal
from django.test import Client
from django.utils import timezone


pytestmark = [pytest.mark.django_db, pytest.mark.unit]


# ---------------------------------------------------------------------------
# Dashboard / Index
# ---------------------------------------------------------------------------

class TestDashboard:

    def test_requires_login(self):
        client = Client()
        response = client.get('/m/multicurrency/')
        assert response.status_code == 302

    def test_index_loads(self, auth_client):
        response = auth_client.get('/m/multicurrency/')
        assert response.status_code == 200

    def test_index_htmx(self, auth_client):
        response = auth_client.get('/m/multicurrency/', HTTP_HX_REQUEST='true')
        assert response.status_code == 200

    def test_dashboard_loads(self, auth_client):
        response = auth_client.get('/m/multicurrency/dashboard/')
        assert response.status_code == 200

    def test_dashboard_with_currencies(self, auth_client, usd_currency, gbp_currency):
        response = auth_client.get('/m/multicurrency/')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Currencies List
# ---------------------------------------------------------------------------

class TestCurrenciesList:

    def test_currencies_list_loads(self, auth_client):
        response = auth_client.get('/m/multicurrency/currencies/')
        assert response.status_code == 200

    def test_currencies_list_with_data(self, auth_client, usd_currency, gbp_currency):
        response = auth_client.get('/m/multicurrency/currencies/')
        assert response.status_code == 200

    def test_currencies_list_htmx(self, auth_client):
        response = auth_client.get('/m/multicurrency/currencies/', HTTP_HX_REQUEST='true')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Currency Create
# ---------------------------------------------------------------------------

class TestCurrencyCreate:

    def test_create_form_loads(self, auth_client):
        response = auth_client.get('/m/multicurrency/currencies/new/')
        assert response.status_code == 200

    def test_create_form_htmx(self, auth_client):
        response = auth_client.get(
            '/m/multicurrency/currencies/new/', HTTP_HX_REQUEST='true',
        )
        assert response.status_code == 200

    def test_create_currency_post(self, auth_client):
        from multicurrency.models import Currency
        response = auth_client.post('/m/multicurrency/currencies/new/', {
            'code': 'CHF',
            'name': 'Swiss Franc',
            'symbol': 'CHF',
            'decimal_places': 2,
            'exchange_rate': '0.945000',
            'is_active': True,
            'sort_order': 0,
        })
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert Currency.objects.filter(code='CHF').exists()

    def test_create_currency_records_history(self, auth_client):
        from multicurrency.models import Currency, ExchangeRateHistory
        auth_client.post('/m/multicurrency/currencies/new/', {
            'code': 'CHF',
            'name': 'Swiss Franc',
            'symbol': 'CHF',
            'decimal_places': 2,
            'exchange_rate': '0.945000',
            'is_active': True,
            'sort_order': 0,
        })
        currency = Currency.objects.get(code='CHF')
        history = ExchangeRateHistory.objects.filter(currency=currency)
        assert history.count() == 1
        assert history.first().source == 'manual'


# ---------------------------------------------------------------------------
# Currency Edit
# ---------------------------------------------------------------------------

class TestCurrencyEdit:

    def test_edit_form_loads(self, auth_client, usd_currency):
        response = auth_client.get(f'/m/multicurrency/currencies/{usd_currency.pk}/edit/')
        assert response.status_code == 200

    def test_edit_form_not_found(self, auth_client):
        fake_uuid = uuid.uuid4()
        response = auth_client.get(f'/m/multicurrency/currencies/{fake_uuid}/edit/')
        assert response.status_code == 200  # Returns error in context

    def test_edit_currency_post(self, auth_client, usd_currency):
        response = auth_client.post(
            f'/m/multicurrency/currencies/{usd_currency.pk}/edit/', {
                'code': 'USD',
                'name': 'US Dollar Updated',
                'symbol': '$',
                'decimal_places': 2,
                'exchange_rate': '1.100000',
                'is_active': True,
                'sort_order': 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        usd_currency.refresh_from_db()
        assert usd_currency.name == 'US Dollar Updated'
        assert usd_currency.exchange_rate == Decimal('1.100000')

    def test_edit_rate_change_records_history(self, auth_client, usd_currency):
        """Changing exchange rate records a history entry."""
        from multicurrency.models import ExchangeRateHistory
        auth_client.post(
            f'/m/multicurrency/currencies/{usd_currency.pk}/edit/', {
                'code': 'USD',
                'name': 'US Dollar',
                'symbol': '$',
                'decimal_places': 2,
                'exchange_rate': '1.200000',
                'is_active': True,
                'sort_order': 1,
            },
        )
        history = ExchangeRateHistory.objects.filter(
            currency=usd_currency, rate=Decimal('1.200000'),
        )
        assert history.exists()


# ---------------------------------------------------------------------------
# Currency Toggle
# ---------------------------------------------------------------------------

class TestCurrencyToggle:

    def test_toggle_active(self, auth_client, usd_currency):
        assert usd_currency.is_active is True
        response = auth_client.post(
            f'/m/multicurrency/currencies/{usd_currency.pk}/toggle/',
        )
        assert response.status_code == 200
        usd_currency.refresh_from_db()
        assert usd_currency.is_active is False

    def test_toggle_inactive(self, auth_client, hub_id):
        from multicurrency.models import Currency
        c = Currency.objects.create(
            hub_id=hub_id, code='NOK', name='Norwegian Krone',
            symbol='kr', is_active=False,
        )
        response = auth_client.post(f'/m/multicurrency/currencies/{c.pk}/toggle/')
        assert response.status_code == 200
        c.refresh_from_db()
        assert c.is_active is True

    def test_toggle_not_found(self, auth_client):
        fake_uuid = uuid.uuid4()
        response = auth_client.post(f'/m/multicurrency/currencies/{fake_uuid}/toggle/')
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Currency Delete
# ---------------------------------------------------------------------------

class TestCurrencyDelete:

    def test_delete_currency(self, auth_client, gbp_currency):
        response = auth_client.post(
            f'/m/multicurrency/currencies/{gbp_currency.pk}/delete/',
        )
        assert response.status_code == 200
        gbp_currency.refresh_from_db()
        assert gbp_currency.is_deleted is True

    def test_delete_not_found(self, auth_client):
        fake_uuid = uuid.uuid4()
        response = auth_client.post(f'/m/multicurrency/currencies/{fake_uuid}/delete/')
        assert response.status_code == 404

    def test_delete_with_payments_fails(self, auth_client, usd_currency, currency_payment):
        response = auth_client.post(
            f'/m/multicurrency/currencies/{usd_currency.pk}/delete/',
        )
        assert response.status_code == 400
        usd_currency.refresh_from_db()
        assert usd_currency.is_deleted is False


# ---------------------------------------------------------------------------
# Update Rates
# ---------------------------------------------------------------------------

class TestUpdateRates:

    def test_update_rates_manual_source(self, auth_client, currency_settings):
        """Manual source returns error."""
        response = auth_client.post('/m/multicurrency/update-rates/')
        assert response.status_code == 400
        data = response.json()
        assert data['ok'] is False

    def test_update_rates_requires_login(self):
        client = Client()
        response = client.post('/m/multicurrency/update-rates/')
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

class TestHistory:

    def test_history_loads(self, auth_client):
        response = auth_client.get('/m/multicurrency/history/')
        assert response.status_code == 200

    def test_history_with_data(self, auth_client, rate_history_entries):
        response = auth_client.get('/m/multicurrency/history/')
        assert response.status_code == 200

    def test_history_htmx(self, auth_client):
        response = auth_client.get('/m/multicurrency/history/', HTTP_HX_REQUEST='true')
        assert response.status_code == 200

    def test_history_filter_by_currency(self, auth_client, rate_history_entries, usd_currency):
        response = auth_client.get('/m/multicurrency/history/?currency=USD')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# API: Convert
# ---------------------------------------------------------------------------

class TestApiConvert:

    def test_convert_usd_to_base(self, auth_client, usd_currency):
        response = auth_client.get('/m/multicurrency/api/convert/?from=USD&to=EUR&amount=108.50')
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['from'] == 'USD'
        assert data['to'] == 'EUR'
        assert Decimal(data['result']) == Decimal('100.00')

    def test_convert_base_to_usd(self, auth_client, usd_currency):
        response = auth_client.get('/m/multicurrency/api/convert/?from=EUR&to=USD&amount=100')
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert Decimal(data['result']) == Decimal('108.50')

    def test_convert_invalid_amount(self, auth_client):
        response = auth_client.get('/m/multicurrency/api/convert/?from=USD&to=EUR&amount=abc')
        assert response.status_code == 400

    def test_convert_missing_params(self, auth_client):
        response = auth_client.get('/m/multicurrency/api/convert/?amount=100')
        assert response.status_code == 400

    def test_convert_unknown_currency(self, auth_client):
        response = auth_client.get('/m/multicurrency/api/convert/?from=XYZ&to=EUR&amount=100')
        assert response.status_code == 404

    def test_convert_requires_login(self):
        client = Client()
        response = client.get('/m/multicurrency/api/convert/?from=USD&to=EUR&amount=100')
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# API: Rates
# ---------------------------------------------------------------------------

class TestApiRates:

    def test_rates_empty(self, auth_client):
        response = auth_client.get('/m/multicurrency/api/rates/')
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert data['base_currency'] == 'EUR'
        assert data['rates'] == []

    def test_rates_with_currencies(self, auth_client, usd_currency, gbp_currency):
        response = auth_client.get('/m/multicurrency/api/rates/')
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True
        assert len(data['rates']) == 2
        codes = [r['code'] for r in data['rates']]
        assert 'USD' in codes
        assert 'GBP' in codes

    def test_rates_structure(self, auth_client, usd_currency):
        response = auth_client.get('/m/multicurrency/api/rates/')
        data = response.json()
        rate = data['rates'][0]
        assert 'code' in rate
        assert 'name' in rate
        assert 'symbol' in rate
        assert 'exchange_rate' in rate
        assert 'decimal_places' in rate
        assert 'last_updated' in rate

    def test_rates_requires_login(self):
        client = Client()
        response = client.get('/m/multicurrency/api/rates/')
        assert response.status_code == 302


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class TestSettingsView:

    def test_settings_loads(self, auth_client):
        response = auth_client.get('/m/multicurrency/settings/')
        assert response.status_code == 200

    def test_settings_htmx(self, auth_client):
        response = auth_client.get('/m/multicurrency/settings/', HTTP_HX_REQUEST='true')
        assert response.status_code == 200

    def test_settings_save(self, auth_client):
        from multicurrency.models import CurrencySettings
        response = auth_client.post('/m/multicurrency/settings/save/', {
            'base_currency': 'USD',
            'auto_update_rates': False,
            'update_frequency': 'weekly',
            'rate_source': 'manual',
            'api_key': '',
            'round_to_decimals': 4,
            'show_both_currencies': True,
            'allow_multi_currency_payment': False,
        })
        assert response.status_code == 200
        data = response.json()
        assert data['ok'] is True

        settings_obj = CurrencySettings.objects.first()
        assert settings_obj.base_currency == 'USD'
        assert settings_obj.round_to_decimals == 4
        assert settings_obj.allow_multi_currency_payment is False

    def test_settings_save_requires_login(self):
        client = Client()
        response = client.post('/m/multicurrency/settings/save/', {})
        assert response.status_code == 302
