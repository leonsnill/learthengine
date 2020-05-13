import ee


def mask_landsat_sr(bits):
    def wrap(img):
        qa = img.select('pixel_qa')
        mask = qa.bitwiseAnd(bits).eq(0)
        return img.updateMask(mask) \
                  .copyProperties(source=img).set('system:time_start', img.get('system:time_start'))
    return wrap


def mask_s2_scl(img):
    #mask_kernel = ee.Kernel.square(radius=5)
    scl = img.select('SCL')
    mask = scl.neq(3).And(scl.neq(7)).And(
            scl.neq(8)).And(
            scl.neq(9)).And(
            scl.neq(10)).And(
            scl.neq(11))
    #mask = mask.focal_mode(kernel=mask_kernel, iterations=1).rename('CLOUD')
    return img.addBands(mask).updateMask(mask)\
              .copyProperties(source=img).set('system:time_start', img.get('system:time_start'))


def mask_s2_cdi(cdi=-0.5):
    def wrap(img):
        img_cdi = ee.Algorithms.Sentinel2.CDI(img)
        mask = img_cdi.lt(cdi).rename("mask")
        return img.addBands(mask).updateMask(mask) \
           .copyProperties(source=img).set('system:time_start', img.get('system:time_start'))
    return wrap


def mask_s2(img):
    qa = img.select('QA60')
    cloudBitMask = ee.Number(2).pow(10).int()
    cirrusBitMask = ee.Number(2).pow(11).int()
    mask = qa.bitwiseAnd(cloudBitMask).eq(0).And(qa.bitwiseAnd(cirrusBitMask).eq(0)).rename('CLOUD')
    return img.addBands(mask).updateMask(mask)\
              .copyProperties(source=img).set('system:time_start', img.get('system:time_start'))

