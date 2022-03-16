import csv
import io
import urllib
import yaml
import zipfile
import ujson as json

import pandas
import seaborn

from astropy.table import vstack
from astropy.units import Quantity

from celery import shared_task

from django.conf import settings
from django.core.files.base import ContentFile

from matplotlib import pyplot

from panoptes_client import Subject, Project
from PIL import Image

from .models import Star, FoldedLightcurve, ZooniverseSubject


@shared_task
def generate_export(export_id):
    export = DataExport.objects.get(id=export_id)
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
    fits_url = f"http://wasp.warwick.ac.uk/lcextract?{encoded_params}"
    fits_data = urllib.request.urlopen(fits_url, timeout=30)
    star.fits_file.save(f"{star.superwasp_id}.fits", fits_data)
    star.save()

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
    plot.set_title(
        f"{lightcurve.star.superwasp_id} Period {lightcurve.period_length}s ({lightcurve.get_classification_display()})"
    )
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
    zoo_subject = Subject.find(vespa_subject.zooniverse_id)

    zoo_subject.metadata = vespa_subject.subject_metadata

    if settings.ZOONIVERSE_COMMIT_CHANGES:
        zoo_subject.save()

    vespa_subject.metadata_version = ZooniverseSubject.CURRENT_METADATA_VERSION
    vespa_subject.save()


@shared_task
def prepare_data_release(data_release_id):
    # To do: Add generate=True to this when ready
    print("requesting export")
    classification_export = Project(settings.ZOONIVERSE_PROJECT_ID).get_export(
        "classifications"
    )
    print("parsing export")
    # Can't load it all into pandas because of limited memory
    classifications = {"subject_id": [], "classification": [], "period_certainty": []}
    for row in classification_export.csv_dictreader():
        if int(row["workflow_id"]) != settings.ZOONIVERSE_MAIN_WORKFLOW_ID:
            continue
        annotations = json.loads(row["annotations"])
        classifications["classification"].append(annotations[0]["value"])
        try:
            classifications["period_certainty"].append(annotations[1]["value"])
        except IndexError:
            classifications["period_certainty"].append(None)
        classifications["subject_id"].append(row["subject_ids"])

    classifications = pandas.DataFrame(classifications)
    print(classifications)

    aggregated_classifications = classifications.pivot_table(
        columns=["classification"],
        values="classification",
        index="subject_id",
        aggfunc=len,
        fill_value=0,
    )
    # aggregated_classifications["consensus"] = aggregated_classifications.apply(
    #    lambda c: "Real" if c["Real"] > 0 else ("Junk" if c["Junk"] >= 3 else ""),
    #    axis=1,
    # )
    print(aggregated_classifications)

    aggregated_period_certainties = classifications.pivot_table(
        columns=["period_certainty"],
        values="period_certainty",
        index="subject_id",
        aggfunc=len,
        fill_value=0,
    )
    print(aggregated_period_certainties)


from .exports import (
    EXPORT_DATA_DESCRIPTION,
    gen_export_params_yaml_dict,
    gen_export_record_dict,
    DataExport,
)
