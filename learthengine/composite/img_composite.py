# ====================================================================================================#
#
# Title: Landsat and Sentinel-2 Image Compositing Tool
# Author: Leon Nill
# Last modified: 2019-06-20
#
# ====================================================================================================#

'''
This tool allows for creating pixel-based Landsat image composites based on the
approach of Griffiths et al. (2013): "A Pixel-Based Landsat Compositing Algorithm
for Large Area Land Cover Mapping".

Further, the user can specify the calculation of either spectral-temporal metrics (STMs) (e.g. mean, min, ...)
or pixel-based composites based on scoring functions that determine the suitability of each pixel.

-- User Requirements --
SENSOR               [STRING] – Single sensors or combinations (S2_L1C, S2_L2A, LS, L5, L7, L8, SL)

TARGET_YEARS         [INT] – List of integer years.
SURR_YEARS           INT – 'surrounding years', i.e. should adjacent years be considered for compositing
MONTHLY              BOOLEAN – if True, a monthly iteration is used, if False, iteration is over chosen
                     day of years
SCORE                [STRING] – Score paramater used to create image composite in "qualityMosaic()"-function.
                     ('SCORE', 'NDVI') Selection is based on the maximum of the given parameter, e.g. max NDVI
TARGET_MONTHS_client [INT] – List of target months
STMs                 [ee.Reducer] STMs as ee.Reducer object(s), e.g. ee.Reducer.mean()

ROI                  [xMin, yMin, xMax, yMax] – List of corner coordinates, e.g. [22.26, -19.54, 22.94, -18.89]
ROI_NAME             STRING – Name of the study area which will be used for the output filenames
EPSG                 STRING - Coordinate System !Currently disabled and exports are in WGS84!
PIXEL_RESOLUTION     INT/FLOAT – Output pixelsize in meters

CLOUD_COVER          INT/FLOAT – Maximum cloud cover percentage of scenes considered in pre-selection
BANDS                [STRING] – List of string band-names for export image (B,G,R,NIR,SWIR1,SWIR2,NDVI,TCW, ...)

DOY_RANGE            INT – Offset in days to consider around target doy
REQ_DISTANCE_client  INT – Distance from clouds/ c. shadows in pixels at which optimal conditions are expected
MIN_DISTANCE_client  INT - Minimum distance from clouds/ c. shadows in pixels
W_DOYSCORE_client    FLOAT – Weight of day of year in scoring (0-1)
W_YEARSCORE_client   FLOAT – Weight of year in scoring (0-1)
W_CLOUDSCORE_client  FLOAT – Weight of cloud distance in scoring (0-1)

'''

import ee
ee.Initialize()

from learthengine import generals
from learthengine import prepro
from learthengine import composite

import datetime
import numpy as np


# ====================================================================================================#
# USER INPUTS
# ====================================================================================================#


kwargs = {
    'sensor': 'S2_L2A',
    'bands': ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'],
    'pixel_resolution': 20,
    'cloud_cover': 70,
    'masks': ['cloud', 'cshadow', 'snow'],
    'roi': [38.4824, 8.7550, 39.0482, 9.2000],
    'score': 'STM',
    'reducer': ee.Reducer.median(),
    'target_years': [2020],  # 1985, 1990, 1995, 2000, 2005, 2010, 2015, 2020
    'surr_years': 1,
    'target_doys': [182],  # [16, 46, 75, 105, 136, 166, 197, 228, 258, 289, 319, 350]
    'doy_range': 182,
    'exclude_slc_off': True,
    'export_option': 'Asset',
    'asset_path': "users/leonxnill/Addis/",
    'export_name': 'MEDIAN_ADDIS'
}

# ====================================================================================================#
# EXECUTE
# ====================================================================================================#

