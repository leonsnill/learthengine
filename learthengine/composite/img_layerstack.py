# ====================================================================================================#
#
# Title: Landsat and Sentinel-2 Image Layerstacking Tool
# Author: Leon Nill
# Last modified: 2020-06-08
#
# ====================================================================================================#
import ee
ee.Initialize()

from learthengine import generals
from learthengine import prepro
from learthengine import lst


def layerstack(imgCol):
    # Create initial image
    first = ee.Image(imgCol.first())
    # Write a function that appends a band to an image
    def addband(img, previous):
        datestring = ee.String(img.date().format("YYYY-MM-dd"))
        sensorstring = ee.String(img.get('satellite_id'))
        namestring = ee.String(sensorstring).cat(datestring)
        return ee.Image(previous).addBands(img.rename(namestring))
    return ee.Image(imgCol.iterate(addband, first))


def get_dates(imgCol):
    def wrap(img):
        return ee.Date(ee.Image(img).date().format("YYYY-MM-dd"))
    return ee.List(imgCol.toList(imgCol.size()).map(wrap))


def mosaic(imgCol, date):
    def wrap(date, newList):
        # cast
        newList = ee.List(newList)
        date = ee.Date(date)

        # filter collection
        filtered = ee.ImageCollection(imgCol.filterDate(date, date.advance(1, 'day')))

        # mosaic
        first = filtered.first()
        mosaic = ee.Image(filtered.mosaic())\
            .copyProperties(source=first).set('system:time_start', first.get('system:time_start'))

        return ee.List(newList.add(mosaic))

    return ee.ImageCollection(ee.List(date.iterate(wrap, ee.List([]))))


def img_layerstack(sensor='LS', bands=None, years=None, months=None, pixel_resolution=30, cloud_cover=70,
                  masks=None, roi=None, epsg=None, exclude_slc_off=False, export_option="Drive", asset_path=None,
                  export_name=None, lst_threshold=None, wv_method="NCEP"):

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

    # time
    years = [years] if isinstance(years, int) else years
    months = [months] if isinstance(months, int) else months
    time_filter = generals.time_filter(l_years=years, l_months=months)

    # image collections
    imgCol_L5_SR = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR') \
        .filterBounds(roi_geom) \
        .filter(time_filter) \
        .filter(ee.Filter.lt('CLOUD_COVER_LAND', cloud_cover)) \
        .map(prepro.rename_bands_l5) \
        .map(prepro.mask_landsat_sr(masks)) \
        .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR'])) \
        .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

    imgCol_L7_SR = ee.ImageCollection('LANDSAT/LE07/C01/T1_SR') \
        .filterBounds(roi_geom) \
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
        .filterBounds(roi_geom) \
        .filter(time_filter) \
        .filter(ee.Filter.lt('CLOUD_COVER_LAND', cloud_cover)) \
        .map(prepro.rename_bands_l8) \
        .map(prepro.mask_landsat_sr(masks)) \
        .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2'], ['TIR'])) \
        .map(prepro.scale_img(0.1, ['TIR'], ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

    imgCol_S2_L1C = ee.ImageCollection('COPERNICUS/S2') \
        .filterBounds(roi_geom) \
        .filter(time_filter) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_cover)) \
        .map(prepro.mask_s2_cdi(-0.5)) \
        .map(prepro.rename_bands_s2) \
        .map(prepro.mask_s2) \
        .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

    imgCol_S2_L2A = ee.ImageCollection('COPERNICUS/S2_SR') \
        .filterBounds(roi_geom) \
        .filter(time_filter) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_cover)) \
        .map(prepro.mask_s2_cdi(-0.5)) \
        .map(prepro.rename_bands_s2) \
        .map(prepro.mask_s2_scl) \
        .map(prepro.scale_img(0.0001, ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2']))

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

    imgCol_SR = imgCol_SR.sort("system:time_start")

    # --------------------------------------------------
    # Calculate Indices
    # --------------------------------------------------
    if ('NDVI' in bands) or ('LST' in bands):
        imgCol_SR = imgCol_SR.map(prepro.ndvi)
    if 'EVI' in bands:
        imgCol_SR = imgCol_SR.map(prepro.evi())
    if 'NDWI1' in bands:
        imgCol_SR = imgCol_SR.map(prepro.ndwi1)
    if 'NDWI2' in bands:
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

    dates = get_dates(imgCol_SR)
    date_range = dates.distinct()
    newcol = mosaic(imgCol_SR.select(bands), date_range)

    for band in bands:
        lyr = layerstack(newcol.select(band))
        lyr = lyr.multiply(10000)
        lyr = lyr.toInt16()

        out_file = sensor + '_layerstack_' + export_name + '_' + band + '_' + str(min(years)) + '-' + str(max(years))+ \
                   '_' + str(min(months)) + '-' + str(max(months))

        out = ee.batch.Export.image.toDrive(image=lyr, description=out_file,
                                            scale=pixel_resolution,
                                            maxPixels=1e13,
                                            region=roi_geom['coordinates'][0],
                                            crs=epsg)
        process = ee.batch.Task.start(out)

        return print("Submitted to Server.")
