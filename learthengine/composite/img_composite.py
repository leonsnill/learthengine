# ====================================================================================================#
#
# Title: Landsat and Sentinel-2 Image Compositing Tool
# Author: Leon Nill
# Last modified: 2020-06-08
#
# ====================================================================================================#
import ee
ee.Initialize()

from learthengine import generals
from learthengine import prepro
from learthengine import composite
from learthengine import lst

import datetime
import numpy as np


def img_composite(sensor='LS', bands=None, pixel_resolution=30, cloud_cover=70, masks=None, T_threshold=None,
                  T_omission=True, roi=None, score='STM', reducer=None, epsg=None, target_years=None, surr_years=0,
                  target_doys=None, doy_range=182, doy_vs_year=20, min_clouddistance=10, max_clouddistance=50,
                  weight_doy=0.4, weight_year=0.4, weight_cloud=0.2, exclude_slc_off=False, export_option="Drive",
                  asset_path=None, export_name=None, lst_threshold=None, wv_method="NCEP"):
    """
    Image compositing function capable of creating pixel-based composites (PBC) according to Griffiths et al. (2013):
    "A Pixel-Based Landsat Compositing Algorithm for Large Area Land Cover Mapping", maximum NDVI composites as well as
    spectral-temporal metrics (STMs).

    :param sensor:              (Str) sensors to use. One of S2_L1C (TOA), S2_L2A (BOA), L5, L7, L8, LS (L-5/7/8),
                                SL (LS+S2_L2A)
    :param bands:               (List) of bandnames. One of ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2', 'NDVI', 'NDWI1',
                                'NDWI2', 'TCG', 'TCB', 'TCW', 'NDBI']. Default ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'].
    :param pixel_resolution:    (Int) pixel (spatial) resolution in CRS unit (usually meters). Default to 30.
    :param cloud_cover:         (Int) maximum scene cloud cover. Default to 70.
    :param masks:               (List) of objects to mask. One of and default to ['cloud', 'cshadow', 'snow'].
    :param roi_geom:                 (List) of rectangle corner coordinates in [lon1, lat1, lon2, lat2]. Default to "Berlin".
    :param score:               (Str) Which method to use for compositing. One of "PBC", "MAXNDVI", "STM" or "NOBS"
                                (pixel wise number of observations). Default to "STM".
    :param reducer:             (ee.Reducer object) if score = "STM". Default to ee.Reducer.median().
    :param epsg:                (Str) EPSG code. Default to None will automatically detect UTM Zone.
    :param target_years:        (List) of target years for compositing. Default to [2019].
    :param surr_years:          (Int) +- years to consider around target_years. Default to 0.
    :param target_doys:         (List) of target DOYs for compositing. Default to [182].
    :param doy_range:           (Int) +- DOYs to consider around target_doys. Default to 182.
    :param doy_vs_year:         (Int) If score = "PBC". DOY at which an image with an one year offset from target_years
                                has the same score as an image in the target_year with that DOY offset.
    :param min_clouddistance:   (Int) If score = "PBC". Minimum required distance from clouds.
    :param max_clouddistance:   (Int) If score = "PBC". Distance at which the maximum cloud score is allocated.
    :param weight_doy:          (Int) If score = "PBC". Weight for the DOY score. Default to 0.4.
    :param weight_year:         (Int) If score = "PBC". Weight for the YEAR score. Default to 0.4.
    :param weight_cloud:        (Int) If score = "PBC". Weight for the CLOUD score. Default to 0.2.
    :param exclude_slc_off:     (Bool) Exclude Landsat-7 ETM+ scenes after the scan-line corrector failure
                                (i.e. after May 31, 2003). Default to False.
    :param export_option:       (Str) One of "Drive" or "Asset". Default to "Drive".
    :param asset_path:          (Str) If export_option = "Asset". Directory string to store Assets in.
    :param export_name:         (Str) Name that is appendend to the image files. E.g. if the study area is Berlin,
                                the STM = ee.Reducer.median() and the band = "NDVI" one may choose "NDVI_MEDIAN_BERLIN"
    :return:                    If successful, returns "Submitted to Server."
    """

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
    if reducer is None:
        reducer = ee.Reducer.median()
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
    roi_geom = ee.Geometry.Rectangle(roi)

    # find epsg
    if epsg is None:
        epsg = generals.find_utm(roi_geom)


    for year in target_years:
        for i in range(len(target_doys)):

            # time definition
            iter_target_doy = target_doys[i]
            year_min = year - surr_years
            year_max = year + surr_years
            time_filter = generals.time_filter(l_years=[year_min, year_max], l_doys=iter_target_doy,
                                               doy_offset=doy_range)
            # server side cloud distance
            REQ_DISTANCE = ee.Number(max_clouddistance)
            MIN_DISTANCE = ee.Number(min_clouddistance)

            # import collections
            imgCol_L5_SR = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR') \
                .filterBounds(roi_geom) \
                .filter(time_filter) \
                .filter(ee.Filter.lt('CLOUD_COVER_LAND', cloud_cover)) \
                .map(prepro.rename_bands_l5) \
                .map(prepro.mask_landsat_sr(masks, T_threshold=T_threshold, omission=T_omission)) \
                .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR'])) \
                .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

            imgCol_L7_SR = ee.ImageCollection('LANDSAT/LE07/C01/T1_SR') \
                .filterBounds(roi_geom) \
                .filter(time_filter) \
                .filter(ee.Filter.lt('CLOUD_COVER_LAND', cloud_cover)) \
                .map(prepro.rename_bands_l7) \
                .map(prepro.mask_landsat_sr(masks, T_threshold=T_threshold, omission=T_omission)) \
                .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR'])) \
                .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

            # check SLC_OFF statement
            if exclude_slc_off:
                imgCol_L7_SR = imgCol_L7_SR.filter(ee.Filter.date("1999-04-18", "2003-05-31"))

            imgCol_L8_SR = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR') \
                .filterBounds(roi_geom) \
                .filter(time_filter) \
                .filter(ee.Filter.lt('CLOUD_COVER_LAND', cloud_cover)) \
                .map(prepro.rename_bands_l8) \
                .map(prepro.mask_landsat_sr(masks, T_threshold=T_threshold, omission=T_omission)) \
                .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR'])) \
                .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

            imgCol_S2_L1C = ee.ImageCollection('COPERNICUS/S2') \
                .filterBounds(roi_geom) \
                .filter(time_filter) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_cover)) \
                .map(prepro.mask_s2_cdi(-0.5)) \
                .map(prepro.rename_bands_s2) \
                .map(prepro.mask_s2) \
                .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'RE1', 'RE2', 'RE3', 'NIR', 'RE4', 'SWIR1', 'SWIR2']))

            imgCol_S2_L2A = ee.ImageCollection('COPERNICUS/S2_SR') \
                .filterBounds(roi_geom) \
                .filter(time_filter) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_cover)) \
                .map(prepro.mask_s2_cdi(-0.5)) \
                .map(prepro.rename_bands_s2) \
                .map(prepro.mask_s2_scl) \
                .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'RE1', 'RE2', 'RE3', 'NIR', 'RE4', 'SWIR1', 'SWIR2']))

            if 'LST' in bands:
                if imgCol_L5_SR.size().getInfo() > 0:
                    imgCol_L5_SR = lst.apply_lst_prepro(imgCol_L5_SR, sensor="L5", time_filter=time_filter,
                                                        roi=roi_geom, cloud_cover=cloud_cover, wv_method=wv_method)
                if imgCol_L7_SR.size().getInfo() > 0:
                    imgCol_L7_SR = lst.apply_lst_prepro(imgCol_L7_SR, sensor="L7", time_filter=time_filter,
                                                        roi=roi_geom, cloud_cover=cloud_cover, wv_method=wv_method)
                if imgCol_L8_SR.size().getInfo() > 0:
                    imgCol_L8_SR = lst.apply_lst_prepro(imgCol_L8_SR, sensor="L8", time_filter=time_filter,
                                                        roi=roi_geom, cloud_cover=cloud_cover, wv_method=wv_method)

            if 'ALBEDO' in bands:
                imgCol_L5_SR = imgCol_L5_SR.map(prepro.surface_albedo(sensor="L5"))
                imgCol_L7_SR = imgCol_L7_SR.map(prepro.surface_albedo(sensor="L7"))
                imgCol_L8_SR = imgCol_L8_SR.map(prepro.surface_albedo(sensor="L8"))

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
            if ('NDVI' in bands) or (score == 'MAXNDVI') or ('LST' in bands):
                imgCol_SR = imgCol_SR.map(prepro.ndvi)
            if 'EVI' in bands:
                imgCol_SR = imgCol_SR.map(prepro.evi())
            if 'NDWI1' in bands:
                imgCol_SR = imgCol_SR.map(prepro.ndwi1)
            if ('NDWI2' in bands) or ('LST' in bands):
                imgCol_SR = imgCol_SR.map(prepro.ndwi2)
            if 'NDBI' in bands:
                imgCol_SR = imgCol_SR.map(prepro.ndbi)
            if 'TCG' in bands:
                imgCol_SR = imgCol_SR.map(prepro.tcg)
            if 'TCB' in bands:
                imgCol_SR = imgCol_SR.map(prepro.tcb)
            if 'TCW' in bands:
                imgCol_SR = imgCol_SR.map(prepro.tcw)

            if 'LST' in bands:
                imgCol_SR = imgCol_SR.map(prepro.fvc(ndvi_soil=0.15, ndvi_vegetation=0.9))
                imgCol_SR = imgCol_SR.map(lst.emissivity())
                imgCol_SR = imgCol_SR.map(lst.land_surface_temperature(scale=0.01))
                if lst_threshold:
                    imgCol_SR = imgCol_SR.map(lst.mask_lst(threshold=lst_threshold, scale=0.01))


            # --------------------------------------------------
            # Add DOY, YEAR & CLOUD Bands to ImgCol
            # --------------------------------------------------
            imgCol_SR = imgCol_SR.map(composite.fun_add_doy_band)
            imgCol_SR = imgCol_SR.map(composite.fun_addyearband)
            imgCol_SR = imgCol_SR.map(composite.fun_addcloudband(REQ_DISTANCE))

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

            elif score == 'TS_slope':
                imgCol_SR = imgCol_SR.map(generals.add_timeband())
                for i in range(len(bands)):
                    slope = imgCol_SR.select(['TIME', bands[i]]).reduce(ee.Reducer.sensSlope())
                    slope = slope.select('slope')
                    slope = slope.multiply(365.25)  # yearly increase
                    slope = slope.multiply(10000).rename(bands[i]+'_slope')
                    slope = slope.int16()
                    if i == 0:
                        img_composite = ee.Image(slope)
                    else:
                        img_composite = img_composite.addBands(slope)

            elif score == 'NOBS':
                img_composite = imgCol_SR.select(bands[0]).count().rename('NOBS')
                img_composite = img_composite.int16()

            else:
                print("Invalid score specified. Must be one of 'PBC', 'MAXNDVI', 'STM' or 'NOBS'")


            # output filename
            out_file = sensor + '_' + score + '_' + export_name + '_' + \
                       str(pixel_resolution) + 'm_' + str(iter_target_doy) + '-' + str(doy_range) + \
                        '_' + str(year) + '-' + str(surr_years)

            # export image
            if export_option == "Drive":
                out = ee.batch.Export.image.toDrive(image=img_composite, description=out_file,
                                                    scale=pixel_resolution,
                                                    maxPixels=1e13,
                                                    region=roi_geom['coordinates'][0],
                                                    crs=epsg)
            elif export_option == "Asset":
                out = ee.batch.Export.image.toAsset(image=img_composite, description=out_file,
                                                    assetId=asset_path+out_file,
                                                    scale=pixel_resolution,
                                                    maxPixels=1e13,
                                                    region=roi_geom['coordinates'][0],
                                                    crs=epsg)
            else:
                print("Invalid export option specified. Must be one of 'Drive' or 'Asset'")

            process = ee.batch.Task.start(out)

    return print("Submitted to Server.")


# =====================================================================================================================#
# END
# =====================================================================================================================#
