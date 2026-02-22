from django.utils.translation import gettext_lazy as _

MODULE_ID = 'multicurrency'
MODULE_NAME = _('Multi-Currency')
MODULE_VERSION = '1.0.0'
MODULE_ICON = 'cash-outline'
MODULE_DESCRIPTION = _('Multi-currency support with exchange rates for POS')
MODULE_AUTHOR = 'ERPlora'
MODULE_CATEGORY = 'pos'

MENU = {
    'label': _('Currencies'),
    'icon': 'cash-outline',
    'order': 88,
}

NAVIGATION = [
    {'label': _('Exchange Rates'), 'icon': 'swap-horizontal-outline', 'id': 'dashboard'},
    {'label': _('Currencies'), 'icon': 'cash-outline', 'id': 'currencies'},
    {'label': _('History'), 'icon': 'time-outline', 'id': 'history'},
    {'label': _('Settings'), 'icon': 'settings-outline', 'id': 'settings'},
]

DEPENDENCIES = []

PERMISSIONS = [
    'multicurrency.view_currency',
    'multicurrency.add_currency',
    'multicurrency.change_currency',
    'multicurrency.delete_currency',
    'multicurrency.update_rates',
    'multicurrency.manage_settings',
]
