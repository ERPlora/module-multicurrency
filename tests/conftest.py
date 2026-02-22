"""
Fixtures for multicurrency tests.
"""

import os
import pytest
from decimal import Decimal
from django.test import Client
from django.utils import timezone


os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'


# ---------------------------------------------------------------------------
# Hub & Auth Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _set_hub_config(db, settings):
    """Ensure HubConfig + StoreConfig exist so middleware won't redirect."""
    from apps.configuration.models import HubConfig, StoreConfig
    config = HubConfig.get_solo()
    config.save()
    store = StoreConfig.get_solo()
    store.business_name = 'Test Business'
    store.is_configured = True
    store.save()


@pytest.fixture
def hub_id(db):
    from apps.configuration.models import HubConfig
    return HubConfig.get_solo().hub_id


@pytest.fixture
def employee(db):
    """Create a local user (employee)."""
    from apps.accounts.models import LocalUser
    return LocalUser.objects.create(
        name='Test Employee',
        email='employee@test.com',
        role='admin',
        is_active=True,
    )


@pytest.fixture
def auth_client(employee):
    """Authenticated Django test client."""
    client = Client()
    session = client.session
    session['local_user_id'] = str(employee.id)
    session['user_name'] = employee.name
    session['user_email'] = employee.email
    session['user_role'] = employee.role
    session['store_config_checked'] = True
    session.save()
    return client


# ---------------------------------------------------------------------------
# Model Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def currency_settings(hub_id):
    """Create currency settings."""
    from multicurrency.models import CurrencySettings
    return CurrencySettings.get_settings(hub_id)


@pytest.fixture
def eur_currency(hub_id):
    """EUR currency (base)."""
    from multicurrency.models import Currency
    return Currency.objects.create(
        hub_id=hub_id,
        code='EUR',
        name='Euro',
        symbol='\u20ac',
        decimal_places=2,
        exchange_rate=Decimal('1.000000'),
        is_active=True,
        last_updated=timezone.now(),
        sort_order=0,
    )


@pytest.fixture
def usd_currency(hub_id):
    """USD currency."""
    from multicurrency.models import Currency
    return Currency.objects.create(
        hub_id=hub_id,
        code='USD',
        name='US Dollar',
        symbol='$',
        decimal_places=2,
        exchange_rate=Decimal('1.085000'),
        is_active=True,
        last_updated=timezone.now(),
        sort_order=1,
    )


@pytest.fixture
def gbp_currency(hub_id):
    """GBP currency."""
    from multicurrency.models import Currency
    return Currency.objects.create(
        hub_id=hub_id,
        code='GBP',
        name='British Pound',
        symbol='\u00a3',
        decimal_places=2,
        exchange_rate=Decimal('0.856000'),
        is_active=True,
        last_updated=timezone.now(),
        sort_order=2,
    )


@pytest.fixture
def rate_history_entries(hub_id, usd_currency):
    """Create rate history entries for USD."""
    from multicurrency.models import ExchangeRateHistory
    entries = []
    rates = [
        Decimal('1.080000'),
        Decimal('1.082000'),
        Decimal('1.085000'),
    ]
    for rate in rates:
        entry = ExchangeRateHistory.objects.create(
            hub_id=hub_id,
            currency=usd_currency,
            rate=rate,
            source='manual',
        )
        entries.append(entry)
    return entries


@pytest.fixture
def currency_payment(hub_id, usd_currency):
    """Create a currency payment."""
    from multicurrency.models import CurrencyPayment
    return CurrencyPayment.objects.create(
        hub_id=hub_id,
        currency=usd_currency,
        original_amount=Decimal('108.50'),
        exchange_rate_used=Decimal('1.085000'),
        base_amount=Decimal('100.00'),
    )
