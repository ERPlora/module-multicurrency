"""
Unit tests for Multi-currency models.
"""

import pytest
from decimal import Decimal
from django.utils import timezone


pytestmark = [pytest.mark.django_db, pytest.mark.unit]


# ---------------------------------------------------------------------------
# CurrencySettings
# ---------------------------------------------------------------------------

class TestCurrencySettings:
    """Tests for CurrencySettings model."""

    def test_get_settings_creates(self, hub_id):
        from multicurrency.models import CurrencySettings
        s = CurrencySettings.get_settings(hub_id)
        assert s is not None
        assert s.hub_id == hub_id

    def test_get_settings_returns_existing(self, hub_id):
        from multicurrency.models import CurrencySettings
        s1 = CurrencySettings.get_settings(hub_id)
        s2 = CurrencySettings.get_settings(hub_id)
        assert s1.pk == s2.pk

    def test_default_values(self, hub_id):
        from multicurrency.models import CurrencySettings
        s = CurrencySettings.get_settings(hub_id)
        assert s.base_currency == 'EUR'
        assert s.auto_update_rates is False
        assert s.update_frequency == 'daily'
        assert s.rate_source == 'manual'
        assert s.api_key == ''
        assert s.round_to_decimals == 2
        assert s.show_both_currencies is True
        assert s.allow_multi_currency_payment is True

    def test_str(self, hub_id):
        from multicurrency.models import CurrencySettings
        s = CurrencySettings.get_settings(hub_id)
        assert 'Currency Settings' in str(s)

    def test_update_settings(self, hub_id):
        from multicurrency.models import CurrencySettings
        s = CurrencySettings.get_settings(hub_id)
        s.base_currency = 'USD'
        s.auto_update_rates = True
        s.update_frequency = 'hourly'
        s.rate_source = 'ecb'
        s.save()

        refreshed = CurrencySettings.get_settings(hub_id)
        assert refreshed.base_currency == 'USD'
        assert refreshed.auto_update_rates is True
        assert refreshed.update_frequency == 'hourly'
        assert refreshed.rate_source == 'ecb'

    def test_singleton_per_hub(self, hub_id):
        """unique_together on hub_id ensures one settings per hub."""
        from multicurrency.models import CurrencySettings
        unique = CurrencySettings._meta.unique_together
        assert ('hub_id',) in unique


# ---------------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------------

class TestCurrency:
    """Tests for Currency model."""

    def test_create(self, usd_currency):
        assert usd_currency.code == 'USD'
        assert usd_currency.name == 'US Dollar'
        assert usd_currency.symbol == '$'
        assert usd_currency.decimal_places == 2
        assert usd_currency.exchange_rate == Decimal('1.085000')
        assert usd_currency.is_active is True

    def test_str(self, usd_currency):
        assert str(usd_currency) == 'USD - US Dollar'

    def test_unique_code_per_hub(self, hub_id, usd_currency):
        """Cannot create two currencies with same code for same hub."""
        from multicurrency.models import Currency
        unique = Currency._meta.unique_together
        assert ('hub_id', 'code') in unique

    def test_ordering_by_sort_order_then_code(self, hub_id, eur_currency, usd_currency, gbp_currency):
        from multicurrency.models import Currency
        currencies = list(Currency.objects.filter(hub_id=hub_id))
        codes = [c.code for c in currencies]
        # EUR (0), USD (1), GBP (2) by sort_order
        assert codes == ['EUR', 'USD', 'GBP']

    def test_convert_from_base(self, usd_currency):
        """1 EUR = 1.085 USD, so 100 EUR = 108.50 USD."""
        result = usd_currency.convert_from_base(Decimal('100'))
        assert result == Decimal('108.50')

    def test_convert_to_base(self, usd_currency):
        """108.50 USD = 100.00 EUR."""
        result = usd_currency.convert_to_base(Decimal('108.50'))
        assert result == Decimal('100.00')

    def test_convert_from_base_gbp(self, gbp_currency):
        """1 EUR = 0.856 GBP, so 100 EUR = 85.60 GBP."""
        result = gbp_currency.convert_from_base(Decimal('100'))
        assert result == Decimal('85.60')

    def test_convert_to_base_gbp(self, gbp_currency):
        """85.60 GBP -> EUR (85.60 / 0.856 = 100)."""
        result = gbp_currency.convert_to_base(Decimal('85.60'))
        assert result == Decimal('100.00')

    def test_convert_zero_rate(self, hub_id):
        """Zero exchange rate returns 0."""
        from multicurrency.models import Currency
        c = Currency.objects.create(
            hub_id=hub_id, code='XXX', name='Zero',
            symbol='X', exchange_rate=Decimal('0'),
        )
        assert c.convert_from_base(Decimal('100')) == Decimal('0')
        assert c.convert_to_base(Decimal('100')) == Decimal('0')

    def test_exchange_rate_precision(self, hub_id):
        """Exchange rate supports 6 decimal places."""
        from multicurrency.models import Currency
        c = Currency.objects.create(
            hub_id=hub_id, code='JPY', name='Japanese Yen',
            symbol='\u00a5', decimal_places=0,
            exchange_rate=Decimal('163.456789'),
        )
        c.refresh_from_db()
        assert c.exchange_rate == Decimal('163.456789')

    def test_soft_delete(self, usd_currency):
        from multicurrency.models import Currency
        usd_currency.delete()
        assert usd_currency.is_deleted is True
        assert Currency.objects.filter(pk=usd_currency.pk).count() == 0
        assert Currency.all_objects.filter(pk=usd_currency.pk).count() == 1

    def test_convert_from_base_rounds_to_decimal_places(self, hub_id):
        """Conversion rounds to the currency's decimal_places."""
        from multicurrency.models import Currency
        c = Currency.objects.create(
            hub_id=hub_id, code='JPY', name='Japanese Yen',
            symbol='\u00a5', decimal_places=0,
            exchange_rate=Decimal('163.456789'),
        )
        result = c.convert_from_base(Decimal('1'))
        # Should round to 0 decimal places
        assert result == Decimal('163')


