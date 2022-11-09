from cpython.dict cimport (
    PyDict_Contains,
    PyDict_GetItem,
    PyDict_SetItem,
)
from cython cimport Py_ssize_t

cdef class AxisProperty:

    cdef readonly:
        Py_ssize_t axis
        object __doc__

    def __init__(self, axis=0, doc=""):
        self.axis = axis
        self.__doc__ = doc

    def __get__(self, obj, type):
        cdef:
            list axes

        if obj is None:
            # Only instances have _mgr, not classes
            return self
        else:
            axes = obj._mgr.axes
        return axes[self.axis]

    def __set__(self, obj, value):
        obj._set_axis(self.axis, value)
