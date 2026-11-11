from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.opportunities.models import Opportunity
from apps.opportunities.seed_data import OPPORTUNITIES


class Command(BaseCommand):
    help = "Seed clearly-labelled EXAMPLE opportunities. TODO(owner): replace before launch."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing opportunity rows first (destructive).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if options["reset"]:
            Opportunity.objects.all().delete()
            self.stdout.write(self.style.WARNING("Deleted existing opportunities."))

        created = 0
        updated = 0
        for payload in OPPORTUNITIES:
            data = {**payload, "last_verified_at": timezone.now()}
            _, was_created = Opportunity.objects.update_or_create(
                name=payload["name"], defaults=data
            )
            created += int(was_created)
            updated += int(not was_created)
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded opportunities: {created} created, {updated} updated. "
                "TODO(owner): replace EXAMPLE entries with verified real opportunities."
            )
        )
