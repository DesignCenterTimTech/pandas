from collections import abc
from decimal import Decimal
from enum import Enum
import inspect
from typing import Literal
import warnings

# from pandas.util._exceptions import find_stack_level

import datetime

import numpy as np


from pandas._libs.tslibs import util_pp
from pandas._libs.util_pp import (
    # INT64_MAX,
    # INT64_MIN,
    # UINT64_MAX,
    is_nan,
)

# from pandas._libs.tslib import array_to_datetime
# from pandas._libs.tslibs import (
#     OutOfBoundsDatetime,
#     OutOfBoundsTimedelta,
# )
from pandas._libs.tslibs.period import Period

from pandas._libs.missing import (
    NA as C_NA,
    NA,
    # checknull,
    # is_matching_na,
    # is_null_datetime64,
    # is_null_timedelta64,
)
from pandas._libs.missing_pp import (
    is_null_datetime64,
)

# from pandas._libs.tslibs.conversion import convert_to_tsobject
from pandas._libs.tslibs.nattype import (
    # NPY_NAT,
    iNaT as NPY_NAT,
    NaT,
#     checknull_with_nat,
)
from pandas._libs.tslibs.nattype_pp import (
    checknull_with_nat
)

# from pandas._libs.tslibs.offsets import is_offset_object

# from pandas._libs.tslibs.period import is_period_object
def is_period_object(obj):
    return isinstance(obj, Period)

# from pandas._libs.tslibs.timedeltas import convert_to_timedelta64
# from pandas._libs.tslibs.timezones import tz_compare


_TYPE_MAP = {
    "categorical": "categorical",
    "category": "categorical",
    "int8": "integer",
    "int16": "integer",
    "int32": "integer",
    "int64": "integer",
    "i": "integer",
    "uint8": "integer",
    "uint16": "integer",
    "uint32": "integer",
    "uint64": "integer",
    "u": "integer",
    "float32": "floating",
    "float64": "floating",
    "f": "floating",
    "complex64": "complex",
    "complex128": "complex",
    "c": "complex",
    "string": "string",
    str: "string",
    "S": "bytes",
    "U": "string",
    "bool": "boolean",
    "b": "boolean",
    "datetime64[ns]": "datetime64",
    "M": "datetime64",
    "timedelta64[ns]": "timedelta64",
    "m": "timedelta64",
    "interval": "interval",
    Period: "period",
}

def _try_infer_map(dtype):
    """
    If its in our map, just return the dtype.
    """
    for attr in ["name", "kind", "base", "type"]:
        val = getattr(dtype, attr, None)
        if val in _TYPE_MAP:
            return _TYPE_MAP[val]
    return None

