import ee
from .atmospheric_functions import atmospheric_functions, radiance_addband, scale_wv, radcal, era5_tcwv
from .collection_matching import maxDiffFilter, join_wv, join_l
from .land_surface_temperatue import delta, gamma


def apply_lst_prepro(imgcol_sr, sensor="L5", time_filter=None, roi=None, cloud_cover=70, wv_method=None):

    if wv_method is None:
        wv_method = "NCEP"

    if sensor == "L5":
        coef = 1256
        imgcol_toa = ee.ImageCollection('LANDSAT/LT05/C01/T1')\
            .filterBounds(roi)\
            .filter(time_filter)\
            .filter(ee.Filter.lt('CLOUD_COVER_LAND', cloud_cover))\
            .select(['B6'])

    elif sensor == "L7":
        coef = 1277
        imgcol_toa = ee.ImageCollection('LANDSAT/LE07/C01/T1') \
            .filterBounds(roi) \
            .filter(time_filter) \
            .filter(ee.Filter.lt('CLOUD_COVER_LAND', cloud_cover)) \
            .select(['B6_VCID_2'])

    elif sensor == "L8":
        coef = 1324
        imgcol_toa = ee.ImageCollection('LANDSAT/LC08/C01/T1') \
            .filterBounds(roi) \
            .filter(time_filter) \
            .filter(ee.Filter.lt('CLOUD_COVER_LAND', cloud_cover)) \
            .select(['B10'])

    imgcol_toa = imgcol_toa.map(radcal)

    imgcol_sr = ee.ImageCollection(join_l.apply(imgcol_sr, imgcol_toa, maxDiffFilter))

    # Water Vapor
    if wv_method == 'NCEP':
        imgCol_WV = ee.ImageCollection('NCEP_RE/surface_wv') \
            .filterBounds(roi) \
            .filter(time_filter)
        imgcol_sr = ee.ImageCollection(join_wv.apply(imgcol_sr, imgCol_WV, maxDiffFilter))
        imgcol_sr = imgcol_sr.map(scale_wv)

    elif wv_method == 'ERA5':
        print("Begin client-side ERA5 retrieval")

        # ee.geometry to bounding box for era5
        flatten = lambda l: [item for sublist in l for item in sublist]
        coords = flatten(roi.coordinates().getInfo())
        lons = [x[0] for x in coords]
        lats = [x[1] for x in coords]
        roi_era5 = [max(lats), min(lons), min(lats), max(lons)]

        imgcol_sr = era5_tcwv(imgcol_sr, roi=roi_era5)

    imgcol_sr = imgcol_sr.map(radiance_addband)

    # Atmospheric Functions
    imgcol_sr = imgcol_sr.map(atmospheric_functions(sensor=sensor))

    # Delta and Gamma Functions
    imgcol_sr = imgcol_sr.map(delta(coef=coef))
    imgcol_sr = imgcol_sr.map(gamma(coef=coef))

    return imgcol_sr

