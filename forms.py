"""Multi-currency forms."""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Currency, CurrencySettings


class CurrencyForm(forms.ModelForm):
    class Meta:
        model = Currency
        fields = [
            'code', 'name', 'symbol', 'decimal_places',
            'exchange_rate', 'is_active', 'sort_order',
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'input', 'maxlength': '3',
                'style': 'text-transform:uppercase',
                'placeholder': 'USD',
            }),
            'name': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': _('US Dollar'),
            }),
            'symbol': forms.TextInput(attrs={
                'class': 'input', 'maxlength': '10',
                'placeholder': '$',
            }),
            'decimal_places': forms.NumberInput(attrs={
                'class': 'input', 'min': '0', 'max': '6',
            }),
            'exchange_rate': forms.NumberInput(attrs={
                'class': 'input', 'step': '0.000001', 'min': '0',
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'toggle'}),
            'sort_order': forms.NumberInput(attrs={
                'class': 'input', 'min': '0',
            }),
        }


class CurrencySettingsForm(forms.ModelForm):
    class Meta:
        model = CurrencySettings
        fields = [
            'base_currency', 'auto_update_rates', 'update_frequency',
            'rate_source', 'api_key', 'round_to_decimals',
            'show_both_currencies', 'allow_multi_currency_payment',
        ]
        widgets = {
            'base_currency': forms.TextInput(attrs={
                'class': 'input', 'maxlength': '3',
                'style': 'text-transform:uppercase',
                'placeholder': 'EUR',
            }),
            'auto_update_rates': forms.CheckboxInput(attrs={'class': 'toggle'}),
            'update_frequency': forms.Select(attrs={'class': 'select'}),
            'rate_source': forms.Select(attrs={'class': 'select'}),
            'api_key': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': _('Enter API key'),
            }),
            'round_to_decimals': forms.NumberInput(attrs={
                'class': 'input', 'min': '0', 'max': '6',
            }),
            'show_both_currencies': forms.CheckboxInput(attrs={'class': 'toggle'}),
            'allow_multi_currency_payment': forms.CheckboxInput(attrs={'class': 'toggle'}),
        }
