import ee


def atmospheric_functions(cs=None, sensor='L5'):

    if cs is None:
        cs_l8 = [0.04019, 0.02916, 1.01523,
                 -0.38333, -1.50294, 0.20324,
                 0.00918, 1.36072, -0.27514]
        cs_l7 = [0.06518, 0.00683, 1.02717,
                 -0.53003, -1.25866, 0.10490,
                 -0.01965, 1.36947, -0.24310]
        cs_l5 = [0.07518, -0.00492, 1.03189,
                 -0.59600, -1.22554, 0.08104,
                 -0.02767, 1.43740, -0.25844]

        if sensor == 'L5':
            cs = cs_l5
        if sensor == 'L7':
            cs = cs_l7
        if sensor == 'L8':
            cs = cs_l8

    def wrap(img):
        af1 = img.expression(
            '('+str(cs[0])+'*(WV**2))+('+str(cs[1])+'*WV)+('+str(cs[2])+')',
            {
                'WV': img.select('WV_SCALED')
            }
        ).rename('AF1')

        af2 = img.expression(
            '(' + str(cs[3]) + '*(WV**2))+(' + str(cs[4]) + '*WV)+(' + str(cs[5]) + ')',
            {
                'WV': img.select('WV_SCALED')
            }
        ).rename('AF2')

        af3 = img.expression(
            '(' + str(cs[6]) + '*(WV**2))+(' + str(cs[7]) + '*WV)+(' + str(cs[8]) + ')',
            {
                'WV': img.select('WV_SCALED')
            }
        ).rename('AF3')

        return img.addBands(af1).addBands(af2).addBands(af3)
    return wrap


def scale_wv(img):
    wv_scaled = ee.Image(img.get('WV')).multiply(0.1).rename('WV_SCALED')
    wv_scaled = wv_scaled.resample('bilinear')
    return img.addBands(wv_scaled)


def radcal(img):
    radiance = ee.Algorithms.Landsat.calibratedRadiance(img).rename('RADIANCE')
    return img.addBands(radiance)


# L to ee.Image
def radiance_addband(img):
    l = ee.Image(img.get('L')).select('RADIANCE').rename('L')
    return img.addBands(l)