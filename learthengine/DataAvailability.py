import ee
ee.Initialize()

import numpy as np
import pandas as pd


sel_roi = ee.Geometry.Rectangle([21.68, -20.39, 23.72, -18.14])
cloud_cover = 50
year_start = 2018
year_end = 2018
month_start = 1
month_end = 12


imgCol_L8_SR = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR')\
    .filterBounds(sel_roi)\
    .filter(ee.Filter.calendarRange(year_start, year_end, 'year'))\
    .filter(ee.Filter.calendarRange(month_start, month_end, 'month'))\
    .filter(ee.Filter.lt('CLOUD_COVER_LAND', cloud_cover))

imgCol_L8_TOA = ee.ImageCollection('LANDSAT/LC08/C01/T1_TOA')\
    .filterBounds(sel_roi)\
    .filter(ee.Filter.calendarRange(year_start, year_end, 'year'))\
    .filter(ee.Filter.calendarRange(month_start, month_end, 'month'))\
    .filter(ee.Filter.lt('CLOUD_COVER_LAND', cloud_cover))

imgCol_S2_L1C = ee.ImageCollection('COPERNICUS/S2')\
    .filterBounds(sel_roi)\
    .filter(ee.Filter.calendarRange(year_start, year_end, 'year'))\
    .filter(ee.Filter.calendarRange(month_start, month_end, 'month'))\
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_cover))

imgCol_S2_L2A = ee.ImageCollection('COPERNICUS/S2')\
    .filterBounds(sel_roi)\
    .filter(ee.Filter.calendarRange(year_start, year_end, 'year'))\
    .filter(ee.Filter.calendarRange(month_start, month_end, 'month'))\
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', cloud_cover))


def ymdList(imgCol):
    def iter_func(image, newlist):
        date = ee.Number.parse(image.date().format("YYYYMMdd"))
        newlist = ee.List(newlist)
        return ee.List(newlist.add(date).sort())
    return imgCol.iterate(iter_func, ee.List([]))


# ---------------------------------------------------------------------------------------------------- #
# Retrieve sensor specific unique dates
# ---------------------------------------------------------------------------------------------------- #
L8SR_list = np.unique(ymdList(imgCol_L8_SR).getInfo())
L8TOA_list = np.unique(ymdList(imgCol_L8_TOA).getInfo())
L1C_list = np.unique(ymdList(imgCol_S2_L1C).getInfo())
L2A_list = np.unique(ymdList(imgCol_S2_L2A).getInfo())


# ---------------------------------------------------------------------------------------------------- #
# Create bar-chart of dates
# ---------------------------------------------------------------------------------------------------- #
sel_list = pd.DataFrame(L1C_list, columns=['date'])

sel_list['date'] = pd.to_datetime(sel_list['date'].astype(str), format='%Y%m%d')
month_count = pd.DataFrame(sel_list.groupby([sel_list['date'].dt.month]).agg({'count'}), columns=[('date', 'count')])

import matplotlib.pyplot as plt
import matplotlib as mpl

mpl.rcParams['font.size'] = 14
ax = month_count.plot.bar(legend=False, rot=0, color='b')
ax.set_xlabel('Month')
ax.set_ylabel('Image count')
#plt.show()

plt.savefig('/Users/leonnill/Desktop/S2_Scene_Count.png',
            dpi=500)
plt.close()
# ---------------------------------------------------------------------------------------------------- #
# Check for sensor date overlaps
# ---------------------------------------------------------------------------------------------------- #
BOA_list = []
for e in L8SR_list:
    if e in L2A_list:
        BOA_list.append(e)

TOA_list = []
for e in L8TOA_list:
    if e in L1C_list:
        TOA_list.append(e)
