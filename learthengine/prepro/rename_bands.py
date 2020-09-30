import ee


def rename_bands_l5(img):
    bands = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'pixel_qa']
    new_bands = ['B', 'G', 'R', 'NIR', 'SWIR1', 'TIR', 'SWIR2', 'pixel_qa']
    return img.select(bands).rename(new_bands).set('satellite_id', 'L5_')


def rename_bands_l7(img):
    bands = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'pixel_qa']
    new_bands = ['B', 'G', 'R', 'NIR', 'SWIR1', 'TIR', 'SWIR2', 'pixel_qa']
    return img.select(bands).rename(new_bands).set('satellite_id', 'L7_')


def rename_bands_l8(img):
    bands = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B10', 'B11', 'pixel_qa']
    new_bands = ['B', 'G', 'R', 'NIR', 'SWIR1', 'SWIR2', 'TIR', 'TIR2', 'pixel_qa']
    return img.select(bands).rename(new_bands).set('satellite_id', 'L8_')


def rename_bands_s2(img):
    bands = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9',
             'B11', 'B12', 'QA60', 'SCL']
    new_bands = ['AEROSOL', 'B', 'G', 'R', 'RE1', 'RE2', 'RE3', 'NIR', 'RE4', 'WV',
                 'SWIR1', 'SWIR2', 'QA60', 'SCL']
    return img.select(bands).rename(new_bands).set('satellite_id', 'S2_')

