#====================================================================================================#
#
# Title: Landsat and Sentinel-2 Image Compositing Tool
# Author: Leon Nill
# Last modified: 2019-06-20
#
#====================================================================================================#

'''
This tool allows for creating pixel-based Landsat image composites mostly based on the
approach of Griffiths et al. (2013): "A Pixel-Based Landsat Compositing Algorithm
for Large Area Land Cover Mapping".

The user can specify the calculation of either spectral-temporal metrics (STMs) (e.g. mean, min, ...)
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

source activate nillpy
cd '/Users/leonnill/Google Drive/03_LSNRS/Code/01_python/learthengine/learthengine/composite'
python ImgComposite_OKV.py

'''

import ee
ee.Initialize()
from learthengine import generals
from learthengine import prepro
from learthengine import composite
import math
import numpy as np


# ====================================================================================================#
# INPUT
# ====================================================================================================#
SENSOR = 'LS'
CLOUD_COVER = 50
BANDS = ['TCB', 'SCORE']  # 'B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'  # 'TCB', 'TCG', 'TCW'
PIXEL_RESOLUTION = 30
MASKS = ['cloud', 'cshadow', 'snow']  # only for Landsat
RESAMPLE = None #'bilinear'
REDUCE_RESOLUTION = None #ee.Reducer.mean().unweighted()
NATIVE_RESOLUTION = 30

ROI = ee.Geometry.Rectangle([13.377, 52.461, 13.504, 52.543])
'''
ROI = ee.Geometry.Polygon([[-11,32.679],
                           [30.344,32.679],
                           [30.344,72.414],
                           [-11,72.414],
                           [-11,32.679]])
'''
ROI_NAME = 'BERLIN'
EPSG = 'UTM'

# --------------------------------------------------
# TIME
# --------------------------------------------------
TARGET_YEARS = [2016]
SURR_YEARS = 3

MONTHLY = False  # True = no scoring, only temporal filtering and metric calculation

if MONTHLY:
       TARGET_MONTHS_client = [1, 4]
       MONTHS_OFFSET = 1
       STMs = [ee.Reducer.median()]
else:
       TARGET_DOY_client = [197]
       # [16, 46, 75, 105, 136, 166, 197, 228, 258, 289, 319, 350] = central DOY for months
       DOY_RANGE = 90
       DOY_VS_YEAR = 20

       REQ_DISTANCE_client = 50
       MIN_DISTANCE_client = 10

       W_DOYSCORE_client = 0.7
       W_YEARSCORE_client = 0
       W_CLOUDSCORE_client = 0.3

       SCORE = 'SCORE'
       BANDNAME = 'TC'

       STMs = None  # additional STMs? i.e. for defined time range without scoring


# ====================================================================================================#
# FUNCTIONS
# ====================================================================================================#

# --------------------------------------------------
# ADD BANDS
# --------------------------------------------------
def fun_add_doy_band(img):
       DOY_value = img.date().getRelative('day', 'year')
       DOY = ee.Image.constant(DOY_value).int().rename('DOY')
       DOY = DOY.updateMask(img.select('R').mask())
       return img.addBands(DOY)


def fun_doys(img):
       return ee.Feature(None, {'doy': img.date().getRelative('day', 'year')})


def fun_addyearband(img):
       YEAR_value = ee.Number.parse((img.date().format("YYYY")))
       YEAR = ee.Image.constant(YEAR_value).int().rename('YEAR')
       YEAR = YEAR.updateMask(img.select('R').mask())
       return img.addBands(YEAR)


def fun_addcloudband(img):
       CLOUD_MASK = img.mask().select('R')
       CLOUD_DISTANCE = CLOUD_MASK.Not()\
              .distance(ee.Kernel.euclidean(radius=REQ_DISTANCE, units='pixels'))\
              .rename('CLOUD_DISTANCE')
       CLIP_MAX = CLOUD_DISTANCE.lte(ee.Image.constant(REQ_DISTANCE))
       CLOUD_DISTANCE = CLOUD_DISTANCE.updateMask(CLIP_MAX)
       CLOUD_DISTANCE = CLOUD_DISTANCE.updateMask(CLOUD_MASK)
       return img.addBands(CLOUD_DISTANCE)

# ====================================================================================================#
# EXECUTE
# ====================================================================================================#
# select bits for mask
dict_mask = {'cloud': ee.Number(2).pow(5).int(),
             'cshadow': ee.Number(2).pow(3).int(),
             'snow': ee.Number(2).pow(4).int()}

