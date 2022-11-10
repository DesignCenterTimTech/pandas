import numpy as np

def is_integer_object(obj):
    """
    Parameters
    ----------
    val : object

    Returns
    -------
    is_integer : bool

    Notes
    -----
    This counts np.timedelta64 objects as integers.
    'long' type was unified with 'int' type (see http://www.python.org/dev/peps/pep-0237/)
    """
    return isinstance(obj, (int, np.integer)) and not isinstance(obj, bool)

def is_float_object(obj):
    """
    Parameters
    ----------
    val : object

    Returns
    -------
    is_float : bool
    """
    return isinstance(obj, (float, np.complex_))

def is_complex_object(obj):
    """
    Cython equivalent of `isinstance(val, (complex, np.complex_))`
    """
    return isinstance(obj, (complex, np.complex_))
  
def is_nan(val):
    """
    Check if val is a Not-A-Number float or complex, including
    float('NaN') and np.nan.

    Parameters
    ----------
    val : object

    Returns
    -------
    is_nan : bool
    """
    if is_float_object(val):
        fval = val
        return fval != fval
    return is_complex_object(val) and val != val

def is_timedelta64_object(obj):
    """
    Parameters
    ----------
    val : object

    Returns
    -------
    is_timedelta64 : bool
    """
    return isinstance(obj, np.timedelta64)

def is_datetime64_object(obj):
    """
    Parameters
    ----------
    val : object

    Returns
    -------
    is_datetime64 : bool
    """
    return isinstance(obj, np.datetime64)

def is_array(val):
    """
    Cython equivalent of `isinstance(val, np.ndarray)`

    Parameters
    ----------
    val : object

    Returns
    -------
    is_ndarray : bool
    """
    return isinstance(val, np.ndarray)

def is_bool_object(obj):
    """
    Cython equivalent of `isinstance(val, (bool, np.bool_))`

    Parameters
    ----------
    val : object

    Returns
    -------
    is_bool : bool
    """
    return isinstance(obj, (bool, np.bool_))
