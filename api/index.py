"""
Vercel Serverless Function for Django
Note: Requires external PostgreSQL database for data persistence
"""
import os
import sys
from pathlib import Path

# Add project to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RemindHer.settings')

def handler(request, context):
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
    return application(request, context)