sel_masks = [dict_mask[x] for x in MASKS]
bits = ee.Number(1)

for m in sel_masks:
    bits = ee.Number(bits.add(m))


# find epsg
if EPSG == 'UTM':
    EPSG = generals.find_utm(ROI)

for year in TARGET_YEARS:
       if MONTHLY:
              year_min = year - SURR_YEARS
              year_max = year + SURR_YEARS

              for month in TARGET_MONTHS_client:

                     months_min = month - MONTHS_OFFSET
                     if months_min < 1:
                            months_min = 1
                     months_max = month + MONTHS_OFFSET
                     if months_max > 12:
                            months_max = 12

                     # --------------------------------------------------
                     # IMPORT ImageCollections
                     # --------------------------------------------------

                     imgCol_L5_SR = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR') \
                            .filterBounds(ROI) \
                            .filter(ee.Filter.calendarRange(year_min, year_max, 'year')) \
                            .filter(ee.Filter.calendarRange(months_min, months_max, 'month')) \
                            .filter(ee.Filter.lt('CLOUD_COVER_LAND', CLOUD_COVER)) \
                            .map(prepro.rename_bands_l5) \
                            .map(prepro.mask_landsat_sr(bits)) \
                            .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR'])) \
                            .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

                     imgCol_L7_SR = ee.ImageCollection('LANDSAT/LE07/C01/T1_SR') \
                            .filterBounds(ROI) \
                            .filter(ee.Filter.calendarRange(year_min, year_max, 'year')) \
                            .filter(ee.Filter.calendarRange(months_min, months_max, 'month')) \
                            .filter(ee.Filter.lt('CLOUD_COVER_LAND', CLOUD_COVER)) \
                            .map(prepro.rename_bands_l7) \
                            .map(prepro.mask_landsat_sr(bits)) \
                            .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR'])) \
                            .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

                     imgCol_L8_SR = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR') \
                            .filterBounds(ROI) \
                            .filter(ee.Filter.calendarRange(year_min, year_max, 'year')) \
                            .filter(ee.Filter.calendarRange(months_min, months_max, 'month')) \
                            .filter(ee.Filter.lt('CLOUD_COVER_LAND', CLOUD_COVER)) \
                            .map(prepro.rename_bands_l8) \
                            .map(prepro.mask_landsat_sr(bits)) \
                            .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR'])) \
                            .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

                     imgCol_S2_L1C = ee.ImageCollection('COPERNICUS/S2') \
                            .filterBounds(ROI) \
                            .filter(ee.Filter.calendarRange(year_min, year_max, 'year')) \
                            .filter(ee.Filter.calendarRange(months_min, months_max, 'month')) \
                            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', CLOUD_COVER)) \
                            .map(prepro.mask_s2_cdi(0.5)) \
                            .map(prepro.rename_bands_s2) \
                            .map(prepro.mask_s2) \
                            .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

                     imgCol_S2_L2A = ee.ImageCollection('COPERNICUS/S2_SR') \
                            .filterBounds(ROI) \
                            .filter(ee.Filter.calendarRange(year_min, year_max, 'year')) \
                            .filter(ee.Filter.calendarRange(months_min, months_max, 'month')) \
                            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', CLOUD_COVER)) \
                            .map(prepro.mask_s2_cdi(0.5)) \
                            .map(prepro.rename_bands_s2) \
                            .map(prepro.mask_s2_scl) \
                            .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

                     # --------------------------------------------------
                     # MERGE imgCols
                     # --------------------------------------------------
                     if SENSOR == 'S2_L1C':
                            imgCol_SR = imgCol_S2_L1C
                     elif SENSOR == 'S2_L2A':
                            imgCol_SR = imgCol_S2_L2A
                     elif SENSOR == 'LS':
                            imgCol_SR = imgCol_L5_SR.merge(imgCol_L7_SR).merge(imgCol_L8_SR)
                            imgCol_SR = imgCol_SR.sort("system:time_start")
                     elif SENSOR == 'L8':
                            imgCol_SR = imgCol_L8_SR
                     elif SENSOR == 'L7':
                            imgCol_SR = imgCol_L7_SR
                     elif SENSOR == 'L5':
                            imgCol_SR = imgCol_L5_SR
                     elif SENSOR == 'SL8':
                            imgCol_SR = imgCol_L8_SR.merge(imgCol_S2_L2A)
                     elif SENSOR == 'SL':
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
                     imgCol_SR = imgCol_SR.map(prepro.tcg)
                     imgCol_SR = imgCol_SR.map(prepro.tcb)
                     imgCol_SR = imgCol_SR.map(prepro.tcw)

                     # --------------------------------------------------
                     # Add DOY, YEAR & CLOUD Bands to ImgCol
                     # --------------------------------------------------
                     imgCol_SR = imgCol_SR.map(fun_add_doy_band)
                     imgCol_SR = imgCol_SR.map(fun_addyearband)

                     # --------------------------------------------------
                     # SPECTRAL TEMPORAL METRICS
                     # --------------------------------------------------
                     for i in range(len(STMs)):
                            if i == 0:
                                   PAR = ee.Image(imgCol_SR.select(BANDS).reduce(STMs[i]))
                            else:
                                   PAR = PAR.addBands(ee.Image(imgCol_SR.select(BANDS).reduce(STMs[i])))

                     # Resample
                     if RESAMPLE:
                            PAR = PAR.resample(RESAMPLE).reproject(crs=EPSG, scale=PIXEL_RESOLUTION)
                     if REDUCE_RESOLUTION:
                            PAR = PAR.reduceResolution(reducer=REDUCE_RESOLUTION, maxPixels=1024) \
                                     .reproject(crs=EPSG, scale=PIXEL_RESOLUTION)
                     
                     #PAR = ee.Image(imgCol_SR.select(BANDS).reduce(ee.Reducer.median()));
                     PAR = PAR.multiply(10000)
                     PAR = PAR.int16()

                     if year_max-year_min == 0:
                            year_filename = str(year)
                     else:
                            year_filename = str(year_min)+'-'+str(year_max)

                     if months_max-months_min == 0:
                            out_file = SENSOR + '_STMs_' + ROI_NAME + '_' + str(PIXEL_RESOLUTION) + 'm_' + \
                                       year_filename + '_' + str(month)
                     elif months_max-months_min == 11:
                            out_file = SENSOR + '_STMs_' + ROI_NAME + '_' + str(PIXEL_RESOLUTION) + 'm_' + \
                                       year_filename
                     else:
                            out_file = SENSOR + '_STMs_' + ROI_NAME + '_' + str(PIXEL_RESOLUTION) + 'm_' + \
                                       year_filename + '_' + str(months_min)+'-' \
                                    + str(months_max)

                     out = ee.batch.Export.image.toDrive(image=PAR, description=out_file,
                                                         scale=PIXEL_RESOLUTION,
                                                         maxPixels=1e13,
                                                         region=ROI['coordinates'][0],
                                                         crs=EPSG)
                     process = ee.batch.Task.start(out)
       else:
              for i in range(len(TARGET_DOY_client)):
                     # --------------------------------------------------
                     # Prepare variables
                     # --------------------------------------------------
                     # Define considered time intervals (min & max)
                     iter_target_doy = TARGET_DOY_client[i]
                     iter_target_doy_min = iter_target_doy - DOY_RANGE
                     if iter_target_doy_min < 1:
                            iter_target_doy_min = 1

                     iter_target_doy_max = iter_target_doy + DOY_RANGE
                     if iter_target_doy_max > 365:
                            iter_target_doy_max = 365

                     year_min = year - SURR_YEARS
                     year_max = year + SURR_YEARS

                     REQ_DISTANCE = ee.Number(REQ_DISTANCE_client)
                     MIN_DISTANCE = ee.Number(MIN_DISTANCE_client)

                     # --------------------------------------------------
                     # IMPORT ImageCollections
                     # --------------------------------------------------
                     imgCol_L5_SR = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR') \
                            .filterBounds(ROI) \
                            .filter(ee.Filter.calendarRange(year_min, year_max, 'year')) \
                            .filter(ee.Filter.calendarRange(iter_target_doy_min, iter_target_doy_max, 'day_of_year')) \
                            .filter(ee.Filter.lt('CLOUD_COVER_LAND', CLOUD_COVER)) \
                            .map(prepro.rename_bands_l5) \
                            .map(prepro.mask_landsat_sr(bits)) \
                            .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR'])) \
                            .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

                     imgCol_L7_SR = ee.ImageCollection('LANDSAT/LE07/C01/T1_SR') \
                            .filterBounds(ROI) \
                            .filter(ee.Filter.calendarRange(year_min, year_max, 'year')) \
                            .filter(ee.Filter.calendarRange(iter_target_doy_min, iter_target_doy_max, 'day_of_year')) \
                            .filter(ee.Filter.lt('CLOUD_COVER_LAND', CLOUD_COVER)) \
                            .map(prepro.rename_bands_l7) \
                            .map(prepro.mask_landsat_sr(bits)) \
                            .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR'])) \
                            .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

                     imgCol_L8_SR = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR') \
                            .filterBounds(ROI) \
                            .filter(ee.Filter.calendarRange(year_min, year_max, 'year')) \
                            .filter(ee.Filter.calendarRange(iter_target_doy_min, iter_target_doy_max, 'day_of_year')) \
                            .filter(ee.Filter.lt('CLOUD_COVER_LAND', CLOUD_COVER)) \
                            .map(prepro.rename_bands_l8) \
                            .map(prepro.mask_landsat_sr(bits)) \
                            .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR'])) \
                            .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

                     imgCol_S2_L1C = ee.ImageCollection('COPERNICUS/S2') \
                            .filterBounds(ROI) \
                            .filter(ee.Filter.calendarRange(year_min, year_max, 'year')) \
                            .filter(ee.Filter.calendarRange(iter_target_doy_min, iter_target_doy_max, 'day_of_year')) \
                            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', CLOUD_COVER)) \
                            .map(prepro.mask_s2_cdi(0.5)) \
                            .map(prepro.rename_bands_s2) \
                            .map(prepro.mask_s2) \
                            .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

                     imgCol_S2_L2A = ee.ImageCollection('COPERNICUS/S2_SR') \
                            .filterBounds(ROI) \
                            .filter(ee.Filter.calendarRange(year_min, year_max, 'year')) \
                            .filter(ee.Filter.calendarRange(iter_target_doy_min, iter_target_doy_max, 'day_of_year')) \
                            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', CLOUD_COVER)) \
                            .map(prepro.mask_s2_cdi(0.5)) \
                            .map(prepro.rename_bands_s2) \
                            .map(prepro.mask_s2_scl) \
                            .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

                     # --------------------------------------------------
                     # MERGE imgCols
                     # --------------------------------------------------
                     if SENSOR == 'S2_L1C':
                            imgCol_SR = imgCol_S2_L1C
                     elif SENSOR == 'S2_L2A':
                            imgCol_SR = imgCol_S2_L2A
                     elif SENSOR == 'LS':
                            imgCol_SR = imgCol_L5_SR.merge(imgCol_L7_SR).merge(imgCol_L8_SR)
                            imgCol_SR = imgCol_SR.sort("system:time_start")
                     elif SENSOR == 'L8':
                            imgCol_SR = imgCol_L8_SR
                     elif SENSOR == 'L7':
                            imgCol_SR = imgCol_L7_SR
                     elif SENSOR == 'L5':
                            imgCol_SR = imgCol_L5_SR
                     elif SENSOR == 'SL8':
                            imgCol_SR = imgCol_L8_SR.merge(imgCol_S2_L2A)
                     elif SENSOR == 'SL':
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
                     imgCol_SR = imgCol_SR.map(prepro.tcg)
                     imgCol_SR = imgCol_SR.map(prepro.tcb)
                     imgCol_SR = imgCol_SR.map(prepro.tcw)

                     # --------------------------------------------------
                     # Add DOY, YEAR & CLOUD Bands to ImgCol
                     # --------------------------------------------------
                     imgCol_SR = imgCol_SR.map(fun_add_doy_band)
                     imgCol_SR = imgCol_SR.map(fun_addyearband)
                     imgCol_SR = imgCol_SR.map(fun_addcloudband)
                         
                     if SCORE == 'SCORE':
                            # --------------------------------------------------
                            # SCORING 1: DOY
                            # --------------------------------------------------
                            # add DOY-band to images in imgCol
                            DOYs = imgCol_SR.map(fun_doys).aggregate_array('doy').getInfo()

                            # retrieve target-DOY and DOY-std (client and server side)
                            TARGET_DOY = ee.Number(iter_target_doy)

                            DOY_STD_client = np.std(DOYs)

                            DOY_STD = ee.Number(DOY_STD_client)

                            # add Band with final DOY score to every image in imgCol
                            imgCol_SR = imgCol_SR.map(composite.doyscore(DOY_STD, TARGET_DOY))

                            # --------------------------------------------------
                            # SCORING 2: YEAR
                            # --------------------------------------------------
                            # calculate DOY-score at maximum DOY vs Year threshold
                            DOYSCORE_OFFSET = composite.doyscore_offset(iter_target_doy - DOY_VS_YEAR,
                                                                  iter_target_doy, DOY_STD_client)
                            DOYSCORE_OFFSET_OBJ = ee.Number(DOYSCORE_OFFSET)
                            TARGET_YEARS_OBJ = ee.Number(year)

                            # add Band with final YEAR score to every image in imgCol
                            imgCol_SR = imgCol_SR.map(composite.yearscore(TARGET_YEARS_OBJ, DOYSCORE_OFFSET_OBJ))

                            # --------------------------------------------------
                            # SCORING 3: CLOUD DISTANCE
                            # --------------------------------------------------
                            imgCol_SR = imgCol_SR.map(composite.cloudscore(REQ_DISTANCE, MIN_DISTANCE))

                            # --------------------------------------------------
                            # FINAL SCORING
                            # --------------------------------------------------
                            W_DOYSCORE = ee.Number(W_DOYSCORE_client)
                            W_YEARSCORE = ee.Number(W_YEARSCORE_client)
                            W_CLOUDSCORE = ee.Number(W_CLOUDSCORE_client)

                            imgCol_SR = imgCol_SR.map(composite.score(W_DOYSCORE, W_YEARSCORE, W_CLOUDSCORE))

                            COMPOSITE = imgCol_SR.qualityMosaic(SCORE)
                            COMPOSITE = COMPOSITE.select(BANDS)
                            COMPOSITE = COMPOSITE.multiply(10000)
                            COMPOSITE = COMPOSITE.int16()
                                
                            if STMs is not None:
                                   for i in range(len(STMs)):
                                          COMPOSITE = COMPOSITE.addBands(ee.Image(imgCol_SR.select(BANDS) \
                                                                                  .reduce(STMs[i])).int16())

                     elif SCORE == 'MAXNDVI':
                            COMPOSITE = imgCol_SR.qualityMosaic('NDVI')
                            COMPOSITE = COMPOSITE.select(BANDS)
                            COMPOSITE = COMPOSITE.multiply(10000)
                            COMPOSITE = COMPOSITE.int16()

                            if STMs is not None:
                                   for i in range(len(STMs)):
                                          COMPOSITE = COMPOSITE.addBands(ee.Image(imgCol_SR.select(BANDS) \
                                                                                  .reduce(STMs[i])).int16())
                     
                     else:
                            if STMs is not None:
                                   for i in range(len(STMs)):
                                          if i == 0:
                                                 COMPOSITE = ee.Image(imgCol_SR.select(BANDS).reduce(STMs[i]))
                                          else:
                                                 COMPOSITE = COMPOSITE.addBands(ee.Image(imgCol_SR.select(BANDS) \
                                                                                         .reduce(STMs[i])))
                                   # Resample
                                   if RESAMPLE:
                                          COMPOSITE = COMPOSITE.resample(RESAMPLE)
                                   if REDUCE_RESOLUTION:
                                          maxPixels_factor = math.ceil(PIXEL_RESOLUTION / NATIVE_RESOLUTION)
                                          COMPOSITE = COMPOSITE.reproject(crs=EPSG, scale=NATIVE_RESOLUTION)
                                          COMPOSITE = COMPOSITE.reduceResolution(reducer=REDUCE_RESOLUTION,
                                                                                 bestEffort=False,
                                                                                 maxPixels=maxPixels_factor*maxPixels_factor)

                                   
                                   COMPOSITE = COMPOSITE.multiply(10000)

                     if SURR_YEARS == 0:
                            year_filename = str(year)
                     else:
                            year_filename = str(year)+'-'+str(SURR_YEARS)

                     out_file = SENSOR + '_imgComposite_' + SCORE + '_' + BANDNAME + '_' + ROI_NAME + '_' + \
                                str(PIXEL_RESOLUTION) + 'm_' + year_filename + '_' + str(iter_target_doy)

                     out = ee.batch.Export.image.toDrive(image=COMPOSITE.toInt16(), description=out_file,
                                                         scale=PIXEL_RESOLUTION,
                                                         maxPixels=1e13,
                                                         region=ROI['coordinates'][0],
                                                         crs=EPSG)
                     process = ee.batch.Task.start(out)


# =====================================================================================================================#
# END
# =====================================================================================================================#
