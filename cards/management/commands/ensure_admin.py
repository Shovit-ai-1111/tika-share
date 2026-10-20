import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

# The docker-compose development default. Never allowed outside DEBUG mode.
INSECURE_DEFAULT_PASSWORD = "admin12345"


class Command(BaseCommand):
    help = (
        "Create the admin user from ADMIN_USERNAME / ADMIN_PASSWORD / ADMIN_EMAIL "
        "if it does not exist yet. Safe to run on every start; never changes an existing user."
    )

    def handle(self, *args, **options):
        username = os.environ.get("ADMIN_USERNAME", "admin")
        password = os.environ.get("ADMIN_PASSWORD", "")
        email = os.environ.get("ADMIN_EMAIL", "")

        if not password:
            self.stdout.write("ADMIN_PASSWORD not set - skipping admin creation.")
            return

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Admin user '{username}' already exists - leaving it unchanged.")
            return

        if not settings.DEBUG and password == INSECURE_DEFAULT_PASSWORD:
            raise CommandError(
                "Refusing to create an admin with the default development password. "
                "Set ADMIN_PASSWORD to something private (e.g. in your .env file)."
            )

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Created admin user '{username}'."))
