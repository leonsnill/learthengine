import ee
from learthengine import lst, prepro


def apply_lst_prepro(imgCol_L5_SR, imgCol_L7_SR, imgCol_L8_SR, imgCol_WV):

    imgCol_L5_SR = imgCol_L5_SR.map(lst.radiance_addband)
    imgCol_L7_SR = imgCol_L7_SR.map(lst.radiance_addband)
    imgCol_L8_SR = imgCol_L8_SR.map(lst.radiance_addband)

    # Water Vapor
    imgCol_L5_SR = ee.ImageCollection(lst.join_wv.apply(imgCol_L5_SR, imgCol_WV, lst.maxDiffFilter))
    imgCol_L7_SR = ee.ImageCollection(lst.join_wv.apply(imgCol_L7_SR, imgCol_WV, lst.maxDiffFilter))
    imgCol_L8_SR = ee.ImageCollection(lst.join_wv.apply(imgCol_L8_SR, imgCol_WV, lst.maxDiffFilter))

    imgCol_L5_SR = imgCol_L5_SR.map(lst.scale_wv)
    imgCol_L7_SR = imgCol_L7_SR.map(lst.scale_wv)
    imgCol_L8_SR = imgCol_L8_SR.map(lst.scale_wv)

    # Atmospheric Functions
    imgCol_L5_SR = imgCol_L5_SR.map(lst.atmospheric_functions(sensor='L5'))
    imgCol_L7_SR = imgCol_L7_SR.map(lst.atmospheric_functions(sensor='L7'))
    imgCol_L8_SR = imgCol_L8_SR.map(lst.atmospheric_functions(sensor='L8'))

    # Delta and Gamma Functions
    imgCol_L5_SR = imgCol_L5_SR.map(lst.delta(1256))
    imgCol_L7_SR = imgCol_L7_SR.map(lst.delta(1277))
    imgCol_L8_SR = imgCol_L8_SR.map(lst.delta(1324))

    imgCol_L5_SR = imgCol_L5_SR.map(lst.gamma(1256))
    imgCol_L7_SR = imgCol_L7_SR.map(lst.gamma(1277))
    imgCol_L8_SR = imgCol_L8_SR.map(lst.gamma(1324))

    return imgCol_L5_SR, imgCol_L7_SR, imgCol_L8_SR