def infer_dtype(value: object, skipna: bool = True) -> str:
    """
    Return a string label of the type of a scalar or list-like of values.

    Parameters
    ----------
    value : scalar, list, ndarray, or pandas type
    skipna : bool, default True
        Ignore NaN values when inferring the type.

    Returns
    -------
    str
        Describing the common type of the input data.
    Results can include:

    - string
    - bytes
    - floating
    - integer
    - mixed-integer
    - mixed-integer-float
    - decimal
    - complex
    - categorical
    - boolean
    - datetime64
    - datetime
    - date
    - timedelta64
    - timedelta
    - time
    - period
    - mixed
    - unknown-array

    Raises
    ------
    TypeError
        If ndarray-like but cannot infer the dtype

    Notes
    -----
    - 'mixed' is the catchall for anything that is not otherwise
      specialized
    - 'mixed-integer-float' are floats and integers
    - 'mixed-integer' are integers mixed with non-integers
    - 'unknown-array' is the catchall for something that *is* an array (has
      a dtype attribute), but has a dtype unknown to pandas (e.g. external
      extension array)

    Examples
    --------
    >>> import datetime
    >>> infer_dtype(['foo', 'bar'])
    'string'

    >>> infer_dtype(['a', np.nan, 'b'], skipna=True)
    'string'

    >>> infer_dtype(['a', np.nan, 'b'], skipna=False)
    'mixed'

    >>> infer_dtype([b'foo', b'bar'])
    'bytes'

    >>> infer_dtype([1, 2, 3])
    'integer'

    >>> infer_dtype([1, 2, 3.5])
    'mixed-integer-float'

    >>> infer_dtype([1.0, 2.0, 3.5])
    'floating'

    >>> infer_dtype(['a', 1])
    'mixed-integer'

    >>> infer_dtype([Decimal(1), Decimal(2.0)])
    'decimal'

    >>> infer_dtype([True, False])
    'boolean'

    >>> infer_dtype([True, False, np.nan])
    'boolean'

    >>> infer_dtype([pd.Timestamp('20130101')])
    'datetime'

    >>> infer_dtype([datetime.date(2013, 1, 1)])
    'date'

    >>> infer_dtype([np.datetime64('2013-01-01')])
    'datetime64'

    >>> infer_dtype([datetime.timedelta(0, 1, 1)])
    'timedelta'

    >>> infer_dtype(pd.Series(list('aabc')).astype('category'))
    'categorical'
    """

    if util_pp.is_array(value):
        values = value
    elif hasattr(value, "inferred_type") and skipna is False:
        # Index, use the cached attribute if possible, populate the cache otherwise
        return value.inferred_type
    elif hasattr(value, "dtype"):
        # this will handle ndarray-like
        # e.g. categoricals
        dtype = value.dtype
        if not isinstance(dtype, np.dtype):
            inferred = _try_infer_map(value.dtype)
            if inferred is not None:
                return inferred
            return "unknown-array"

        # Unwrap Series/Index
        values = np.asarray(value)

    else:
        if not isinstance(value, list):
            value = list(value)

        from pandas.core.dtypes.cast import construct_1d_object_array_from_listlike
        values = construct_1d_object_array_from_listlike(value)

    val = _try_infer_map(values.dtype)
    if val is not None:
        # Anything other than object-dtype should return here.
        return val

    if values.dtype != np.object:
        # This should not be reached
        values = values.astype(object)

    n = np.size(values)
    if n == 0:
        return "empty"

    # Iterate until we find our first valid value. We will use this
    #  value to decide which of the is_foo_array functions to call.
    for i in range(n):
        val = values[i]

        # do not use checknull to keep
        # np.datetime64('nat') and np.timedelta64('nat')
        if val is None or util_pp.is_nan(val) or val is C_NA:
            pass
        elif val is NaT:
            seen_pdnat = True
        else:
            seen_val = True
            break

    # if all values are nan/NaT
    if seen_val is False and seen_pdnat is True:
        return "datetime"
        # float/nan is handled in latter logic
    if seen_val is False and skipna:
        return "empty"

    if util_pp.is_datetime64_object(val):
        if is_datetime64_array(values, skipna=skipna):
            return "datetime64"

    elif is_timedelta(val):
        if is_timedelta_or_timedelta64_array(values, skipna=skipna):
            return "timedelta"

    elif util_pp.is_integer_object(val):
        # ordering matters here; this check must come after the is_timedelta
        #  check otherwise numpy timedelta64 objects would come through here

        if is_integer_array(values, skipna=skipna):
            return "integer"
        elif is_integer_float_array(values, skipna=skipna):
            if is_integer_na_array(values, skipna=skipna):
                return "integer-na"
            else:
                return "mixed-integer-float"
        return "mixed-integer"

    # elif PyDateTime_Check(val):
    elif isinstance(val, datetime.datetime):
        if is_datetime_array(values, skipna=skipna):
            return "datetime"
        elif is_date_array(values, skipna=skipna):
            return "date"

    # elif PyDate_Check(val):
    elif isinstance(val, datetime.date):
        if is_date_array(values, skipna=skipna):
            return "date"

    # elif PyTime_Check(val):
    elif isinstance(val, datetime.time):
        if is_time_array(values, skipna=skipna):
            return "time"

    elif is_decimal(val):
        if is_decimal_array(values, skipna=skipna):
            return "decimal"

    elif util_pp.is_complex_object(val):
        if is_complex_array(values):
            return "complex"

    elif util_pp.is_float_object(val):
        if is_float_array(values):
            return "floating"
        elif is_integer_float_array(values, skipna=skipna):
            if is_integer_na_array(values, skipna=skipna):
                return "integer-na"
            else:
                return "mixed-integer-float"

    elif util_pp.is_bool_object(val):
        if is_bool_array(values, skipna=skipna):
            return "boolean"

    elif isinstance(val, str):
        if is_string_array(values, skipna=skipna):
            return "string"

    elif isinstance(val, bytes):
        if is_bytes_array(values, skipna=skipna):
            return "bytes"

    elif is_period_object(val):
        if is_period_array(values, skipna=skipna):
            return "period"

    elif is_interval(val):
        if is_interval_array(values):
            return "interval"

    for i in range(n):
        val = values[i]

        if util_pp.is_integer_object(val):
            return "mixed-integer"

    return "mixed"

def is_timedelta(o):
    # FIXME: PyDelta_Check() pure python alternative?
    # return PyDelta_Check(o) or util_pp.is_timedelta64_object(o)
    return util_pp.is_timedelta64_object(o)

