from django.db import migrations


class Migration(migrations.Migration):
    """
    Install the pgvector PostgreSQL extension before any VectorField is created.

    This must run before 0001_initial (which creates DocumentChunk with a
    VectorField). Without this, Django's test runner fails with:
        django.db.utils.ProgrammingError: type "vector" does not exist

    This migration is safe to run multiple times (CREATE EXTENSION IF NOT EXISTS).
    """

    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="CREATE EXTENSION IF NOT EXISTS vector;",
            reverse_sql="DROP EXTENSION IF EXISTS vector;",
        ),
    ]