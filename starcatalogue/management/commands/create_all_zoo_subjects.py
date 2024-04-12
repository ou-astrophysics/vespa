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
                period_length = float(row[2])
                period_number = int(row[3])
            except IndexError:
                print("Warning: Skipping row {} due to IndexError".format(count))
                continue

            star, _ = Star.objects.get_or_create(superwasp_id=superwasp_id)
            lightcurve, _ = FoldedLightcurve.objects.get_or_create(
                star__id=star.id,
                period_number=period_number,
            )
            if lightcurve.period_length is None:
                lightcurve.period_length = period_length
                lightcurve.save()

            ZooniverseSubject.objects.get_or_create(
                zooniverse_id=subject_id, lightcurve__id=lightcurve.id
            )

            imported_total += 1

        self.stdout.write("Total imported: {}".format(imported_total))
