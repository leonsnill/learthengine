import ee


def mask_landsat_sr(masks, T_threshold=None, omission=True):

    dict_mask = {'cloud': ee.Number(2).pow(5).int(),
                 'cshadow': ee.Number(2).pow(3).int(),
                 'snow': ee.Number(2).pow(4).int()}

    if T_threshold is not None:

        if omission:
            sel_masks = [dict_mask[x] for x in masks if x != 'cloud']
            bits = ee.Number(1)
            for m in sel_masks:
                bits = ee.Number(bits.add(m))

            def wrap(img):
                qa = img.select('pixel_qa')

                cloudbit = ee.Number(2).pow(5).int()
                cloudmask = (qa.bitwiseAnd(cloudbit).eq(0)).Not()

                bt = img.select('TIR')
                temp_th = (T_threshold + 273.15) * 10
                bt_mask = bt.lt(temp_th)  # 1 cloud, 0 clear

                bt_mask = (cloudmask.multiply(bt_mask)).Not()
                mask = (qa.bitwiseAnd(bits).eq(0)).And(bt_mask)

                return img.updateMask(mask) \
                    .copyProperties(source=img).set('system:time_start', img.get('system:time_start'))
        # comission
        else:
            sel_masks = [dict_mask[x] for x in masks]
            bits = ee.Number(1)
            for m in sel_masks:
                bits = ee.Number(bits.add(m))

            def wrap(img):
                qa = img.select('pixel_qa')
                mask = qa.bitwiseAnd(bits).eq(0)

                bt = img.select('TIR')
                temp_th = (T_threshold + 273.15) * 10
                bt_mask = bt.gt(temp_th)  # 1 clear, 0 cloud

                mask = mask.multiply(bt_mask)

                return img.updateMask(mask) \
                    .copyProperties(source=img).set('system:time_start', img.get('system:time_start'))
    else:
        sel_masks = [dict_mask[x] for x in masks]
        bits = ee.Number(1)
        for m in sel_masks:
            bits = ee.Number(bits.add(m))
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


def focal_mask(kernelsize=1.5):
    def wrap(img):
        kernel = ee.Kernel.square(radius=kernelsize, units='pixels')
        mask = img.mask().select('R')
        mask = mask.focal_mode({'kernel': kernel, 'iterations': 1})
        return img.updateMask(mask).copyProperties({'source': img})\
                  .set('system:time_start', img.get('system:time_start'))
    return wrap


def mask_percentiles(band_lwr='R', band_upr='B', lwr=ee.Image(1), upr=ee.Image(1)):
    def wrap(img):
        mask = lwr.where(img.expression('band < lower', {
            'band': img.select(band_lwr),
            'lower': lwr}), 0)
        mask = mask.where(img.expression('band > lower', {
            'band': img.select(band_lwr),
            'lower': lwr}), 1)
        mask = mask.where(img.expression('band > upper', {
            'band': img.select(band_upr),
            'upper': upr}), 0)
        return img.updateMask(mask) \
            .copyProperties(source=img).set('system:time_start', img.get('system:time_start'))
    return wrap


def mask_cloudbuffer(min_distance):
    def wrap(img):
        cloud_distance = img.select('CLOUD_DISTANCE')
        mask = cloud_distance.gte(min_distance)
        return img.updateMask(mask) \
            .copyProperties(source=img).set('system:time_start', img.get('system:time_start'))
    return wrap


#################################################################################
#https://github.com/gee-community/gee_tools
# (c) Rodrigo Principe

def removeDuplicates(eelist):
    """ Remove duplicated values from a EE list object """
    # TODO: See ee.List.distinct()
    newlist = ee.List([])
    def wrap(element, init):
        init = ee.List(init)
        contained = init.contains(element)
        return ee.Algorithms.If(contained, init, init.add(element))
    return ee.List(eelist.iterate(wrap, newlist))


