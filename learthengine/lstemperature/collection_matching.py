import ee


# Create maxDifference-filter to match TOA and SR products
maxDiffFilter = ee.Filter.maxDifference(
    difference=2 * 24 * 60 * 60 * 1000,
    leftField= 'system:time_start',
    rightField= 'system:time_start'
)

# Define join: Water vapor
join_wv = ee.Join.saveBest(
    matchKey = 'WV',
    measureKey = 'timeDiff'
)

# Define join: Radiance
join_l = ee.Join.saveBest(
    matchKey = 'L',
    measureKey = 'timeDiff'
)