class Validator:
    def __init__(self, n, dtype=np.dtype(np.object_),
                  skipna=False):
        self.n = n
        self.dtype = dtype
        self.skipna = skipna

    def validate(self, values):
        if not self.n:
            return False

        if self.is_array_typed():
            # i.e. this is already of the desired dtype
            return True
        elif isinstance(self.dtype, np.dtype):
            if self.skipna:
                return self._validate_skipna(values)
            else:
                return self._validate(values)
        else:
            return False

    def _validate(self, values):
        n = values.size
        for i in range(n):
            val = values[i]
            if not self.is_valid(val):
                return False
        return True

    def _validate_skipna(self, values):
        n = values.size
        for i in range(n):
            val = values[i]
            if not self.is_valid_skipna(val):
                return False

        return True

    def is_valid(self, value):
        return self.is_value_typed(value)

    def is_valid_skipna(self, value):
        return self.is_valid(value) or self.is_valid_null(value)

    def is_value_typed(self, value):
        raise NotImplementedError(f"{type(self).__name__} child class "
                                  "must define is_value_typed")

    def is_valid_null(self, value):
        return value is None or value is C_NA or util_pp.is_nan(value)

    def is_array_typed(self):
        return False

class TemporalValidator(Validator):
    def __init__(self, n, dtype=np.dtype(np.object_),
                 skipna=False):
        self.n = n
        self.dtype = dtype
        self.skipna = skipna
        self.all_generic_na = True

    def is_valid(self, value):
        return self.is_value_typed(value) or self.is_valid_null(value)

    def is_valid_null(self, value):
        raise NotImplementedError(f"{type(self).__name__} child class "
                                  "must define is_valid_null")

    def is_valid_skipna(self, value):
        is_typed_null = self.is_valid_null(value)
        is_generic_null = value is None or util_pp.is_nan(value)
        if not is_generic_null:
            self.all_generic_na = False
        return self.is_value_typed(value) or is_typed_null or is_generic_null

    def _validate_skipna(self, values):
        """
        If we _only_ saw non-dtype-specific NA values, even if they are valid
        for this dtype, we do not infer this dtype.
        """
        return Validator._validate_skipna(self, values) and not self.all_generic_na

class DatetimeValidator(TemporalValidator):
    def is_value_typed(self, value):
        # return PyDateTime_Check(value)
        return isinstance(value, datetime.datetime)

    def is_valid_null(self, value):
        return is_null_datetime64(value)

def is_datetime_array( values, skipna=True):
    validator = DatetimeValidator(len(values), skipna=skipna)
    return validator.validate(values)

class Datetime64Validator(DatetimeValidator):
    def is_value_typed(self, value):
        return util_pp.is_datetime64_object(value)

def is_datetime64_array(values, skipna=True):
    return Datetime64Validator(len(values), skipna=skipna).validate(values)

class TimedeltaValidator(TemporalValidator):
    def is_value_typed(self, value):
        # return PyDelta_Check(value)
        return isinstance(value, datetime.timedelta)

    def is_valid_null(self, value):
        return is_null_timedelta64ADDME(value)

class AnyTimedeltaValidator(TimedeltaValidator):
    def is_value_typed(self, value):
        return is_timedelta(value)

def is_timedelta_or_timedelta64_array(values, skipna=True):
    """
    Infer with timedeltas and/or nat/none.
    """
    validator = AnyTimedeltaValidator(len(values), skipna=skipna)
    return validator.validate(values)

class DateValidator(Validator):
    def is_value_typed(self, value):
        # return PyDate_Check(value)
        return isinstance(value, datetime.date)

# Note: only python-exposed for tests
def is_date_array(values, skipna=False):
    validator = DateValidator(len(values), skipna=skipna)
    return validator.validate(values)

class TimeValidator(Validator):
    def is_value_typed(self, value):
        # return PyTime_Check(value)
        return isinstance(value, datetime.time)


# Note: only python-exposed for tests
def is_time_array(values, skipna=False):
    validator = TimeValidator(len(values), skipna=skipna)
    return validator.validate(values)


def is_interval(obj):
    return getattr(obj, '_typ', '_typ') == 'interval'

def is_decimal(obj):
    return isinstance(obj, Decimal)

class IntegerValidator(Validator):
    def is_value_typed(self, value):
        return util_pp.is_integer_object(value)

    def is_array_typed(self):
        return issubclass(self.dtype.type, np.integer)


# Note: only python-exposed for tests
def is_integer_array(values, skipna=True):
    validator = IntegerValidator(len(values),
                                                      values.dtype,
                                                      skipna=skipna)
    return validator.validate(values)

class IntegerNaValidator(Validator):
    def is_value_typed(self, value):
        return (util_pp.is_integer_object(value)
                or (util_pp.is_nan(value) and util_pp.is_float_object(value)))


def is_integer_na_array(values, skipna=True):
    validator = IntegerNaValidator(len(values), values.dtype, skipna=skipna)
    return validator.validate(values)



