from django.core.management.base import BaseCommand
from django.core.management import call_command
import time


class Command(BaseCommand):
    """
    Load ALL knowledge base documents in sequence, then optionally embed.

    Usage:
      python manage.py load_all                 # Load chunks only (no embedding)
      python manage.py load_all --embed-sync    # Load + embed synchronously (local dev)
      python manage.py load_all --dry-run       # Show what would be loaded

    After loading without --embed-sync, run:
      python manage.py generate_embeddings --sync
    to generate embeddings separately.
    """

    help = 'Load all knowledge base documents and optionally generate embeddings'

    # Loader commands in dependency order
    LOADERS = [
        ('load_quran',               'Quran (Verse by Verse)'),
        ('load_hadith',              'Hadith Collections'),
        ('load_philosophy',          'Rational & Philosophical Arguments'),
        ('load_scientific_signs',    'Scientific Signs in the Quran'),
        ('load_comparative_religion','Comparative Religion'),
        ('load_logic',               'Logic & Reasoning Framework'),
        ('load_meta',                'Meta / Debate Topics / Glossary'),
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--embed-sync',
            action='store_true',
            help='After loading all chunks, run embeddings synchronously. '
                 'Use when Celery is not running (local dev).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show which commands would run without executing them.',
        )
        parser.add_argument(
            '--only',
            type=str,
            help='Comma-separated list of loaders to run, e.g. load_quran,load_hadith',
        )

    def handle(self, *args, **options):
        embed_sync = options['embed_sync']
        dry_run = options['dry_run']
        only = options.get('only')

        if only:
            requested = [s.strip() for s in only.split(',')]
            loaders = [(cmd, label) for cmd, label in self.LOADERS if cmd in requested]
            if not loaders:
                self.stderr.write(
                    self.style.ERROR(f'No matching loaders found for: {only}')
                )
                return
        else:
            loaders = self.LOADERS

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n{"=" * 60}\n'
            f'  DoesGodExist.ai — Knowledge Base Loader\n'
            f'  Loading {len(loaders)} document set(s)\n'
            f'{"=" * 60}\n'
        ))

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no changes will be made\n'))
            for cmd, label in loaders:
                self.stdout.write(f'  Would run: {cmd}  ({label})')
            return

        start_time = time.time()
        successes = []
        failures = []

        for cmd, label in loaders:
            self.stdout.write(f'\n→ Loading: {label}')
            self.stdout.write(f'  Command: python manage.py {cmd}')
            try:
                # ── FIX: individual loaders don't accept no_embed/embed_sync
                # Just call them plainly — they only load chunks
                call_command(cmd)
                successes.append(label)
                self.stdout.write(self.style.SUCCESS(f'  ✓ {label} loaded'))
            except Exception as e:
                failures.append((label, str(e)))
                self.stdout.write(self.style.ERROR(f'  ✗ {label} FAILED: {e}'))

        elapsed = time.time() - start_time

        # Summary
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\n{"=" * 60}\n'
            f'  Load Complete ({elapsed:.1f}s)\n'
            f'{"=" * 60}'
        ))
        self.stdout.write(
            self.style.SUCCESS(f'  ✓ Succeeded: {len(successes)}')
        )
        if failures:
            self.stdout.write(
                self.style.ERROR(f'  ✗ Failed:    {len(failures)}')
            )
            for label, err in failures:
                self.stdout.write(self.style.ERROR(f'    - {label}: {err}'))

        # ── Embed after loading if requested
        if embed_sync and successes:
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'\n{"=" * 60}\n'
                f'  Generating Embeddings (synchronous)\n'
                f'{"=" * 60}\n'
            ))
            try:
                call_command('generate_embeddings', sync=True)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Embedding failed: {e}'))
        elif successes:
            self.stdout.write(self.style.WARNING(
                '\n  Chunks loaded. Now generate embeddings:\n\n'
                '    python manage.py generate_embeddings --sync\n\n'
                '  Or reload + embed in one step:\n'
                '    python manage.py load_all --embed-sync'
            ))