from pandas._libs.tslibs.nattype_pp import (
    checknull_with_nat,
    is_dt64nat,
    # is_td64nat,
)

def is_null_datetime64(v):
    # determine if we have a null for a datetime (or integer versions),
    # excluding np.timedelta64('nat')
    if checknull_with_nat(v) or is_dt64nat(v):
        return True
    return False
