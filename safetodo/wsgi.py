"""
WSGI config for safetodo project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safetodo.settings')

application = get_wsgi_application()
