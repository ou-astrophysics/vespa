import csv
import datetime
import io
import urllib
import yaml
import time
import zipfile
import ujson as json

import pandas
import seaborn

from astropy.table import vstack
from astropy.units import Quantity

from celery import shared_task

from django.conf import settings
from django.core.files.base import ContentFile
from django.db.models import Q, F

from matplotlib import pyplot

from pathlib import Path

from panoptes_client import Subject, Project
from PIL import Image

from .models import (
    AggregatedClassification,
    DataRelease,
    Star,
    FoldedLightcurve,
    ZooniverseSubject,
)


@shared_task
def generate_export(export_id):
    for attempt in range(5):
        try:
            export = DataExport.objects.get(id=export_id)
            break
        except DataExport.DoesNotExist:
            time.sleep(10)
    if export.export_status in (export.STATUS_RUNNING, export.STATUS_COMPLETE):
        return

    export.export_status = export.STATUS_RUNNING
    export.save()

    try:
        export_csv = io.StringIO()
        w = csv.DictWriter(export_csv, fieldnames=EXPORT_DATA_DESCRIPTION.keys())
        w.writeheader()
        total_records = export.queryset.count()
        for i, record in enumerate(export.queryset):
            if i % 1000 == 0:
                export.progress = float(i) / total_records * 100
                export.save()
            w.writerow(gen_export_record_dict(record))

        export_file = ContentFile(b"")
        with zipfile.ZipFile(
            export_file, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as export_zip:
            export_zip.writestr("export.csv", export_csv.getvalue())
            export_zip.writestr("fields.yaml", yaml.dump(EXPORT_DATA_DESCRIPTION))
            export_zip.writestr(
                "params.yaml",
                yaml.dump(gen_export_params_yaml_dict(export, total_records)),
            )
        export.export_file.save(export.EXPORT_FILE_NAME, export_file)
    except:
        export.export_status = export.STATUS_FAILED
        export.save()
        raise

    export.export_status = export.STATUS_COMPLETE
    export.save()


@shared_task
def download_fits(star_id):
    star = Star.objects.get(id=star_id)
    if star.fits_error_count >= settings.FITS_DOWNLOAD_ATTEMPTS:
        return
    encoded_params = urllib.parse.urlencode(
        {"objid": star.superwasp_id.replace("1SWASP", "1SWASP ")},
        quote_via=urllib.parse.quote,
    )
    fits_file_name = f"{star.superwasp_id}.fits"
    missing_paths = (Path(settings.MEDIA_ROOT) / "missing").glob(
        f"batch_*/{fits_file_name}"
    )
    unlink_missing = False
    for missing_path in missing_paths:
        with open(missing_path, "rb") as fits_f:
            fits_data = fits_f.read()
        unlink_missing = True
        break
    else:
        fits_url = f"http://wasp.warwick.ac.uk/lcextract?{encoded_params}"
        try:
            fits_data = urllib.request.urlopen(fits_url, timeout=30)
        except urllib.request.HTTPError:
            star.fits_error_count += 1
            star.save()
            return
    star.fits_file.save(fits_file_name, fits_data)
    star.save()

    if unlink_missing:
        missing_paths[0].unlink()

    star.get_image_location()
    star.calculate_magnitudes()

    for lightcurve in star.foldedlightcurve_set.all():
        lightcurve.get_image_location()


@shared_task
def generate_star_json_files(star_id):
    star = Star.objects.get(id=star_id)

    if not star.fits:
        return

    ts = star.timeseries
    if not ts:
        return
    ts_flux = Star.outlier_clip(ts["TAMFLUX2"])
    # Format based on Zooniverse lightcurve viewer requirements:
    # https://github.com/zooniverse/front-end-monorepo/blob/master/packages/lib-classifier/src/components/Classifier/components/SubjectViewer/components/ScatterPlotViewer/README.md#scatter-plot-viewer
    ts_data = {
        "data": {
            "x": list((ts.time.jd[~ts_flux.mask]).astype(float)),
            "y": list(ts_flux[~ts_flux.mask].astype(float)),
        },
    }

    json_data = ContentFile("")
    json.dump(ts_data, json_data)
    star.json_file.save("lightcurve.json", json_data)
    star.json_version = star.CURRENT_JSON_VERSION
    star.save()


@shared_task
def generate_lightcurve_images(lightcurve_id):
    lightcurve = FoldedLightcurve.objects.get(id=lightcurve_id)

    if not lightcurve.star.fits:
        return

    ts = lightcurve.timeseries
    if not ts:
        return
    epoch_length = ts["time"].max() - ts["time"].min()
    ts_extend = ts.copy()
    ts_extend["time"] = ts_extend["time"] + epoch_length
    ts = vstack([ts, ts_extend])
    ts_flux = Star.outlier_clip(ts["TAMFLUX2"])
    ts_data = {
        "phase": (ts.time / epoch_length) - Quantity(0.5, unit=None),
        "flux": ts_flux,
    }
    fig = pyplot.figure()
    plot = seaborn.scatterplot(
        data=ts_data,
        x="phase",
        y="flux",
        alpha=0.5,
        s=1,
    )
    plot.set_title(f"{lightcurve.star.superwasp_id} Period {lightcurve.period_length}s")
    image_data = ContentFile(b"")
    fig.savefig(image_data)
    lightcurve.image_file.save(f"lightcurve-{lightcurve.id}.png", image_data)

    thumbnail_data = ContentFile(b"")
    thumbmail_image = Image.open(image_data)
    thumbmail_image.thumbnail((100, 60))
    thumbmail_image.save(thumbnail_data, format="png")
    lightcurve.thumbnail_file.save(
        f"lightcurve-{lightcurve.id}-small.png", thumbnail_data
    )

    lightcurve.image_version = lightcurve.CURRENT_IMAGE_VERSION
    lightcurve.save()
    pyplot.close()


@shared_task
def generate_star_images(star_id):
    star = Star.objects.get(id=star_id)

    if not star.fits:
        return

    ts = star.timeseries
    if not ts:
        return
    ts_flux = Star.outlier_clip(ts["TAMFLUX2"])
    ts_data = {
        "time": ts.time.jd,
        "flux": ts_flux,
    }
    fig = pyplot.figure()
    plot = seaborn.scatterplot(
        data=ts_data,
        x="time",
        y="flux",
        alpha=0.5,
        s=1,
    )
    plot.set_title(star.superwasp_id)
    image_data = ContentFile(b"")
    fig.savefig(image_data)
    star.image_file.save(f"lightcurve.png", image_data)
    star.image_version = star.CURRENT_IMAGE_VERSION
    star.save()
    pyplot.close()


@shared_task
def save_zooniverse_metadata(vespa_subject_id):
    vespa_subject = ZooniverseSubject.objects.get(id=vespa_subject_id)

    if vespa_subject.lightcurve.cnn_junk_prediction is None:
        return

    zoo_subject = Subject.find(vespa_subject.zooniverse_id)

    zoo_subject.metadata = vespa_subject.subject_metadata

    if settings.ZOONIVERSE_COMMIT_CHANGES:
        zoo_subject.save()

    vespa_subject.metadata_version = ZooniverseSubject.CURRENT_METADATA_VERSION
    vespa_subject.save()


@shared_task
def prepare_data_release(data_release_id):
    period_certainty_overrides = {
        "Rotator": "Correct period",
        "Unknown": "Correct period",
        "Junk": "Wrong period",
    }
    # This task seems to hit a race condition sometimes where the DataRelease hasn't
    # actually been saved yet
    time.sleep(5)
    data_release = DataRelease.objects.get(id=data_release_id)

    classifications = None

    if settings.ZOONIVERSE_CACHE_EXPORT:
        try:
            classifications = pandas.read_pickle("classifications.pkl")
        except FileNotFoundError:
            classification_export = Project(settings.ZOONIVERSE_PROJECT_ID).get_export(
                "classifications"
            )
    else:
        classification_export = Project(settings.ZOONIVERSE_PROJECT_ID).get_export(
            "classifications", generate=data_release.generate_export
        )

    if classifications is None:
        classifications = {
            "subject_id": [],
            "classification": [],
            "period_certainty": [],
            "user_name": [],
        }
        # Can't load it all into pandas because of limited memory
        for row in classification_export.csv_dictreader():
            # We count classifications from both workflows, to correctly aggregate subjects
            # which were filtered as junk after receiving classifications in the main
            # workflow.
            if int(row["workflow_id"]) not in (
                settings.ZOONIVERSE_MAIN_WORKFLOW_ID,
                settings.ZOONIVERSE_JUNK_WORKFLOW_ID,
            ):
                continue
            annotations = json.loads(row["annotations"])
            classification = annotations[0]["value"]
            if classification == "Real":
                # We don't need these as they are subsequently classified in the main workflow
                continue
            classifications["classification"].append(classification)
            try:
                period_certainty = annotations[1]["value"]
            except IndexError:
                period_certainty = None
            # Prepend primary classification to period certainty vote so we can count votes for
            # each primary class separately.
            classifications["period_certainty"].append(
                f"{classification} {period_certainty_overrides.get(classification, period_certainty)}"
            )
            classifications["subject_id"].append(int(row["subject_ids"]))
            classifications["user_name"].append(row["user_name"])
        del classification_export
        classifications = pandas.DataFrame(classifications)
        classifications.drop_duplicates(
            subset=["user_name", "subject_id"], inplace=True
        )
        if settings.ZOONIVERSE_CACHE_EXPORT:
            try:
                classifications.to_pickle("classifications.pkl")
            except PermissionError:
                pass

    aggregated_classifications = classifications.pivot_table(
        columns=["classification"],
        values="user_name",
        index="subject_id",
        aggfunc=len,
        fill_value=0,
    )
    aggregated_classifications["consensus class"] = aggregated_classifications[
        [  # The ordering of columns matters here for tie breaking
            "Junk",
            "Pulsator",
            "Rotator",
            "EW type",
            "EA/EB type",
            "Unknown",
        ]
    ].idxmax(axis="columns")

    aggregated_period_certainties = classifications.pivot_table(
        columns=["period_certainty"],
        values="user_name",
        index="subject_id",
        aggfunc=len,
        fill_value=0,
    )

    del classifications

    aggregated_classifications = aggregated_classifications.join(
        aggregated_period_certainties,
    )

    aggregated_classifications = aggregated_classifications[
        aggregated_classifications["consensus class"] != "Junk"
    ]

    zoo_lookup = pandas.read_csv(
        settings.IMPORT_ROOT / "lookup.dat",
        delim_whitespace=True,
        header=None,
    )
    zoo_lookup.columns = [
        "subject_id",
        "SWASP ID",
        "Period",
        "Period Number",
    ]
    zoo_lookup.set_index("subject_id", inplace=True)
    # Lookup periods were rounded to 3 dp, but (presumably) due to floating point errors
    # weren't always rounded consistently. To enable matching of records, we cast periods
    # to int to truncate without rounding.
    zoo_lookup["Period"] = zoo_lookup["Period"].apply(int)

    periodicity_cat = pandas.read_csv(
        settings.IMPORT_ROOT / "results_total.dat",
        delim_whitespace=True,
        header=None,
    )
    periodicity_cat.columns = [
        "Camera Number",
        "SWASP",
        "ID",
        "Period Number",
        "Period",
        "Sigma",
        "Chi Squared",
        "Period Flag",
    ]
    periodicity_cat = periodicity_cat[(periodicity_cat["Period Flag"] == 0)]
    periodicity_cat["SWASP ID"] = periodicity_cat["SWASP"] + periodicity_cat["ID"]
    periodicity_cat["Original Period"] = periodicity_cat["Period"]
    periodicity_cat["Period"] = periodicity_cat["Period"].apply(int)
    periodicity_cat.drop(
        ["Period Flag", "Camera Number", "SWASP", "ID"], axis="columns", inplace=True
    )
    periodicity_cat.set_index(["SWASP ID", "Period", "Period Number"], inplace=True)
    periodicity_cat.drop_duplicates(inplace=True)

    aggregated_classifications = aggregated_classifications.join(zoo_lookup)
    aggregated_classifications = aggregated_classifications.join(
        periodicity_cat, on=("SWASP ID", "Period", "Period Number")
    )
    del zoo_lookup, periodicity_cat

    if settings.DATA_RELEASE_IMPORT_LIMIT:
        aggregated_classifications = aggregated_classifications.head(
            settings.DATA_RELEASE_IMPORT_LIMIT
        )

    CLASSIFICATION_LOOKUP = {
        "EA/EB type": AggregatedClassification.EA_EB,
        "EW type": AggregatedClassification.EW,
        "Pulsator": AggregatedClassification.PULSATOR,
        "Rotator": AggregatedClassification.ROTATOR,
        "Unknown": AggregatedClassification.UNKNOWN,
        "Wrong period": AggregatedClassification.UNCERTAIN,
        "Correct period": AggregatedClassification.CERTAIN,
        "Half correct period": AggregatedClassification.HALF,
    }

    for subject_id, row in aggregated_classifications.iterrows():
        star, _ = Star.objects.get_or_create(superwasp_id=row["SWASP ID"])

        try:
            zoo_subject = ZooniverseSubject.objects.get(zooniverse_id=subject_id)
            folded_lightcurve = zoo_subject.lightcurve
        except ZooniverseSubject.DoesNotExist:
            zoo_subject = None
            # Because of earlier data issues there can be duplicate lightcurves, but it is
            # safe to just use the first one and ignore the others
            folded_lightcurve = FoldedLightcurve.objects.filter(
                star=star, period_number=row["Period Number"]
            ).first()

        if folded_lightcurve is None:
            folded_lightcurve = FoldedLightcurve.objects.create(
                star=star,
                period_number=row["Period Number"],
                period_length=row["Original Period"],
                sigma=row["Sigma"],
                chi_squared=row["Chi Squared"],
            )
        elif (
            folded_lightcurve.period_length != row["Original Period"]
            or folded_lightcurve.sigma != row["Sigma"]
            or folded_lightcurve.chi_squared != row["Chi Squared"]
        ):
            folded_lightcurve.updated_period_length = row["Original Period"]
            folded_lightcurve.updated_sigma = row["Sigma"]
            folded_lightcurve.updated_chi_squared = row["Chi Squared"]
            folded_lightcurve.save()

        if zoo_subject is None:
            ZooniverseSubject.objects.get_or_create(
                zooniverse_id=subject_id, lightcurve=folded_lightcurve
            )

        if row["consensus class"] in period_certainty_overrides:
            period_certainty = period_certainty_overrides[row["consensus class"]]
        else:
            column_order = [
                f"{row['consensus class']} Correct period",
                f"{row['consensus class']} Wrong period",
            ]
            if row["consensus class"] != "Pulsator":
                column_order = [
                    f"{row['consensus class']} Half correct period",
                ] + column_order
            period_certainty = (
                pandas.to_numeric(row[column_order])
                .idxmax()
                .replace(f"{row['consensus class']} ", "")
            )

        AggregatedClassification.objects.create(
            data_release=data_release,
            lightcurve=folded_lightcurve,
            classification=CLASSIFICATION_LOOKUP[row["consensus class"]],
            period_uncertainty=CLASSIFICATION_LOOKUP[period_certainty],
            classification_count=sum(
                row[t]
                for t in [
                    "EA/EB type",
                    "EW type",
                    "Pulsator",
                    "Rotator",
                    "Unknown",
                    "Junk",
                ]
            ),
        )

    data_release.aggregation_finished = datetime.datetime.now()
    data_release.save()


@shared_task
def activate_data_release(data_release_id):
    # This data import may have staged corrected metadata for lightcurves
    # Move the staged metadata into the live fields
    outdated_lightcurves = FoldedLightcurve.objects.exclude(
        Q(updated_period_length=None)
        | Q(updated_sigma=None)
        | Q(updated_chi_squared=None)
    )

    outdated_lightcurves.update(
        period_length=F("updated_period_length"),
        sigma=F("updated_sigma"),
        chi_squared=F("updated_chi_squared"),
        image_version=None,
    )

    outdated_lightcurves.update(
        updated_period_length=None,
        updated_sigma=None,
        updated_chi_squared=None,
    )

    data_release = DataRelease.objects.get(pk=data_release_id)
    # Now pre-generate the full data export
    DataExport.objects.create(
        data_release=data_release,
        data_version=data_release.version,
        in_data_archive=True,
    )
    data_release.active_at = datetime.datetime.now()
    data_release.save()


from .exports import (
    EXPORT_DATA_DESCRIPTION,
    gen_export_params_yaml_dict,
    gen_export_record_dict,
    DataExport,
)
