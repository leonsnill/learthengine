import ee
import numpy as np


def doyscore(doy_std, target_doy):
    def wrap(img):
        DOYSCORE = img.expression(
            'exp(-0.5*pow((DOY-TARGET_DOY)/DOY_STD, 2))',
            {
                'DOY': img.select('DOY'),
                'DOY_STD': doy_std,
                'TARGET_DOY': target_doy
            }
        ).rename('DOYSCORE')
        DOYSCORE = DOYSCORE.multiply(10000)
        return img.addBands(DOYSCORE)
    return wrap


def doyscore_offset(DOY, TARGET_DOY, DOY_STD):
    return np.exp(-0.5 * pow((DOY - TARGET_DOY) / DOY_STD, 2))


def yearscore(target_years_obj, doyscore_offset_obj):
    def wrap(img):
        YEAR = ee.Number.parse(img.date().format("YYYY"))
        YEAR_IMG = ee.Algorithms.If(YEAR.eq(target_years_obj),
                                    ee.Image.constant(1).multiply(10000).int().rename('YEARSCORE'),
                                    ee.Image.constant(doyscore_offset_obj).multiply(10000).int().rename('YEARSCORE'))

        return img.addBands(YEAR_IMG)
    return wrap


def cloudscore(req_distance, min_distance):
    def wrap(img):
        cloud_mask = img.mask().select('R')
        cloud_distance = img.select('CLOUD_DISTANCE')

        img_max = ee.Image.constant(req_distance)
        img_min = ee.Image.constant(min_distance)
        c = img_max.subtract(img_min).divide(ee.Image(2))
        b = cloud_distance.min(img_max)
        a = b.subtract(c).multiply(ee.Image(-0.2)).exp()
        e = ee.Image(1).add(a)

        cldDist = ee.Image(1).divide(e)
        masc_inv = cldDist.mask().Not()
        cldDist = cldDist.mask().where(1, cldDist)
        cldDist = cldDist.add(masc_inv)
        cldDist = cldDist.updateMask(cloud_mask).rename('CLOUDSCORE')
        cldDist = cldDist.multiply(10000)
        return img.addBands(cldDist)
    return wrap


def score(w_doyscore, w_yearscore, w_cloudscore):
    def wrap(img):
        SCORE = img.expression(
            'DOYSCORE*W_DOYSCORE + YEARSCORE*W_YEARSCORE + CLOUDSCORE*W_CLOUDSCORE',
            {
                'DOYSCORE': img.select('DOYSCORE'),
                'YEARSCORE': img.select('YEARSCORE'),
                'CLOUDSCORE': img.select('CLOUDSCORE'),
                'W_DOYSCORE': w_doyscore,
                'W_YEARSCORE': w_yearscore,
                'W_CLOUDSCORE': w_cloudscore
            }
        ).rename('SCORE')
        SCORE = SCORE.divide(10000)
        return img.addBands(SCORE)
    return wrap

