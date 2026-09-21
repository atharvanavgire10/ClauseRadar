from django.core.management.base import BaseCommand

from eval.seed import seed_eval_workspace


class Command(BaseCommand):
    help = "Seed (or reseed) the public evaluation workspace with fictional demo data."

    def handle(self, *args, **options):
        summary = seed_eval_workspace()
        self.stdout.write(self.style.SUCCESS(f"Evaluation workspace seeded: {summary}"))