def img_composite(sensor='LS', bands=None, pixel_resolution=30, cloud_cover=70, masks=None,
                  roi=None, score='STM', reducer=None, epsg=None, target_years=None, surr_years=0, target_doys=None,
                  doy_range=182, doy_vs_year=20, pbc_cloud_distance=(10, 50), pbc_weights=(0.6, 0.1, 0.3),
                  exclude_slc_off=True, export_option="Asset", asset_path=None, export_name=None):

    # defaults
    if roi is None:
        roi = [13.08, 52.32, 13.76, 52.67]  # Berlin
        print("No region of interest specified. Berlin it is.")
    if masks is None:
        masks = ['cloud', 'cshadow', 'snow']
        print("No masks specified. Masking clouds, cloud shadows and snow.")
    if sensor is None:
        sensor = "LS"
        print("No sensor specified. Landsat it is.")
    if bands is None:
        bands = ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']
        print("No bands specified. B-G-R-NIR-SWIR1-SWIR2 it is.")
    if target_years is None:
        target_years = [2019]
        print("No target years specified. 2019 it is.")
    if target_doys is None:
        target_doys = [182]
        print("No target DOYs specified. 182 it is.")
    if (export_option == "Asset") & (asset_path is None):
        print("No asset path specified.")
        return
    if export_name is None:
        export_name = "BERLIN"

    # roi client to server
    roi = ee.Geometry.Rectangle(roi)

    # find epsg
    if epsg is None:
        epsg = generals.find_utm(roi)

    min_clouddistance, max_clouddistance = pbc_cloud_distance
    weight_doy, weight_year, weight_cloud = pbc_weights

    for year in target_years:
        for i in range(len(target_doys)):

            # time
            iter_target_doy = target_doys[i]

            year_min = year - surr_years
            year_max = year + surr_years

            temp_filter = []
            for t in range(year_min, year_max+1):
                temp_target_doy = datetime.datetime(t, 1, 1) + datetime.timedelta(iter_target_doy - 1)
                temp_min_date = (temp_target_doy - datetime.timedelta(doy_range - 1)).strftime('%Y-%m-%d')
                temp_max_date = (temp_target_doy + datetime.timedelta(doy_range - 1)).strftime('%Y-%m-%d')
                temp_filter.append(ee.Filter.date(temp_min_date, temp_max_date))

            time_filter = ee.Filter.Or(*temp_filter)


            REQ_DISTANCE = ee.Number(max_clouddistance)
            MIN_DISTANCE = ee.Number(min_clouddistance)

            # .filter(ee.Filter.calendarRange(year_min, year_max, 'year')) \
            # .filter(ee.Filter.calendarRange(iter_target_doy_min, iter_target_doy_max, 'day_of_year')) \

            # --------------------------------------------------
            # IMPORT ImageCollections
            # --------------------------------------------------
            imgCol_L5_SR = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR') \
                .filterBounds(roi) \
                .filter(time_filter) \
                .filter(ee.Filter.lt('CLOUD_COVER_LAND', cloud_cover)) \
                .map(prepro.rename_bands_l5) \
                .map(prepro.mask_landsat_sr(masks)) \
                .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR'])) \
                .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

            imgCol_L7_SR = ee.ImageCollection('LANDSAT/LE07/C01/T1_SR') \
                .filterBounds(roi) \
                .filter(time_filter) \
                .filter(ee.Filter.lt('CLOUD_COVER_LAND', cloud_cover)) \
                .map(prepro.rename_bands_l7) \
                .map(prepro.mask_landsat_sr(masks)) \
                .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR'])) \
                .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

            # check SLC_OFF statement
            if exclude_slc_off:
                imgCol_L7_SR = imgCol_L7_SR.filter(ee.Filter.date("1999-04-18", "2003-05-31"))

            imgCol_L8_SR = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR') \
                .filterBounds(roi) \
                .filter(time_filter) \
                .filter(ee.Filter.lt('CLOUD_COVER_LAND', cloud_cover)) \
                .map(prepro.rename_bands_l8) \
                .map(prepro.mask_landsat_sr(masks)) \
                .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR'])) \
                .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

            imgCol_S2_L1C = ee.ImageCollection('COPERNICUS/S2') \
                .filterBounds(roi) \
                .filter(time_filter) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_cover)) \
                .map(prepro.mask_s2_cdi(-0.5)) \
                .map(prepro.rename_bands_s2) \
                .map(prepro.mask_s2) \
                .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

            imgCol_S2_L2A = ee.ImageCollection('COPERNICUS/S2_SR') \
                .filterBounds(roi) \
                .filter(time_filter) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_cover)) \
                .map(prepro.mask_s2_cdi(-0.5)) \
                .map(prepro.rename_bands_s2) \
                .map(prepro.mask_s2_scl) \
                .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

            # --------------------------------------------------
            # MERGE imgCols
            # --------------------------------------------------
            if sensor == 'S2_L1C':
                imgCol_SR = imgCol_S2_L1C
            elif sensor == 'S2_L2A':
                imgCol_SR = imgCol_S2_L2A
            elif sensor == 'LS':
                imgCol_SR = imgCol_L5_SR.merge(imgCol_L7_SR).merge(imgCol_L8_SR)
                imgCol_SR = imgCol_SR.sort("system:time_start")
            elif sensor == 'L8':
                imgCol_SR = imgCol_L8_SR
            elif sensor == 'L7':
                imgCol_SR = imgCol_L7_SR
            elif sensor == 'L5':
                imgCol_SR = imgCol_L5_SR
            elif sensor == 'SL8':
                imgCol_SR = imgCol_L8_SR.merge(imgCol_S2_L2A)
            elif sensor == 'SL':
                imgCol_SR = imgCol_L5_SR.merge(imgCol_L7_SR).merge(imgCol_L8_SR).merge(imgCol_S2_L2A)
            else:
                imgCol_SR = None
                print('No sensor specified!')

            # --------------------------------------------------
            # Calculate Indices
            # --------------------------------------------------
            imgCol_SR = imgCol_SR.map(prepro.ndvi)
            imgCol_SR = imgCol_SR.map(prepro.ndwi1)
            imgCol_SR = imgCol_SR.map(prepro.ndwi2)
            imgCol_SR = imgCol_SR.map(prepro.ndbi)
            imgCol_SR = imgCol_SR.map(prepro.tcg)
            imgCol_SR = imgCol_SR.map(prepro.tcb)
            imgCol_SR = imgCol_SR.map(prepro.tcw)

            # --------------------------------------------------
            # Add DOY, YEAR & CLOUD Bands to ImgCol
            # --------------------------------------------------
            imgCol_SR = imgCol_SR.map(composite.fun_add_doy_band)
            imgCol_SR = imgCol_SR.map(composite.fun_addyearband)
            imgCol_SR = imgCol_SR.map(composite.fun_addcloudband)

            if score == 'PBC':
                # --------------------------------------------------
                # SCORING 1: DOY
                # --------------------------------------------------
                # add DOY-band to images in imgCol
                doys = imgCol_SR.map(composite.fun_doys).aggregate_array('doy').getInfo()

                # retrieve target-DOY and DOY-std (client and server side)
                target_doy = ee.Number(iter_target_doy)

                doy_std_client = np.std(doys)

                doy_std = ee.Number(doy_std_client)

                # add Band with final DOY score to every image in imgCol
                imgCol_SR = imgCol_SR.map(composite.doyscore(doy_std, target_doy))

                # --------------------------------------------------
                # SCORING 2: YEAR
                # --------------------------------------------------
                # calculate DOY-score at maximum DOY vs Year threshold
                doyscore_offset = composite.doyscore_offset(iter_target_doy - doy_vs_year,
                                                            iter_target_doy, doy_std_client)
                doyscore_offset_obj = ee.Number(doyscore_offset)
                target_years_obj = ee.Number(year)

                # add Band with final YEAR score to every image in imgCol
                imgCol_SR = imgCol_SR.map(composite.yearscore(target_years_obj, doyscore_offset_obj))

                # --------------------------------------------------
                # SCORING 3: CLOUD DISTANCE
                # --------------------------------------------------
                imgCol_SR = imgCol_SR.map(composite.cloudscore(REQ_DISTANCE, MIN_DISTANCE))

                # --------------------------------------------------
                # FINAL SCORING
                # --------------------------------------------------
                w_doyscore = ee.Number(weight_doy)
                w_yearscore = ee.Number(weight_year)
                w_cloudscore = ee.Number(weight_cloud)

                imgCol_SR = imgCol_SR.map(composite.score(w_doyscore, w_yearscore, w_cloudscore))

                img_composite = imgCol_SR.qualityMosaic(score)
                img_composite = img_composite.select(bands)
                img_composite = img_composite.multiply(10000)
                img_composite = img_composite.int16()

            elif score == 'MAXNDVI':
                img_composite = imgCol_SR.qualityMosaic('NDVI')
                img_composite = img_composite.select(bands)
                img_composite = img_composite.multiply(10000)
                img_composite = img_composite.int16()

            elif score == 'STM':
                img_composite = ee.Image(imgCol_SR.select(bands).reduce(reducer))
                img_composite = img_composite.multiply(10000)
                img_composite = img_composite.int16()

            elif score == 'NOBS':
                img_composite = imgCol_SR.select(bands[0]).count().rename('NOBS')
                img_composite = img_composite.int16()

            else:
                print("Invalid score specified. Must be one of 'PBC', 'MAX_NDVI', 'STM' or 'NOBS'")

            # output filename
            out_file = sensor + '_' + score + '_' + export_name + '_' + \
                       str(pixel_resolution) + 'm_' + str(iter_target_doy) + '-' + str(doy_range) + \
                        '_' + str(year) + '-' + str(surr_years)

            # export image
            if export_option == "Drive":
                out = ee.batch.Export.image.toDrive(image=img_composite.toInt16(), description=out_file,
                                                    scale=pixel_resolution,
                                                    maxPixels=1e13,
                                                    region=roi['coordinates'][0],
                                                    crs=epsg)
            elif export_option == "Asset":
                out = ee.batch.Export.image.toAsset(image=img_composite.toInt16(), description=out_file,
                                                    assetId=asset_path+out_file,
                                                    scale=pixel_resolution,
                                                    maxPixels=1e13,
                                                    region=roi['coordinates'][0],
                                                    crs=epsg)
            else:
                print("Invalid export option specified. Must be one of 'Drive' or 'Asset'")

            return ee.batch.Task.start(out)

# =====================================================================================================================#
# END
# =====================================================================================================================#
