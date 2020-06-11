import ee
from .atmospheric_functions import atmospheric_functions, radiance_addband, scale_wv
from .collection_matching import maxDiffFilter, join_wv
from .land_surface_temperatue import delta, gamma


def apply_lst_prepro(imgCol_L5_SR, imgCol_L7_SR, imgCol_L8_SR, imgCol_WV):

    imgCol_L5_SR = imgCol_L5_SR.map(radiance_addband)
    imgCol_L7_SR = imgCol_L7_SR.map(radiance_addband)
    imgCol_L8_SR = imgCol_L8_SR.map(radiance_addband)

    # Water Vapor
    imgCol_L5_SR = ee.ImageCollection(join_wv.apply(imgCol_L5_SR, imgCol_WV, maxDiffFilter))
    imgCol_L7_SR = ee.ImageCollection(join_wv.apply(imgCol_L7_SR, imgCol_WV, maxDiffFilter))
    imgCol_L8_SR = ee.ImageCollection(join_wv.apply(imgCol_L8_SR, imgCol_WV, maxDiffFilter))

    imgCol_L5_SR = imgCol_L5_SR.map(scale_wv)
    imgCol_L7_SR = imgCol_L7_SR.map(scale_wv)
    imgCol_L8_SR = imgCol_L8_SR.map(scale_wv)

    # Atmospheric Functions
    imgCol_L5_SR = imgCol_L5_SR.map(atmospheric_functions(sensor='L5'))
    imgCol_L7_SR = imgCol_L7_SR.map(atmospheric_functions(sensor='L7'))
    imgCol_L8_SR = imgCol_L8_SR.map(atmospheric_functions(sensor='L8'))

    # Delta and Gamma Functions
    imgCol_L5_SR = imgCol_L5_SR.map(delta(1256))
    imgCol_L7_SR = imgCol_L7_SR.map(delta(1277))
    imgCol_L8_SR = imgCol_L8_SR.map(delta(1324))

    imgCol_L5_SR = imgCol_L5_SR.map(gamma(1256))
    imgCol_L7_SR = imgCol_L7_SR.map(gamma(1277))
    imgCol_L8_SR = imgCol_L8_SR.map(gamma(1324))

    return imgCol_L5_SR, imgCol_L7_SR, imgCol_L8_SR

