import io
import json
import csv
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

from django.core import mail
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.exceptions import ValidationError

from .media_utils import optimize_image
from .models import Category, Product
from .tasks import queue_email, send_transaction_email
from .public_media import public_catalog_image


class UtilityCoverageTests(TestCase):
    def test_optimize_image_rejects_missing_and_invalid_files(self):
        with self.assertRaises(ValidationError):
            optimize_image(None)
        bad = ContentFile(b"not-an-image", name="bad.bin")
        with self.assertRaises(ValidationError):
            optimize_image(bad)

    def test_optimize_image_converts_rgba_to_webp(self):
        stream = io.BytesIO()
        Image.new("RGBA", (20, 20), (255, 0, 0, 128)).save(stream, "PNG")
        stream.seek(0)
        result = optimize_image(SimpleUploadedFile("source.png", stream.getvalue(), content_type="image/png"))
        self.assertEqual(result.name, "catalogue.webp")
        self.assertTrue(result.size)

    @override_settings(FRONTEND_ORIGIN="https://shop.example/")
    def test_sitemap_contains_static_and_active_products(self):
        category = Category.objects.create(name="Test", slug="test")
        Product.objects.create(name="Visible", slug="visible", category=category,
                               price=1000, active=True)
        Product.objects.create(name="Hidden", slug="hidden", category=category,
                               price=1000, active=False)
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("https://shop.example/produit/visible", body)
        self.assertNotIn("/produit/hidden", body)

    @override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        DEFAULT_FROM_EMAIL="noreply@example.test",
    )
    def test_email_task_and_eager_queue(self):
        self.assertEqual(
            send_transaction_email("Sujet", "Corps", ["user@example.test"]),
            1,
        )
        self.assertEqual(len(mail.outbox), 1)
        with self.captureOnCommitCallbacks(execute=True):
            queue_email("Sujet 2", "Corps 2", ["user@example.test"])
        self.assertEqual(len(mail.outbox), 2)

    def test_public_catalog_image_validation_and_response(self):
        from django.core.files.storage import default_storage
        request = self.client.get("/").wsgi_request
        with patch.object(default_storage, "open", return_value=io.BytesIO(b"data")) as opened:
            response = public_catalog_image(request, "phone.webp")
        opened.assert_called_once_with("catalog/phone.webp", "rb")
        self.assertEqual(response["Cache-Control"], "public, max-age=3600")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        for invalid in ("", "../secret.webp", ".hidden.webp", "phone.txt", r"a\b.webp"):
            with self.assertRaises(Http404):
                public_catalog_image(request, invalid)

    def test_seed_command_is_idempotent_with_temporary_catalog_data(self):
        with tempfile.TemporaryDirectory() as folder:
            data = [{
                "kind": "simple", "slug": "seeded-case", "name": "Seeded",
                "price": 10000, "phone": "Test Phone", "cover_url": "/x.webp",
                "ref": "REF-1",
            }]
            Path(folder, "produits_selection.json").write_text(json.dumps(data))
            with Path(folder, "index_photos_15_archives.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["modele_telephone"])
                writer.writeheader()
                writer.writerow({"modele_telephone": "Test Phone"})
            with patch.dict("os.environ", {"CATALOG_DATA_DIR": folder}):
                call_command("seed_new_arrivals")
                call_command("seed_new_arrivals")
            self.assertTrue(Product.objects.filter(slug="seeded-case").exists())

    def test_import_command_dry_run_and_validation_errors(self):
        from django.core.management.base import CommandError
        with tempfile.TemporaryDirectory() as folder:
            index = Path(folder, "index.csv")
            index.write_text("archive,chemin_dans_zip,modele_telephone\npart1.zip,a.webp,Test\n")
            archives = Path(folder, "archives")
            archives.mkdir()
            with self.assertRaises(CommandError):
                call_command("import_housse_archives", archives_dir=str(archives), index=str(index))
            with zipfile.ZipFile(archives / "part1.zip", "w") as archive:
                archive.writestr("a.webp", b"bad")
            call_command("import_housse_archives", archives_dir=str(archives), index=str(index), dry_run=True)

