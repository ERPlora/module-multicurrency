# Multi-Currency Module

Multi-currency support with exchange rates for POS transactions.

## Features

- Define and manage multiple currencies with ISO 4217 codes
- Automatic or manual exchange rate updates from ECB or ExchangeRate API
- Configurable update frequency (hourly, daily, weekly)
- Full exchange rate history tracking with source logging
- Currency conversion helpers (to/from base currency)
- Foreign currency payment records linked to sales
- Display both base and foreign currency on receipts
- Configurable decimal rounding precision

## Installation

This module is installed automatically via the ERPlora Marketplace.

## Configuration

Access settings via: **Menu > Currencies > Settings**

Configure the base currency (ISO 4217 code), rate source (Manual, European Central Bank, or ExchangeRate API), update frequency, rounding decimals, and whether to show both currencies on receipts.

## Usage

Access via: **Menu > Currencies**

### Views

| View | URL | Description |
|------|-----|-------------|
| Exchange Rates | `/m/multicurrency/dashboard/` | Current exchange rates overview |
| Currencies | `/m/multicurrency/currencies/` | Manage available currencies |
| History | `/m/multicurrency/history/` | Exchange rate change log |
| Settings | `/m/multicurrency/settings/` | Module configuration |

## Models

| Model | Description |
|-------|-------------|
| `CurrencySettings` | Per-hub singleton with base currency, rate source, update frequency, and display options |
| `Currency` | Available currency with ISO code, symbol, exchange rate, decimal places, and sort order |
| `ExchangeRateHistory` | Historical log of exchange rate changes with source and timestamp |
| `CurrencyPayment` | Foreign currency payment linked to a sale with original amount, rate used, and base conversion |

## Permissions

| Permission | Description |
|------------|-------------|
| `multicurrency.view_currency` | View currencies and exchange rates |
| `multicurrency.add_currency` | Add new currencies |
| `multicurrency.change_currency` | Edit currency details and rates |
| `multicurrency.delete_currency` | Remove currencies |
| `multicurrency.update_rates` | Trigger exchange rate updates |
| `multicurrency.manage_settings` | Access and modify module settings |

## License

MIT

## Author

ERPlora Team - support@erplora.com
