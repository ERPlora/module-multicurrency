"""Multi-currency URL Configuration."""

from django.urls import path
from . import views

app_name = 'multicurrency'

urlpatterns = [
    # Dashboard (Exchange Rates)
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('update-rates/', views.update_rates, name='update_rates'),

    # Currencies CRUD
    path('currencies/', views.currencies, name='currencies'),
    path('currencies/new/', views.currency_create, name='currency_create'),
    path('currencies/<uuid:pk>/edit/', views.currency_edit, name='currency_edit'),
    path('currencies/<uuid:pk>/delete/', views.currency_delete, name='currency_delete'),
    path('currencies/<uuid:pk>/toggle/', views.currency_toggle, name='currency_toggle'),

    # History
    path('history/', views.history, name='history'),

    # API
    path('api/convert/', views.api_convert, name='api_convert'),
    path('api/rates/', views.api_rates, name='api_rates'),

    # Settings
    path('settings/', views.settings_view, name='settings'),
    path('settings/save/', views.settings_save, name='settings_save'),
]
