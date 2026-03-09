# Multi-Currency

## Overview

| Property | Value |
|----------|-------|
| **Module ID** | `multicurrency` |
| **Version** | `1.0.0` |
| **Icon** | `cash-outline` |
| **Dependencies** | None |

## Models

### `CurrencySettings`

Per-hub multi-currency configuration.

| Field | Type | Details |
|-------|------|---------|
| `base_currency` | CharField | max_length=3 |
| `auto_update_rates` | BooleanField |  |
| `update_frequency` | CharField | max_length=10, choices: hourly, daily, weekly |
| `rate_source` | CharField | max_length=20, choices: manual, ecb, exchangerate_api |
| `api_key` | CharField | max_length=255, optional |
| `round_to_decimals` | IntegerField |  |
| `show_both_currencies` | BooleanField |  |
| `allow_multi_currency_payment` | BooleanField |  |

**Methods:**

- `get_settings()`

### `Currency`

Available currencies for the hub.

| Field | Type | Details |
|-------|------|---------|
| `code` | CharField | max_length=3 |
| `name` | CharField | max_length=100 |
| `symbol` | CharField | max_length=10 |
| `decimal_places` | IntegerField |  |
| `exchange_rate` | DecimalField |  |
| `is_active` | BooleanField |  |
| `last_updated` | DateTimeField | optional |
| `sort_order` | PositiveIntegerField |  |

**Methods:**

- `convert_from_base()` — Convert an amount from base currency to this currency.
- `convert_to_base()` — Convert an amount from this currency to the base currency.

### `ExchangeRateHistory`

Rate change log for currencies.

| Field | Type | Details |
|-------|------|---------|
| `currency` | ForeignKey | → `multicurrency.Currency`, on_delete=CASCADE |
| `rate` | DecimalField |  |
| `source` | CharField | max_length=50 |
| `recorded_at` | DateTimeField | optional |

### `CurrencyPayment`

Payment in foreign currency linked to a sale.

| Field | Type | Details |
|-------|------|---------|
| `sale_id` | UUIDField | max_length=32, optional |
| `currency` | ForeignKey | → `multicurrency.Currency`, on_delete=SET_NULL, optional |
| `original_amount` | DecimalField |  |
| `exchange_rate_used` | DecimalField |  |
| `base_amount` | DecimalField |  |
| `payment_date` | DateTimeField | optional |

## Cross-Module Relationships

| From | Field | To | on_delete | Nullable |
|------|-------|----|-----------|----------|
| `ExchangeRateHistory` | `currency` | `multicurrency.Currency` | CASCADE | No |
| `CurrencyPayment` | `currency` | `multicurrency.Currency` | SET_NULL | Yes |

## URL Endpoints

Base path: `/m/multicurrency/`

| Path | Name | Method |
|------|------|--------|
| `(root)` | `index` | GET |
| `dashboard/` | `dashboard` | GET |
| `update-rates/` | `update_rates` | GET/POST |
| `currencies/` | `currencies` | GET |
| `currencies/new/` | `currency_create` | GET/POST |
| `currencies/<uuid:pk>/edit/` | `currency_edit` | GET |
| `currencies/<uuid:pk>/delete/` | `currency_delete` | GET/POST |
| `currencies/<uuid:pk>/toggle/` | `currency_toggle` | GET |
| `history/` | `history` | GET |
| `api/convert/` | `api_convert` | GET |
| `api/rates/` | `api_rates` | GET |
| `settings/` | `settings` | GET |
| `settings/save/` | `settings_save` | GET/POST |

## Permissions

| Permission | Description |
|------------|-------------|
| `multicurrency.view_currency` | View Currency |
| `multicurrency.add_currency` | Add Currency |
| `multicurrency.change_currency` | Change Currency |
| `multicurrency.delete_currency` | Delete Currency |
| `multicurrency.update_rates` | Update Rates |
| `multicurrency.manage_settings` | Manage Settings |

**Role assignments:**

- **admin**: All permissions
- **manager**: `add_currency`, `change_currency`, `update_rates`, `view_currency`
- **employee**: `add_currency`, `view_currency`

## Navigation

| View | Icon | ID | Fullpage |
|------|------|----|----------|
| Exchange Rates | `swap-horizontal-outline` | `dashboard` | No |
| Currencies | `cash-outline` | `currencies` | No |
| History | `time-outline` | `history` | No |
| Settings | `settings-outline` | `settings` | No |

## AI Tools

Tools available for the AI assistant:

### `list_currencies`

List configured currencies with exchange rates.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `active_only` | boolean | No | Only show active currencies |

### `convert_currency`

Convert an amount between currencies using current exchange rates.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `amount` | string | Yes | Amount to convert |
| `from_currency` | string | Yes | Source currency code (e.g. EUR) |
| `to_currency` | string | Yes | Target currency code (e.g. USD) |

### `add_currency`

Add a new currency with exchange rate.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `code` | string | Yes | Currency code (e.g. USD, GBP) |
| `name` | string | Yes | Currency name |
| `symbol` | string | Yes | Currency symbol (e.g. $, £) |
| `exchange_rate` | string | Yes | Exchange rate relative to base currency |
| `decimal_places` | integer | No | Decimal places (default: 2) |

### `update_exchange_rate`

Update the exchange rate for a currency.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `currency_code` | string | Yes | Currency code (e.g. USD) |
| `exchange_rate` | string | Yes | New exchange rate |

## File Structure

```
README.md
__init__.py
ai_tools.py
apps.py
forms.py
locale/
  en/
    LC_MESSAGES/
      django.po
  es/
    LC_MESSAGES/
      django.po
migrations/
  0001_initial.py
  __init__.py
models.py
module.py
templates/
  multicurrency/
    pages/
      currencies.html
      currency_form.html
      dashboard.html
      history.html
      settings.html
    partials/
      currencies_content.html
      currencies_table.html
      currency_form_content.html
      dashboard_content.html
      history_content.html
      settings_content.html
tests/
  __init__.py
  conftest.py
  test_models.py
  test_views.py
urls.py
views.py
```
