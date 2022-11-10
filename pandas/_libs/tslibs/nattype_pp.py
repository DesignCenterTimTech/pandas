import pandas._libs.tslibs.util_pp as util_pp

from pandas._libs.tslibs.nattype import (
    NaT,
    iNaT as NPY_NAT,
)

from pandas._libs.tslibs.np_datetime_pp import (
    get_datetime64_value,
    # get_timedelta64_value,
)

def checknull_with_nat(val):
    """
    Utility to check if a value is a nat or not.
    """
    return val is None or util_pp.is_nan(val) or val is NaT

def is_dt64nat(val):
    """
    Is this a np.datetime64 object np.datetime64("NaT").
    """
    if util_pp.is_datetime64_object(val):
        return get_datetime64_value(val) == NPY_NAT
    return False
