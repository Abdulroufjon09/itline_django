"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import logging
import os
import threading

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()


def _startup_tasks():
    """Render'da build vaqtida migrate ishlamasa ham, server ko'tarilganda
    migratsiyalarni va (bir martalik) sheet importini bajaradi."""
    try:
        from django.core.management import call_command

        call_command("migrate", interactive=False)

        from register_withvue.models import Lead

        if not Lead.objects.exists():
            call_command("load_sheet_data")
    except Exception:
        logging.exception("Startup migrate/load_sheet_data xatosi")


threading.Thread(target=_startup_tasks, daemon=True).start()
