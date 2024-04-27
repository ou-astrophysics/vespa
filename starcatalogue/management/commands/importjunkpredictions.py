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
        qs = FoldedLightcurve.objects.filter(cnn_junk_prediction=None)
        total = qs.count()
        updated = 0
        for n, lc in enumerate(qs.iterator(), start=1):
            try:
                image_filename = f"{lc.star.superwasp_id}_P{lc.period_number}_fold.gif"
                try:
                    lc.cnn_junk_prediction = df.loc[image_filename]["prediction"]
                except KeyError:
                    continue
                lcs.append(lc)
            finally:
                if n % 100 == 0 or n == total:
                    print(f"\r{n} / {total} ({(n / total) * 100:.2f}%)", end="")
                    if len(lcs) > 0:
                        updated += FoldedLightcurve.objects.bulk_update(
                            lcs, ["cnn_junk_prediction"]
                        )
                        lcs = []
        print(f"\nUpdated {updated}")
