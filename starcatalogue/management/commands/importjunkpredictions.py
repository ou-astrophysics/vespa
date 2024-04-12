from django.core.management.base import BaseCommand, CommandError

import csv
import pandas

from starcatalogue.models import FoldedLightcurve


class Command(BaseCommand):
    help = "Imports CNN junk predictions from a DataFrame into FoldedLightcurves"

    def add_arguments(self, parser):
        parser.add_argument("file", nargs=1, type=str)

    def handle(self, *args, **options):
        df = pandas.read_pickle(options["file"][0])
        imported_total = 0
        lcs = []
        total = len(df)
        updated = 0
        for n, (i, row) in enumerate(df.iterrows(), start=1):
            superwasp_id, period_number, _ = i.replace(".gif", "").split("_")
            period_number = int(period_number.replace("P", ""))
            try:
                lcs.append(
                    FoldedLightcurve.objects.get(
                        star__superwasp_id=superwasp_id, period_number=period_number
                    )
                )
                lcs[-1].cnn_junk_prediction = row["prediction"]
            except FoldedLightcurve.DoesNotExist:
                pass
            if n % 100 == 0 or n == total:
                print(f"\r{n} / {total} ({(n / total) * 100:.2f}%)", end="")
                if len(lcs) > 0:
                    updated += FoldedLightcurve.objects.bulk_update(
                        lcs, ["cnn_junk_prediction"]
                    )
                    lcs = []
        print(f"\nUpdated {updated}")
