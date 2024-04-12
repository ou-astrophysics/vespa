from django.core.management.base import BaseCommand, CommandError

import csv

from starcatalogue.models import Star, FoldedLightcurve, ZooniverseSubject


class Command(BaseCommand):
    help = "Imports folded lightcurve data (lookup.dat)"

    def add_arguments(self, parser):
        parser.add_argument("file", nargs=1, type=open)

    def handle(self, *args, **options):
        r = csv.reader(options["file"][0], delimiter=" ", skipinitialspace=True)
        imported_total = 0
        for count, row in enumerate(r):
            try:
                subject_id = int(row[0])
                superwasp_id = row[1]
                period_number = int(row[3])
            except IndexError:
                print("Warning: Skipping row {} due to IndexError".format(count))
                continue

            star = Star.objects.get_or_create(superwasp_id=superwasp_id)
            lightcurve = FoldedLightcurve.objects.get_or_create(
                star=star,
                period_number=period_number,
            )

            ZooniverseSubject.objects.get_or_create(
                zooniverse_id=subject_id, lightcurve=lightcurve
            )

            imported_total += 1

        self.stdout.write("Total imported: {}".format(imported_total))