class IntegerFloatValidator(Validator):
    def is_value_typed(self, value):
        return util_pp.is_integer_object(value) or util_pp.is_float_object(value)

    def is_array_typed(self):
        return issubclass(self.dtype.type, np.integer)


def is_integer_float_array(values, skipna=True):
    validator = IntegerFloatValidator(len(values),
                                                                values.dtype,
                                                                skipna=skipna)
    return validator.validate(values)

class FloatValidator(Validator):
    def is_value_typed(self, value):
        return util_pp.is_float_object(value)

    def is_array_typed(self):
        return issubclass(self.dtype.type, np.floating)

# Note: only python-exposed for tests
def is_float_array(values):
    validator = FloatValidator(len(values), values.dtype)
    return validator.validate(values)

class ComplexValidator(Validator):
    def is_value_typed(self, value):
        return (
            util_pp.is_complex_object(value)
            or (util_pp.is_float_object(value) and is_nan(value))
        )

    def is_array_typed(self):
        return issubclass(self.dtype.type, np.complexfloating)

def is_complex_array(values):
    validator = ComplexValidator(len(values), values.dtype)
    return validator.validate(values)

class DecimalValidator(Validator):
    def is_value_typed(self, value):
        return is_decimal(value)

def is_decimal_array(values, skipna=False):
    validator = DecimalValidator(
            len(values), values.dtype, skipna=skipna
        )
    return validator.validate(values)

class StringValidator(Validator):
    def is_value_typed(self, value):
        return isinstance(value, str)

    def is_array_typed(self):
        return issubclass(self.dtype.type, np.str_)

def is_string_array(values, skipna=False):
    validator = StringValidator(len(values),
                                                    values.dtype,
                                                    skipna=skipna)
    return validator.validate(values)

class BytesValidator(Validator):
    def is_value_typed(self, value):
        return isinstance(value, bytes)

    def is_array_typed(self):
        return issubclass(self.dtype.type, np.bytes_)

def is_bytes_array(values, skipna=False):
    validator = BytesValidator(len(values), values.dtype,
                                                  skipna=skipna)
    return validator.validate(values)

class BoolValidator(Validator):
    def is_value_typed(self, value):
        return util_pp.is_bool_object(value)

    def is_array_typed(self):
        return issubclass(self.dtype.type, np.bool_)


def is_bool_array(values, skipna=False):
    validator = BoolValidator(len(values),
                                                values.dtype,
                                                skipna=skipna)
    return validator.validate(values)

# FIXME: actually use skipna
def is_period_array(values, skipna=True):
    """
    Is this an of Period objects (or NaT) with a single `freq`?
    """
    # values should be object-dtype, but ndarray[object] assumes 1D, while
    #  this _may_ be 2D.
    N = values.size
    dtype_code = -10000  # i.e. c_FreqGroup.FR_UND

    if N == 0:
        return False

    for i in range(N):
        val = values[i]

        if is_period_object(val):
            if dtype_code == -10000:
                dtype_code = val._dtype._dtype_code
            elif dtype_code != val._dtype._dtype_code:
                # mismatched freqs
                return False
        elif checknull_with_nat(val):
            pass
        else:
            # Not a Period or NaT-like
            return False

    if dtype_code == -10000:
        # we saw all-NaTs, no actual Periods
        return False
    return True


# Note: only python-exposed for tests
def is_interval_array(values):
    """
    Is this an of Interval (or np.nan) with a single dtype?
    """
    n = len(values)
    closed = None
    numeric = False
    dt64 = False
    td64 = False

    if len(values) == 0:
        return False

    for i in range(n):
        val = values[i]

        if is_interval(val):
            if closed is None:
                closed = val.closed
                numeric = (
                    util_pp.is_float_object(val.left)
                    or util_pp.is_integer_object(val.left)
                )
                td64 = is_timedelta(val.left)
                # dt64 = PyDateTime_Check(val.left)
                dt64 = util_pp.is_datetime64_object(val.left)
            elif val.closed != closed:
                # mismatched closedness
                return False
            elif numeric:
                if not (
                    util_pp.is_float_object(val.left)
                    or util_pp.is_integer_object(val.left)
                ):
                    # i.e. datetime64 or timedelta64
                    return False
            elif td64:
                if not is_timedelta(val.left):
                    return False
            elif dt64:
                # if not PyDateTime_Check(val.left):
                if not util_pp.is_datetime64_object(val.left):
                    return False
            else:
                raise ValueError(val)
        elif util_pp.is_nan(val) or val is None:
            pass
        else:
            return False

    if closed is None:
        # we saw all-NAs, no actual Intervals
        return False
    return True