def binary(conditions, classes, mask_name='dt_mask'):

    cond = ee.Dictionary(conditions)
    paths = ee.Dictionary(classes)

    def C(condition, bool):
        # b = ee.Number(bool)
        return ee.Image(ee.Algorithms.If(bool, ee.Image(condition),
                                         ee.Image(condition).Not()))

    # function to iterate over the path (classes)
    def overpath(key, path):
        v = ee.List(path) # the path is a list of lists
        # define an intial image = 1 with one band with the name of the class
        ini = ee.Image.constant(1).select([0], [key])

        # iterate over the path (first arg is a pair: [cond, bool])
        def toiterate(pair, init):
            init = ee.Image(init)
            pair = ee.List(pair)
            boolean = pair.get(1)
            condition_key = pair.get(0)  # could need var casting
            condition = cond.get(condition_key)
            final_condition = C(condition, boolean)
            return ee.Image(init.And(ee.Image(final_condition)))

        result = ee.Image(v.iterate(toiterate, ini))
        return result

    new_classes = ee.Dictionary(paths.map(overpath))

    # UNIFY CLASSES. example: {'snow-1':x, 'snow-2':y} into {'snow': x.and(y)}
    new_classes_list = new_classes.keys()

    def mapclasses(el):
        return ee.String(el).split('-').get(0)

    repeated = new_classes_list.map(mapclasses)

    unique = removeDuplicates(repeated)

    # CREATE INITIAL DICT
    def createinitial(baseclass, ini):
        ini = ee.Dictionary(ini)
        i = ee.Image.constant(0).select([0], [baseclass])
        return ini.set(baseclass, i)

    ini = ee.Dictionary(unique.iterate(createinitial, ee.Dictionary({})))

    def unify(key, init):
        init = ee.Dictionary(init)
        baseclass = ee.String(key).split('-').get(0)
        mask_before = ee.Image(init.get(baseclass))
        mask = new_classes.get(key)
        new_mask = mask_before.Or(mask)
        return init.set(baseclass, new_mask)

    new_classes_unique = ee.Dictionary(new_classes_list.iterate(unify, ini))

    masks = new_classes_unique.values() # list of masks

    # Return an Image with one band per option

    def tomaskimg(mask, ini):
        ini = ee.Image(ini)
        return ini.addBands(mask)

    mask_img = ee.Image(masks.slice(1).iterate(tomaskimg,
                                               ee.Image(masks.get(0))))
    # print(mask_img)

    init = ee.Image.constant(0).rename(mask_name)

    def iterate_results(mask, ini):
        ini = ee.Image(ini)
        return ini.Or(mask)

    result = masks.iterate(iterate_results, init)

    not_mask = ee.Image(result).Not()

    return mask_img.addBands(not_mask)


def hollsteinMask(image,
                  options=('cloud', 'snow', 'shadow', 'water', 'cirrus'),
                  aerosol='B1', blue='B2', green='B3', red_edge1='B5',
                  red_edge2='B6', red_edge3='B7', red_edge4='B8A',
                  water_vapor='B9', cirrus='B10', swir='B11',
                  name='hollstein'):
    """ Get Hollstein mask """
    def difference(a, b):
        def wrap(img):
            return img.select(a).subtract(img.select(b))
        return wrap

    def ratio(a, b):
        def wrap(img):
            return img.select(a).divide(img.select(b))
        return wrap

    # 1
    b3 = image.select(green).lt(3190)

    # 2
    b8a = image.select(red_edge4).lt(1660)
    r511 = ratio(red_edge1, swir)(image).lt(4.33)

    # 3
    s1110 = difference(swir, cirrus)(image).lt(2550)
    b3_3 = image.select(green).lt(5250)
    r210 = ratio(blue, cirrus)(image).lt(14.689)
    s37 = difference(green, red_edge3)(image).lt(270)

    # 4
    r15 = ratio(aerosol, red_edge1)(image).lt(1.184)
    s67 = difference(red_edge2, red_edge3)(image).lt(-160)
    b1 = image.select(aerosol).lt(3000)
    r29 =  ratio(blue, water_vapor)(image).lt(0.788)
    s911 = difference(water_vapor, swir)(image).lt(210)
    s911_2 = difference(water_vapor, swir)(image).lt(-970)

    snow = {'snow':[['1',0], ['22',0], ['34',0]]}
    cloud = {'cloud-1':[['1',0], ['22',1],['33',1],['44',1]],
             'cloud-2':[['1',0], ['22',1],['33',0],['45',0]]}
    cirrus = {'cirrus-1':[['1',0], ['22',1],['33',1],['44',0]],
              'cirrus-2':[['1',1], ['21',0],['32',1],['43',0]]}
    shadow = {'shadow-1':[['1',1], ['21',1],['31',1],['41',0]],
              'shadow-2':[['1',1], ['21',1],['31',0],['42',0]],
              'shadow-3':[['1',0], ['22',0],['34',1],['46',0]]}
    water = {'water':[['1',1], ['21',1],['31',0],['42',1]]}

    all = {'cloud':cloud,
           'snow': snow,
           'shadow':shadow,
           'water':water,
           'cirrus':cirrus}

    final = {}

    for option in options:
        final.update(all[option])

    dtf = binary(
        {'1':b3,
         '21':b8a, '22':r511,
         '31':s37, '32':r210, '33':s1110, '34':b3_3,
         '41': s911_2, '42':s911, '43':r29, '44':s67, '45':b1, '46':r15
         }, final, name)

    return dtf


def applyHollstein(options=('cloud', 'snow', 'shadow', 'water', 'cirrus'),
                   aerosol='B1', blue='B2', green='B3', red_edge1='B5',
                   red_edge2='B6', red_edge3='B7', red_edge4='B8A',
                   water_vapor='B9', cirrus='B10', swir='B11'):
    def wrap(img):
        """ Apply Hollstein mask """
        mask = hollsteinMask(img, options, aerosol, blue, green, red_edge1,
                             red_edge2, red_edge3, red_edge4, water_vapor,
                             cirrus, swir).select('hollstein')
        return img.updateMask(mask)
    return wrap

#################################################################################

