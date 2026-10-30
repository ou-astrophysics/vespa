import errno
from unittest.mock import patch

from django.template import Context, Template
from django.test import SimpleTestCase

from .exports import DataExport
from .models import Star


class FileSizeRenderingTests(SimpleTestCase):
    def test_file_sizes_render_and_storage_errors_are_reported(self):
        cases = (
            (Star(fits_file="sources/test.fits"), "fits_file", "fits_file_naturalsize"),
            (DataExport(export_file="exports/test.csv"), "export_file", "export_file_naturalsize"),
        )
        for obj, field_name, property_name in cases:
            template = Template("{{ object." + property_name + " }}")
            context = Context({"object": obj})
            storage = getattr(obj, field_name).storage
            with self.subTest(field=field_name, outcome="success"):
                with patch.object(storage, "size", return_value=1000), patch(
                    "sentry_sdk.capture_exception"
                ) as capture:
                    self.assertEqual(template.render(context), "1.0 kB")
                    capture.assert_not_called()

            for error_number in (errno.ESTALE, errno.ENOENT, errno.EACCES):
                error = OSError(error_number, "Storage unavailable", "test-file")
                with self.subTest(field=field_name, errno=error_number):
                    with patch.object(storage, "size", side_effect=error), patch(
                        "sentry_sdk.capture_exception"
                    ) as capture:
                        self.assertEqual(template.render(context), "size unavailable")
                        capture.assert_called_once_with(error)
