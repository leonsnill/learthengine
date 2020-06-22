import ee


def ndvi(img):
       ndvi = img.normalizedDifference(['NIR', 'R']).rename('NDVI')
       #ndvi = ndvi.multiply(10000)
       return img.addBands(ndvi)


def evi(gain=2.5, l=1, c1=6, c2=7.5):
    def wrap(img):
        evi = img.expression(
            'gain * ((nir - red) / (nir + c1 * red - c2 * blue + l))',
            {
                'gain': gain,
                'nir': img.select('NIR'),
                'red': img.select('R'),
                'blue': img.select('B'),
                'c1': c1,
                'c2': c2,
                'l': l
            }
        ).rename('EVI')
        return img.addBands(evi)
    return wrap


def fvc(ndvi_soil=0.15, ndvi_vegetation=0.9):
    """
    Derive fractional vegetation cover from linear relationship to NDVI
    Default valaues follow recommendations for higher resolution data according to Jimenez-Munoz et al. (2009):
    "Comparison Between Fractional Vegetation Cover Retrievals from Vegetation Indices and Spectral Mixture Analysis:
    Case Study of PROBA/CHRIS Data Over an Agricultural Area", Sensors, 9(2), 768–793.
    """
    def wrap(img):
        fvc = img.expression(
            '((NDVI-NDVI_s)/(NDVI_v-NDVI_s))**2',
            {
                'NDVI': img.select('NDVI'),
                'NDVI_s': ndvi_soil,
                'NDVI_v': ndvi_vegetation
            }
        )
        fvc = fvc.where(fvc.expression('fvc > 1',
                                                   {'fvc': fvc}), 1)
        fvc = fvc.where(fvc.expression('fvc < 0',
                                                   {'fvc': fvc}), 0).rename('FVC')
        return img.addBands(fvc)
    return wrap


def ndwi1(img):
       ndwi = img.normalizedDifference(['NIR', 'SWIR1']).rename('NDWI1')
       #ndwi = ndwi.multiply(10000)
       return img.addBands(ndwi)


def ndwi2(img):
       ndwi = img.normalizedDifference(['G', 'NIR']).rename('NDWI2')
       #ndwi = ndwi.multiply(10000)
       return img.addBands(ndwi)


# Zha et al. (2003): Use of Normalized Difference Built-Up Index in Automatically Mapping Urban Areas from TM Imagery
def ndbi(img):
    ndbi = img.normalizedDifference(['SWIR1', 'NIR']).rename('NDBI')
    # ndwi = ndwi.multiply(10000)
    return img.addBands(ndbi)


# Tasseled Cap Transformation (brightness, greenness, wetness) based on Christ 1985
def tcg(img):
    tcg = img.expression(
                         'B*(-0.1603) + G*(-0.2819) + R*(-0.4934) + NIR*0.7940 + SWIR1*(-0.0002) + SWIR2*(-0.1446)',
                         {
                         'B': img.select(['B']),
                         'G': img.select(['G']),
                         'R': img.select(['R']),
                         'NIR': img.select(['NIR']),
                         'SWIR1': img.select(['SWIR1']),
                         'SWIR2': img.select(['SWIR2'])
                         }).rename('TCG')
    #tcg = tcg.multiply(10000)
    return img.addBands(tcg)


def tcb(img):
    tcb = img.expression(
                         'B*0.2043 + G*0.4158 + R*0.5524 + NIR*0.5741 + SWIR1*0.3124 + SWIR2*0.2303',
                         {
                         'B': img.select(['B']),
                         'G': img.select(['G']),
                         'R': img.select(['R']),
                         'NIR': img.select(['NIR']),
                         'SWIR1': img.select(['SWIR1']),
                         'SWIR2': img.select(['SWIR2'])
                         }).rename('TCB')
    #tcb = tcb.multiply(10000)
    return img.addBands(tcb)


def tcw(img):
       tcw = img.expression(
              'B*0.0315 + G*0.2021 + R*0.3102 + NIR*0.1594 + SWIR1*(-0.6806) + SWIR2*(-0.6109)',
              {
                     'B': img.select(['B']),
                     'G': img.select(['G']),
                     'R': img.select(['R']),
                     'NIR': img.select(['NIR']),
                     'SWIR1': img.select(['SWIR1']),
                     'SWIR2': img.select(['SWIR2'])
              }).rename('TCW')
       #tcw = tcw.multiply(10000)
       return img.addBands(tcw)


def surface_albedo(coef=None, sensor="L5"):

    if coef is None:

        # Cunha et al. (2020): "Surface albedo as a proxy for land-cover clearing in seasonally dry forests: Evidence
        # from the Brazilian Caatinga", Remote Sensing of Environment.
        coef_l5 = [0.3206, 0, 0.1572, 0.3666, 0.1162, 0.0457, -0.0063]
        coef_l7 = [0.3141, 0, 0.1607, 0.3694, 0.1160, 0.0456, -0.0057]
        coef_l8 = [0.2453, 0.0508, 0.1804, 0.3081, 0.1332, 0.0521, 0.0011]

        if sensor == 'L5':
            coef = coef_l5
        elif sensor == 'L7':
            coef = coef_l7
        elif sensor == 'L8':
            coef = coef_l8
        else:
            return

    coef = [str(x) for x in coef]

    def wrap(img):
        albedo = img.expression(
            coef[0]+'*B+'+coef[1]+'*G+'+coef[2]+'*R+'+coef[3]+'*NIR+'+coef[4]+'*SWIR1+'+coef[5]+'*SWIR2+'+coef[6],
            {
                'B': img.select(['B']),
                'G': img.select(['G']),
                'R': img.select(['R']),
                'NIR': img.select(['NIR']),
                'SWIR1': img.select(['SWIR1']),
                'SWIR2': img.select(['SWIR2'])
            }).rename('ALBEDO')
        return img.addBands(albedo)
    return wrap
