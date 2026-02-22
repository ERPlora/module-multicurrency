from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MulticurrencyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'multicurrency'
    label = 'multicurrency'
    verbose_name = _('Multi-Currency')

    def ready(self):
        pass
