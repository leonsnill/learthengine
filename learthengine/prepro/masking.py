import ee


def mask_landsat_sr(masks, T_threshold=None):

    dict_mask = {'cloud': ee.Number(2).pow(5).int(),
                 'cshadow': ee.Number(2).pow(3).int(),
                 'snow': ee.Number(2).pow(4).int()}
    sel_masks = [dict_mask[x] for x in masks]
    bits = ee.Number(1)
    for m in sel_masks:
        bits = ee.Number(bits.add(m))

    if T_threshold is not None:
        def wrap(img):
            qa = img.select('pixel_qa')
            mask = (qa.bitwiseAnd(bits).eq(0)).Not()

            bt = img.select('TIR')
            temp_th = (T_threshold + 273.15) * 10
            bt_mask = bt.lt(temp_th)

            mask = (mask.multiply(bt_mask)).Not()

            return img.updateMask(mask) \
                      .copyProperties(source=img).set('system:time_start', img.get('system:time_start'))
    else:
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
        mask = img_cdi.gt(cdi).rename("mask")
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


def focal_mask(kernelsize=10):
    def wrap(img):
        kernel = ee.Kernel.square(kernelsize, 'pixels')
        mask = img.mask()
        smooth = ee.Kernel.circle(radius=1)
        mask = mask.focal_max({'kernel': smooth, 'iterations': 2})
        mask = mask.focal_min({'kernel': kernel, 'iterations': 2})
        return img.updateMask(mask).copyProperties({'source': img})\
                  .set('system:time_start', img.get('system:time_start'))
    return wrap
