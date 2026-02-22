"""Multi-currency models."""

from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import HubBaseModel


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

class CurrencySettings(HubBaseModel):
    """Per-hub multi-currency configuration."""

    class UpdateFrequency(models.TextChoices):
        HOURLY = 'hourly', _('Hourly')
        DAILY = 'daily', _('Daily')
        WEEKLY = 'weekly', _('Weekly')

    class RateSource(models.TextChoices):
        MANUAL = 'manual', _('Manual')
        ECB = 'ecb', _('European Central Bank')
        EXCHANGERATE_API = 'exchangerate_api', _('ExchangeRate API')

    base_currency = models.CharField(
        _('Base Currency'), max_length=3, default='EUR',
        help_text=_('ISO 4217 code for the base currency'),
    )
    auto_update_rates = models.BooleanField(
        _('Auto-update Rates'), default=False,
    )
    update_frequency = models.CharField(
        _('Update Frequency'), max_length=10,
        choices=UpdateFrequency.choices, default=UpdateFrequency.DAILY,
    )
    rate_source = models.CharField(
        _('Rate Source'), max_length=20,
        choices=RateSource.choices, default=RateSource.MANUAL,
    )
    api_key = models.CharField(
        _('API Key'), max_length=255, blank=True,
        help_text=_('API key for the exchange rate provider'),
    )
    round_to_decimals = models.IntegerField(
        _('Round to Decimals'), default=2,
    )
    show_both_currencies = models.BooleanField(
        _('Show Both Currencies'), default=True,
        help_text=_('Show base + foreign currency on receipt'),
    )
    allow_multi_currency_payment = models.BooleanField(
        _('Allow Multi-Currency Payment'), default=True,
    )

    class Meta(HubBaseModel.Meta):
        db_table = 'multicurrency_settings'
        verbose_name = _('Currency Settings')
        verbose_name_plural = _('Currency Settings')
        unique_together = [('hub_id',)]

    def __str__(self):
        return f'Currency Settings (hub={self.hub_id})'

    @classmethod
    def get_settings(cls, hub_id):
        obj, _ = cls.all_objects.get_or_create(hub_id=hub_id)
        return obj


# ---------------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------------

class Currency(HubBaseModel):
    """Available currencies for the hub."""

    code = models.CharField(
        _('Currency Code'), max_length=3,
        help_text=_('ISO 4217 code, e.g. USD'),
    )
    name = models.CharField(_('Name'), max_length=100)
    symbol = models.CharField(_('Symbol'), max_length=10)
    decimal_places = models.IntegerField(
        _('Decimal Places'), default=2,
    )
    exchange_rate = models.DecimalField(
        _('Exchange Rate'), max_digits=12, decimal_places=6,
        default=Decimal('1.000000'),
        help_text=_('Rate vs base currency'),
    )
    is_active = models.BooleanField(_('Active'), default=True)
    last_updated = models.DateTimeField(
        _('Last Updated'), null=True, blank=True,
    )
    sort_order = models.PositiveIntegerField(
        _('Sort Order'), default=0,
    )

    class Meta(HubBaseModel.Meta):
        db_table = 'multicurrency_currency'
        verbose_name = _('Currency')
        verbose_name_plural = _('Currencies')
        unique_together = [('hub_id', 'code')]
        ordering = ['sort_order', 'code']

    def __str__(self):
        return f'{self.code} - {self.name}'

    def convert_from_base(self, amount):
        """Convert an amount from base currency to this currency."""
        if self.exchange_rate == 0:
            return Decimal('0')
        result = Decimal(str(amount)) * self.exchange_rate
        return result.quantize(
            Decimal(10) ** -self.decimal_places,
            rounding=ROUND_HALF_UP,
        )

    def convert_to_base(self, amount):
        """Convert an amount from this currency to the base currency."""
        if self.exchange_rate == 0:
            return Decimal('0')
        result = Decimal(str(amount)) / self.exchange_rate
        return result.quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP,
        )


# ---------------------------------------------------------------------------
# Exchange Rate History
# ---------------------------------------------------------------------------

class ExchangeRateHistory(HubBaseModel):
    """Rate change log for currencies."""

    currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE,
        related_name='rate_history',
        verbose_name=_('Currency'),
    )
    rate = models.DecimalField(
        _('Exchange Rate'), max_digits=12, decimal_places=6,
    )
    source = models.CharField(
        _('Source'), max_length=50,
        help_text=_('manual/ecb/api'),
    )
    recorded_at = models.DateTimeField(
        _('Recorded At'), auto_now_add=True,
    )

    class Meta(HubBaseModel.Meta):
        db_table = 'multicurrency_rate_history'
        verbose_name = _('Exchange Rate History')
        verbose_name_plural = _('Exchange Rate History')
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['currency', '-recorded_at']),
        ]

    def __str__(self):
        return f'{self.currency.code}: {self.rate} ({self.source})'


# ---------------------------------------------------------------------------
# Currency Payment
# ---------------------------------------------------------------------------

class CurrencyPayment(HubBaseModel):
    """Payment in foreign currency linked to a sale."""

    sale_id = models.UUIDField(
        _('Sale'), null=True, blank=True,
        help_text=_('FK to sale'),
    )
    currency = models.ForeignKey(
        Currency, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payments',
        verbose_name=_('Currency'),
    )
    original_amount = models.DecimalField(
        _('Original Amount'), max_digits=10, decimal_places=2,
        help_text=_('Amount in foreign currency'),
    )
    exchange_rate_used = models.DecimalField(
        _('Exchange Rate Used'), max_digits=12, decimal_places=6,
    )
    base_amount = models.DecimalField(
        _('Base Amount'), max_digits=10, decimal_places=2,
        help_text=_('Converted to base currency'),
    )
    payment_date = models.DateTimeField(
        _('Payment Date'), auto_now_add=True,
    )

    class Meta(HubBaseModel.Meta):
        db_table = 'multicurrency_payment'
        verbose_name = _('Currency Payment')
        verbose_name_plural = _('Currency Payments')
        ordering = ['-payment_date']

    def __str__(self):
        currency_code = self.currency.code if self.currency else '???'
        return f'{self.original_amount} {currency_code} = {self.base_amount} base'
