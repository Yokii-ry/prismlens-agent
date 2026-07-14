import unittest
from unittest.mock import patch

from app.pipeline import checkpoint


class CheckpointTest(unittest.TestCase):
    def test_checkpoint_startup_api_is_importable(self) -> None:
        self.assertTrue(callable(checkpoint.setup_checkpoint_tables))

    def test_default_database_url_uses_project_postgres_password(self) -> None:
        self.assertIn(
            "postgresql+asyncpg://multiprism:multiprism@",
            checkpoint.settings.DATABASE_URL,
        )

    def test_checkpoint_dsn_uses_psycopg_scheme(self) -> None:
        with patch.object(
            checkpoint.settings,
            "DATABASE_URL",
            "postgresql+asyncpg://user:pass@localhost:5432/app",
        ):
            self.assertEqual(
                checkpoint._get_checkpoint_dsn(),
                "postgresql://user:pass@localhost:5432/app",
            )


if __name__ == "__main__":
    unittest.main()
