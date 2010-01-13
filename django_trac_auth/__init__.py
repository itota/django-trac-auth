from django.conf import settings

# for ReviewBoard
try:
    import settings_local as _settings
    settings.TRAC_HTPASSWD = getattr(_settings, 'TRAC_HTPASSWD', '')
    settings.TRAC_HTGROUP = getattr(_settings, 'TRAC_HTGROUP', '')
    settings.TRAC_ENV = getattr(_settings, 'TRAC_ENV', '')
    settings.TRAC_STORE_PASSWORD= getattr(_settings, 'TRAC_STORE_PASSWORD', False)
except:
    pass

