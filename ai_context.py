"""
AI context for the Multicurrency module.
Loaded into the assistant system prompt when this module's tools are active.
"""

CONTEXT = """
## Module Knowledge: Multicurrency

### Models

**CurrencySettings** (singleton per hub)
- `base_currency` (CharField, default `EUR`): ISO 4217 base currency code
- `auto_update_rates` (bool, default False)
- `update_frequency`: `hourly`, `daily`, `weekly`
- `rate_source`: `manual`, `ecb` (European Central Bank), `exchangerate_api`
- `api_key`: for exchangerate_api provider
- `round_to_decimals` (int, default 2)
- `show_both_currencies` (bool, default True): show base + foreign on receipts
- `allow_multi_currency_payment` (bool, default True)
- Access via `CurrencySettings.get_settings(hub_id)`

**Currency**
- `code` (CharField, max 3): ISO 4217, e.g. `USD`, `GBP`, `JPY` — unique per hub
- `name` (CharField): full name, e.g. "US Dollar"
- `symbol` (CharField): e.g. `$`, `£`, `¥`
- `decimal_places` (int, default 2): some currencies use 0 (JPY) or 3 (KWD)
- `exchange_rate` (Decimal 12,6): rate vs base currency (base = 1.0)
- `is_active` (bool), `sort_order` (int), `last_updated` (DateTimeField)
- `convert_from_base(amount)`: base → this currency
- `convert_to_base(amount)`: this currency → base

**ExchangeRateHistory**
- `currency` (FK Currency, related_name `rate_history`)
- `rate` (Decimal 12,6): historical rate recorded
- `source` (CharField): `manual`, `ecb`, `api`
- `recorded_at` (DateTimeField): auto-set

**CurrencyPayment**
- `sale_id` (UUIDField, nullable): FK-like reference to a sale
- `currency` (FK Currency, nullable)
- `original_amount` (Decimal): amount in foreign currency
- `exchange_rate_used` (Decimal 12,6): rate at time of payment
- `base_amount` (Decimal): converted to base currency
- `payment_date` (DateTimeField): auto-set

### Key flows

**Add a foreign currency:**
1. Create `Currency` with code, name, symbol, exchange_rate vs base
2. Rate stored as: 1 base_currency = `exchange_rate` foreign_currency

**Process a foreign currency payment:**
1. Get `Currency` for the foreign currency
2. Use `currency.convert_to_base(amount)` to get base amount
3. Create `CurrencyPayment` recording original, rate, and base amounts

**Update exchange rates:**
- Manual: update `Currency.exchange_rate`, create `ExchangeRateHistory` entry
- Auto: triggered by scheduler based on `update_frequency` and `rate_source`

### Relationships
- Currency → ExchangeRateHistory (one-to-many, related_name `rate_history`)
- Currency → CurrencyPayment (one-to-many, related_name `payments`)
- CurrencyPayment.sale_id is a UUID reference (no enforced FK) to sales.Sale
"""
