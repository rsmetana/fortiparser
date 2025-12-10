"""
WSGI config for hfw project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys

path = '/home/rsmetana/fortiparser/hfw'
if path not in sys.path:
    sys.path.append(path)

site_packages_path = '/home/rsmetana/fortiparser/.hfw/lib/python3.12/site-packages'
if site_packages_path not in sys.path:
    sys.path.append(site_packages_path)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hfw.settings')

application = get_wsgi_application()