# ---------------------------------------------------------------------------
# ExchangeRateHistory
# ---------------------------------------------------------------------------

class TestExchangeRateHistory:
    """Tests for ExchangeRateHistory model."""

    def test_create(self, hub_id, usd_currency):
        from multicurrency.models import ExchangeRateHistory
        entry = ExchangeRateHistory.objects.create(
            hub_id=hub_id,
            currency=usd_currency,
            rate=Decimal('1.090000'),
            source='manual',
        )
        assert entry.rate == Decimal('1.090000')
        assert entry.source == 'manual'
        assert entry.recorded_at is not None

    def test_ordering_newest_first(self, rate_history_entries):
        from multicurrency.models import ExchangeRateHistory
        entries = list(ExchangeRateHistory.objects.all())
        # Most recent should be first
        for i in range(len(entries) - 1):
            assert entries[i].recorded_at >= entries[i + 1].recorded_at

    def test_str(self, hub_id, usd_currency):
        from multicurrency.models import ExchangeRateHistory
        entry = ExchangeRateHistory.objects.create(
            hub_id=hub_id,
            currency=usd_currency,
            rate=Decimal('1.090000'),
            source='ecb',
        )
        result = str(entry)
        assert 'USD' in result
        assert '1.090000' in result
        assert 'ecb' in result

    def test_cascade_delete_with_currency(self, hub_id, usd_currency):
        """Deleting a currency hard-deletes its rate history."""
        from multicurrency.models import ExchangeRateHistory
        ExchangeRateHistory.objects.create(
            hub_id=hub_id, currency=usd_currency,
            rate=Decimal('1.085000'), source='manual',
        )
        assert ExchangeRateHistory.all_objects.filter(currency=usd_currency).count() >= 1
        usd_currency.delete(hard_delete=True)
        assert ExchangeRateHistory.all_objects.filter(currency=usd_currency).count() == 0

    def test_rate_precision(self, hub_id, usd_currency):
        """Rate supports 6 decimal places."""
        from multicurrency.models import ExchangeRateHistory
        entry = ExchangeRateHistory.objects.create(
            hub_id=hub_id,
            currency=usd_currency,
            rate=Decimal('1.123456'),
            source='api',
        )
        entry.refresh_from_db()
        assert entry.rate == Decimal('1.123456')

    def test_index_exists(self):
        from multicurrency.models import ExchangeRateHistory
        index_fields = [idx.fields for idx in ExchangeRateHistory._meta.indexes]
        assert ['currency', '-recorded_at'] in index_fields


# ---------------------------------------------------------------------------
# CurrencyPayment
# ---------------------------------------------------------------------------

class TestCurrencyPayment:
    """Tests for CurrencyPayment model."""

    def test_create(self, currency_payment, usd_currency):
        assert currency_payment.original_amount == Decimal('108.50')
        assert currency_payment.exchange_rate_used == Decimal('1.085000')
        assert currency_payment.base_amount == Decimal('100.00')
        assert currency_payment.currency == usd_currency
        assert currency_payment.payment_date is not None

    def test_str(self, currency_payment):
        result = str(currency_payment)
        assert '108.50' in result
        assert 'USD' in result
        assert '100.00' in result

    def test_ordering_newest_first(self, hub_id, usd_currency):
        from multicurrency.models import CurrencyPayment
        p1 = CurrencyPayment.objects.create(
            hub_id=hub_id, currency=usd_currency,
            original_amount=Decimal('50.00'),
            exchange_rate_used=Decimal('1.085000'),
            base_amount=Decimal('46.08'),
        )
        p2 = CurrencyPayment.objects.create(
            hub_id=hub_id, currency=usd_currency,
            original_amount=Decimal('100.00'),
            exchange_rate_used=Decimal('1.085000'),
            base_amount=Decimal('92.17'),
        )
        payments = list(CurrencyPayment.objects.filter(hub_id=hub_id))
        assert payments[0].pk == p2.pk

    def test_currency_set_null_on_delete(self, hub_id, currency_payment, usd_currency):
        """Currency FK is SET_NULL when currency is hard-deleted."""
        from multicurrency.models import CurrencyPayment
        usd_currency.delete(hard_delete=True)
        currency_payment.refresh_from_db()
        assert currency_payment.currency is None
        # Payment still exists
        assert CurrencyPayment.objects.filter(pk=currency_payment.pk).exists()

    def test_sale_id_optional(self, hub_id, usd_currency):
        """sale_id is optional (null=True)."""
        from multicurrency.models import CurrencyPayment
        p = CurrencyPayment.objects.create(
            hub_id=hub_id, currency=usd_currency,
            original_amount=Decimal('50.00'),
            exchange_rate_used=Decimal('1.085000'),
            base_amount=Decimal('46.08'),
            sale_id=None,
        )
        assert p.sale_id is None

    def test_soft_delete(self, currency_payment):
        from multicurrency.models import CurrencyPayment
        currency_payment.delete()
        assert currency_payment.is_deleted is True
        assert CurrencyPayment.objects.filter(pk=currency_payment.pk).count() == 0
        assert CurrencyPayment.all_objects.filter(pk=currency_payment.pk).count() == 1
