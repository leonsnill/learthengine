import ee
import datetime


def last_day_of_month(any_day):
    next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
    return next_month - datetime.timedelta(days=next_month.day)


def time_filter(l_years=None, l_months=None, l_doys=None, doy_offset=None):
    # initialize
    temp_filter = []
    l_years = [l_years] if isinstance(l_years, int) else l_years
    l_months = [l_months] if isinstance(l_months, int) else l_months
    l_doys = [l_doys] if isinstance(l_doys, int) else l_doys

    min_year = min(l_years)
    max_year = max(l_years)

    for y in range(min_year, max_year + 1):
        # (1) DOY option
        if l_doys is not None:

            if doy_offset is None:
                doy_offset = 1

            for doy in l_doys:
                temp_target_doy = datetime.datetime(y, 1, 1) + datetime.timedelta(doy - 1)
                temp_min_date = (temp_target_doy - datetime.timedelta(doy_offset - 1)).strftime('%Y-%m-%d')
                temp_max_date = (temp_target_doy + datetime.timedelta(doy_offset - 1)).strftime('%Y-%m-%d')
                temp_filter.append(ee.Filter.date(temp_min_date, temp_max_date))

        else:

            if l_months is None:
                min_date = str(y) + "-01-01"
                max_date = str(y) + "-12-31"
                temp_filter.append(ee.Filter.date(min_date, max_date))
            else:
                for m in l_months:
                    min_date = str(y) + "-" + str(m) + "-01"
                    max_date = last_day_of_month(datetime.date(y, m, 1)).strftime('%Y-%m-%d')
                    temp_filter.append(ee.Filter.date(min_date, max_date))

    return ee.Filter.Or(*temp_filter)

