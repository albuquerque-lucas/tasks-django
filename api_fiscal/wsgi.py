"""
WSGI config for api_fiscal project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api_fiscal.settings')

application = get_wsgi_application()
