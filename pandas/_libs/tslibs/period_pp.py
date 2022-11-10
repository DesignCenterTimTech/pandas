# from timestamps import Timestamp

# class PeriodMixin:
#     # Methods shared between Period and PeriodArray

#     @property
#     def start_time(self) -> Timestamp:
#         """
#         Get the Timestamp for the start of the period.

#         Returns
#         -------
#         Timestamp

#         See Also
#         --------
#         Period.end_time : Return the end Timestamp.
#         Period.dayofyear : Return the day of year.
#         Period.daysinmonth : Return the days in that month.
#         Period.dayofweek : Return the day of the week.

#         Examples
#         --------
#         >>> period = pd.Period('2012-1-1', freq='D')
#         >>> period
#         Period('2012-01-01', 'D')

#         >>> period.start_time
#         Timestamp('2012-01-01 00:00:00')

#         >>> period.end_time
#         Timestamp('2012-01-01 23:59:59.999999999')
#         """
#         return self.to_timestamp(how="start")

#     @property
#     def end_time(self) -> Timestamp:
#         """
#         Get the Timestamp for the end of the period.

#         Returns
#         -------
#         Timestamp

#         See Also
#         --------
#         Period.start_time : Return the start Timestamp.
#         Period.dayofyear : Return the day of year.
#         Period.daysinmonth : Return the days in that month.
#         Period.dayofweek : Return the day of the week.
#         """
#         return self.to_timestamp(how="end")

#     def _require_matching_freq(self, other, base=False):
#         # See also arrays.period.raise_on_incompatible
#         if is_offset_object(other):
#             other_freq = other
#         else:
#             other_freq = other.freq

#         if base:
#             condition = self.freq.base != other_freq.base
#         else:
#             condition = self.freq != other_freq

#         if condition:
#             msg = DIFFERENT_FREQ.format(
#                 cls=type(self).__name__,
#                 own_freq=self.freqstr,
#                 other_freq=other_freq.freqstr,
#             )
#             raise IncompatibleFrequency(msg)


# class _Period(PeriodMixin):
#     # higher than np.ndarray, np.matrix, np.timedelta64
#     __array_priority__ = 100

#     dayofweek = _Period.day_of_week
#     dayofyear = _Period.day_of_year

#     def __init__(self, int64_t ordinal, BaseOffset freq):
#         self.ordinal = ordinal
#         self.freq = freq
#         # Note: this is more performant than PeriodDtype.from_date_offset(freq)
#         #  because from_date_offset cannot be made a cdef method (until cython
#         #  supported cdef classmethods)
#         self._dtype = PeriodDtypeBase(freq._period_dtype_code)

#     @classmethod
#     def _maybe_convert_freq(cls, object freq) -> BaseOffset:
#         """
#         Internally we allow integer and tuple representations (for now) that
#         are not recognized by to_offset, so we convert them here.  Also, a
#         Period's freq attribute must have `freq.n > 0`, which we check for here.

#         Returns
#         -------
#         DateOffset
#         """
#         if isinstance(freq, int):
#             # We already have a dtype code
#             dtype = PeriodDtypeBase(freq)
#             freq = dtype._freqstr

#         freq = to_offset(freq)

#         if freq.n <= 0:
#             raise ValueError("Frequency must be positive, because it "
#                              f"represents span: {freq.freqstr}")

#         return freq

#     @classmethod
#     def _from_ordinal(cls, ordinal: int64_t, freq) -> "Period":
#         """
#         Fast creation from an ordinal and freq that are already validated!
#         """
#         if ordinal == NPY_NAT:
#             return NaT
#         else:
#             freq = cls._maybe_convert_freq(freq)
#             self = _Period.__new__(cls, ordinal, freq)
#             return self

#     def __richcmp__(self, other, op):
#         if is_period_object(other):
#             if other.freq != self.freq:
#                 if op == Py_EQ:
#                     return False
#                 elif op == Py_NE:
#                     return True
#                 self._require_matching_freq(other)
#             return PyObject_RichCompareBool(self.ordinal, other.ordinal, op)
#         elif other is NaT:
#             return op == Py_NE
#         elif util.is_array(other):
#             # GH#44285
#             if cnp.PyArray_IsZeroDim(other):
#                 return PyObject_RichCompare(self, other.item(), op)
#             else:
#                 # in particular ndarray[object]; see test_pi_cmp_period
#                 return np.array([PyObject_RichCompare(self, x, op) for x in other])
#         return NotImplemented

#     def __hash__(self):
#         return hash((self.ordinal, self.freqstr))

#     def _add_timedeltalike_scalar(self, other) -> "Period":
#         cdef:
#             int64_t inc

#         if not is_tick_object(self.freq):
#             raise IncompatibleFrequency("Input cannot be converted to "
#                                         f"Period(freq={self.freqstr})")

#         if util.is_timedelta64_object(other) and get_timedelta64_value(other) == NPY_NAT:
#             # i.e. np.timedelta64("nat")
#             return NaT

#         try:
#             inc = delta_to_nanoseconds(other, reso=self.freq._reso, round_ok=False)
#         except ValueError as err:
#             raise IncompatibleFrequency("Input cannot be converted to "
#                                         f"Period(freq={self.freqstr})") from err
#         # TODO: overflow-check here
#         ordinal = self.ordinal + inc
#         return Period(ordinal=ordinal, freq=self.freq)

#     def _add_offset(self, other) -> "Period":
#         # Non-Tick DateOffset other
#         cdef:
#             int64_t ordinal

#         self._require_matching_freq(other, base=True)

#         ordinal = self.ordinal + other.n
#         return Period(ordinal=ordinal, freq=self.freq)

#     def __add__(self, other):
#         if not is_period_object(self):
#             # cython semantics; this is analogous to a call to __radd__
#             # TODO(cython3): remove this
#             if self is NaT:
#                 return NaT
#             return other.__add__(self)

#         if is_any_td_scalar(other):
#             return self._add_timedeltalike_scalar(other)
#         elif is_offset_object(other):
#             return self._add_offset(other)
#         elif other is NaT:
#             return NaT
#         elif util.is_integer_object(other):
#             ordinal = self.ordinal + other * self.freq.n
#             return Period(ordinal=ordinal, freq=self.freq)

#         elif is_period_object(other):
#             # can't add datetime-like
#             # GH#17983; can't just return NotImplemented bc we get a RecursionError
#             #  when called via np.add.reduce see TestNumpyReductions.test_add
#             #  in npdev build
#             sname = type(self).__name__
#             oname = type(other).__name__
#             raise TypeError(f"unsupported operand type(s) for +: '{sname}' "
#                             f"and '{oname}'")

#         return NotImplemented

#     def __radd__(self, other):
#         return self.__add__(other)

#     def __sub__(self, other):
#         if not is_period_object(self):
#             # cython semantics; this is like a call to __rsub__
#             # TODO(cython3): remove this
#             if self is NaT:
#                 return NaT
#             return NotImplemented

#         elif (
#             is_any_td_scalar(other)
#             or is_offset_object(other)
#             or util.is_integer_object(other)
#         ):
#             return self + (-other)
#         elif is_period_object(other):
#             self._require_matching_freq(other)
#             # GH 23915 - mul by base freq since __add__ is agnostic of n
#             return (self.ordinal - other.ordinal) * self.freq.base
#         elif other is NaT:
#             return NaT

#         return NotImplemented

#     def __rsub__(self, other):
#         if other is NaT:
#             return NaT
#         return NotImplemented

#     def asfreq(self, freq, how='E') -> "Period":
#         """
#         Convert Period to desired frequency, at the start or end of the interval.

#         Parameters
#         ----------
#         freq : str, BaseOffset
#             The desired frequency.
#         how : {'E', 'S', 'end', 'start'}, default 'end'
#             Start or end of the timespan.

#         Returns
#         -------
#         resampled : Period
#         """
#         freq = self._maybe_convert_freq(freq)
#         how = validate_end_alias(how)
#         base1 = self._dtype._dtype_code
#         base2 = freq_to_dtype_code(freq)

#         # self.n can't be negative or 0
#         end = how == 'E'
#         if end:
#             ordinal = self.ordinal + self.freq.n - 1
#         else:
#             ordinal = self.ordinal
#         ordinal = period_asfreq(ordinal, base1, base2, end)

#         return Period(ordinal=ordinal, freq=freq)

#     def to_timestamp(self, freq=None, how='start', tz=None) -> Timestamp:
#         """
#         Return the Timestamp representation of the Period.

#         Uses the target frequency specified at the part of the period specified
#         by `how`, which is either `Start` or `Finish`.

#         Parameters
#         ----------
#         freq : str or DateOffset
#             Target frequency. Default is 'D' if self.freq is week or
#             longer and 'S' otherwise.
#         how : str, default 'S' (start)
#             One of 'S', 'E'. Can be aliased as case insensitive
#             'Start', 'Finish', 'Begin', 'End'.

#         Returns
#         -------
#         Timestamp
#         """
#         if tz is not None:
#             # GH#34522
#             warnings.warn(
#                 "Period.to_timestamp `tz` argument is deprecated and will "
#                 "be removed in a future version.  Use "
#                 "`per.to_timestamp(...).tz_localize(tz)` instead.",
#                 FutureWarning,
#                 stacklevel=find_stack_level(inspect.currentframe()),
#             )

#         how = validate_end_alias(how)

#         end = how == 'E'
#         if end:
#             if freq == "B" or self.freq == "B":
#                 # roll forward to ensure we land on B date
#                 adjust = np.timedelta64(1, "D") - np.timedelta64(1, "ns")
#                 return self.to_timestamp(how="start") + adjust
#             endpoint = (self + self.freq).to_timestamp(how='start')
#             return endpoint - np.timedelta64(1, "ns")

#         if freq is None:
#             freq = self._dtype._get_to_timestamp_base()
#             base = freq
#         else:
#             freq = self._maybe_convert_freq(freq)
#             base = freq._period_dtype_code

#         val = self.asfreq(freq, how)

#         dt64 = period_ordinal_to_dt64(val.ordinal, base)
#         return Timestamp(dt64, tz=tz)

#     @property
#     def year(self) -> int:
#         """
#         Return the year this Period falls on.
#         """
#         base = self._dtype._dtype_code
#         return pyear(self.ordinal, base)

#     @property
#     def month(self) -> int:
#         """
#         Return the month this Period falls on.
#         """
#         base = self._dtype._dtype_code
#         return pmonth(self.ordinal, base)

#     @property
#     def day(self) -> int:
#         """
#         Get day of the month that a Period falls on.

#         Returns
#         -------
#         int

#         See Also
#         --------
#         Period.dayofweek : Get the day of the week.
#         Period.dayofyear : Get the day of the year.

#         Examples
#         --------
#         >>> p = pd.Period("2018-03-11", freq='H')
#         >>> p.day
#         11
#         """
#         base = self._dtype._dtype_code
#         return pday(self.ordinal, base)

#     @property
#     def hour(self) -> int:
#         """
#         Get the hour of the day component of the Period.

#         Returns
#         -------
#         int
#             The hour as an integer, between 0 and 23.

#         See Also
#         --------
#         Period.second : Get the second component of the Period.
#         Period.minute : Get the minute component of the Period.

#         Examples
#         --------
#         >>> p = pd.Period("2018-03-11 13:03:12.050000")
#         >>> p.hour
#         13

#         Period longer than a day

#         >>> p = pd.Period("2018-03-11", freq="M")
#         >>> p.hour
#         0
#         """
#         base = self._dtype._dtype_code
#         return phour(self.ordinal, base)

#     @property
#     def minute(self) -> int:
#         """
#         Get minute of the hour component of the Period.

#         Returns
#         -------
#         int
#             The minute as an integer, between 0 and 59.

#         See Also
#         --------
#         Period.hour : Get the hour component of the Period.
#         Period.second : Get the second component of the Period.

#         Examples
#         --------
#         >>> p = pd.Period("2018-03-11 13:03:12.050000")
#         >>> p.minute
#         3
#         """
#         base = self._dtype._dtype_code
#         return pminute(self.ordinal, base)

#     @property
#     def second(self) -> int:
#         """
#         Get the second component of the Period.

#         Returns
#         -------
#         int
#             The second of the Period (ranges from 0 to 59).

#         See Also
#         --------
#         Period.hour : Get the hour component of the Period.
#         Period.minute : Get the minute component of the Period.

#         Examples
#         --------
#         >>> p = pd.Period("2018-03-11 13:03:12.050000")
#         >>> p.second
#         12
#         """
#         base = self._dtype._dtype_code
#         return psecond(self.ordinal, base)

#     @property
#     def weekofyear(self) -> int:
#         """
#         Get the week of the year on the given Period.

#         Returns
#         -------
#         int

#         See Also
#         --------
#         Period.dayofweek : Get the day component of the Period.
#         Period.weekday : Get the day component of the Period.

#         Examples
#         --------
#         >>> p = pd.Period("2018-03-11", "H")
#         >>> p.weekofyear
#         10

#         >>> p = pd.Period("2018-02-01", "D")
#         >>> p.weekofyear
#         5

#         >>> p = pd.Period("2018-01-06", "D")
#         >>> p.weekofyear
#         1
#         """
#         base = self._dtype._dtype_code
#         return pweek(self.ordinal, base)

#     @property
#     def week(self) -> int:
#         """
#         Get the week of the year on the given Period.

#         Returns
#         -------
#         int

#         See Also
#         --------
#         Period.dayofweek : Get the day component of the Period.
#         Period.weekday : Get the day component of the Period.

#         Examples
#         --------
#         >>> p = pd.Period("2018-03-11", "H")
#         >>> p.week
#         10

#         >>> p = pd.Period("2018-02-01", "D")
#         >>> p.week
#         5

#         >>> p = pd.Period("2018-01-06", "D")
#         >>> p.week
#         1
#         """
#         return self.weekofyear

#     @property
#     def day_of_week(self) -> int:
#         """
#         Day of the week the period lies in, with Monday=0 and Sunday=6.

#         If the period frequency is lower than daily (e.g. hourly), and the
#         period spans over multiple days, the day at the start of the period is
#         used.

#         If the frequency is higher than daily (e.g. monthly), the last day
#         of the period is used.

#         Returns
#         -------
#         int
#             Day of the week.

#         See Also
#         --------
#         Period.day_of_week : Day of the week the period lies in.
#         Period.weekday : Alias of Period.day_of_week.
#         Period.day : Day of the month.
#         Period.dayofyear : Day of the year.

#         Examples
#         --------
#         >>> per = pd.Period('2017-12-31 22:00', 'H')
#         >>> per.day_of_week
#         6

#         For periods that span over multiple days, the day at the beginning of
#         the period is returned.

#         >>> per = pd.Period('2017-12-31 22:00', '4H')
#         >>> per.day_of_week
#         6
#         >>> per.start_time.day_of_week
#         6

#         For periods with a frequency higher than days, the last day of the
#         period is returned.

#         >>> per = pd.Period('2018-01', 'M')
#         >>> per.day_of_week
#         2
#         >>> per.end_time.day_of_week
#         2
#         """
#         base = self._dtype._dtype_code
#         return pweekday(self.ordinal, base)

#     @property
#     def weekday(self) -> int:
#         """
#         Day of the week the period lies in, with Monday=0 and Sunday=6.

#         If the period frequency is lower than daily (e.g. hourly), and the
#         period spans over multiple days, the day at the start of the period is
#         used.

#         If the frequency is higher than daily (e.g. monthly), the last day
#         of the period is used.

#         Returns
#         -------
#         int
#             Day of the week.

#         See Also
#         --------
#         Period.dayofweek : Day of the week the period lies in.
#         Period.weekday : Alias of Period.dayofweek.
#         Period.day : Day of the month.
#         Period.dayofyear : Day of the year.

#         Examples
#         --------
#         >>> per = pd.Period('2017-12-31 22:00', 'H')
#         >>> per.dayofweek
#         6

#         For periods that span over multiple days, the day at the beginning of
#         the period is returned.

#         >>> per = pd.Period('2017-12-31 22:00', '4H')
#         >>> per.dayofweek
#         6
#         >>> per.start_time.dayofweek
#         6

#         For periods with a frequency higher than days, the last day of the
#         period is returned.

#         >>> per = pd.Period('2018-01', 'M')
#         >>> per.dayofweek
#         2
#         >>> per.end_time.dayofweek
#         2
#         """
#         # Docstring is a duplicate from dayofweek. Reusing docstrings with
#         # Appender doesn't work for properties in Cython files, and setting
#         # the __doc__ attribute is also not possible.
#         return self.dayofweek

#     @property
#     def day_of_year(self) -> int:
#         """
#         Return the day of the year.

#         This attribute returns the day of the year on which the particular
#         date occurs. The return value ranges between 1 to 365 for regular
#         years and 1 to 366 for leap years.

#         Returns
#         -------
#         int
#             The day of year.

#         See Also
#         --------
#         Period.day : Return the day of the month.
#         Period.day_of_week : Return the day of week.
#         PeriodIndex.day_of_year : Return the day of year of all indexes.

#         Examples
#         --------
#         >>> period = pd.Period("2015-10-23", freq='H')
#         >>> period.day_of_year
#         296
#         >>> period = pd.Period("2012-12-31", freq='D')
#         >>> period.day_of_year
#         366
#         >>> period = pd.Period("2013-01-01", freq='D')
#         >>> period.day_of_year
#         1
#         """
#         base = self._dtype._dtype_code
#         return pday_of_year(self.ordinal, base)

#     @property
#     def quarter(self) -> int:
#         """
#         Return the quarter this Period falls on.
#         """
#         base = self._dtype._dtype_code
#         return pquarter(self.ordinal, base)

#     @property
#     def qyear(self) -> int:
#         """
#         Fiscal year the Period lies in according to its starting-quarter.

#         The `year` and the `qyear` of the period will be the same if the fiscal
#         and calendar years are the same. When they are not, the fiscal year
#         can be different from the calendar year of the period.

#         Returns
#         -------
#         int
#             The fiscal year of the period.

#         See Also
#         --------
#         Period.year : Return the calendar year of the period.

#         Examples
#         --------
#         If the natural and fiscal year are the same, `qyear` and `year` will
#         be the same.

#         >>> per = pd.Period('2018Q1', freq='Q')
#         >>> per.qyear
#         2018
#         >>> per.year
#         2018

#         If the fiscal year starts in April (`Q-MAR`), the first quarter of
#         2018 will start in April 2017. `year` will then be 2017, but `qyear`
#         will be the fiscal year, 2018.

#         >>> per = pd.Period('2018Q1', freq='Q-MAR')
#         >>> per.start_time
#         Timestamp('2017-04-01 00:00:00')
#         >>> per.qyear
#         2018
#         >>> per.year
#         2017
#         """
#         base = self._dtype._dtype_code
#         return pqyear(self.ordinal, base)

#     @property
#     def days_in_month(self) -> int:
#         """
#         Get the total number of days in the month that this period falls on.

#         Returns
#         -------
#         int

#         See Also
#         --------
#         Period.daysinmonth : Gets the number of days in the month.
#         DatetimeIndex.daysinmonth : Gets the number of days in the month.
#         calendar.monthrange : Returns a tuple containing weekday
#             (0-6 ~ Mon-Sun) and number of days (28-31).

#         Examples
#         --------
#         >>> p = pd.Period('2018-2-17')
#         >>> p.days_in_month
#         28

#         >>> pd.Period('2018-03-01').days_in_month
#         31

#         Handles the leap year case as well:

#         >>> p = pd.Period('2016-2-17')
#         >>> p.days_in_month
#         29
#         """
#         base = self._dtype._dtype_code
#         return pdays_in_month(self.ordinal, base)

#     @property
#     def daysinmonth(self) -> int:
#         """
#         Get the total number of days of the month that this period falls on.

#         Returns
#         -------
#         int

#         See Also
#         --------
#         Period.days_in_month : Return the days of the month.
#         Period.dayofyear : Return the day of the year.

#         Examples
#         --------
#         >>> p = pd.Period("2018-03-11", freq='H')
#         >>> p.daysinmonth
#         31
#         """
#         return self.days_in_month

#     @property
#     def is_leap_year(self) -> bool:
#         """
#         Return True if the period's year is in a leap year.
#         """
#         return bool(is_leapyear(self.year))

#     @classmethod
#     def now(cls, freq=None):
#         """
#         Return the period of now's date.
#         """
#         return Period(datetime.now(), freq=freq)

#     @property
#     def freqstr(self) -> str:
#         """
#         Return a string representation of the frequency.
#         """
#         return self.freq.freqstr

#     def __repr__(self) -> str:
#         base = self._dtype._dtype_code
#         formatted = period_format(self.ordinal, base)
#         return f"Period('{formatted}', '{self.freqstr}')"

#     def __str__(self) -> str:
#         """
#         Return a string representation for a particular DataFrame
#         """
#         base = self._dtype._dtype_code
#         formatted = period_format(self.ordinal, base)
#         value = str(formatted)
#         return value

#     def __setstate__(self, state):
#         self.freq = state[1]
#         self.ordinal = state[2]

#     def __reduce__(self):
#         object_state = None, self.freq, self.ordinal
#         return (Period, object_state)

#     def strftime(self, fmt: str) -> str:
#         r"""
#         Returns a formatted string representation of the :class:`Period`.

#         ``fmt`` must be a string containing one or several directives.
#         The method recognizes the same directives as the :func:`time.strftime`
#         function of the standard Python distribution, as well as the specific
#         additional directives ``%f``, ``%F``, ``%q``, ``%l``, ``%u``, ``%n``.
#         (formatting & docs originally from scikits.timeries).

#         +-----------+--------------------------------+-------+
#         | Directive | Meaning                        | Notes |
#         +===========+================================+=======+
#         | ``%a``    | Locale's abbreviated weekday   |       |
#         |           | name.                          |       |
#         +-----------+--------------------------------+-------+
#         | ``%A``    | Locale's full weekday name.    |       |
#         +-----------+--------------------------------+-------+
#         | ``%b``    | Locale's abbreviated month     |       |
#         |           | name.                          |       |
#         +-----------+--------------------------------+-------+
#         | ``%B``    | Locale's full month name.      |       |
#         +-----------+--------------------------------+-------+
#         | ``%c``    | Locale's appropriate date and  |       |
#         |           | time representation.           |       |
#         +-----------+--------------------------------+-------+
#         | ``%d``    | Day of the month as a decimal  |       |
#         |           | number [01,31].                |       |
#         +-----------+--------------------------------+-------+
#         | ``%f``    | 'Fiscal' year without a        | \(1)  |
#         |           | century  as a decimal number   |       |
#         |           | [00,99]                        |       |
#         +-----------+--------------------------------+-------+
#         | ``%F``    | 'Fiscal' year with a century   | \(2)  |
#         |           | as a decimal number            |       |
#         +-----------+--------------------------------+-------+
#         | ``%H``    | Hour (24-hour clock) as a      |       |
#         |           | decimal number [00,23].        |       |
#         +-----------+--------------------------------+-------+
#         | ``%I``    | Hour (12-hour clock) as a      |       |
#         |           | decimal number [01,12].        |       |
#         +-----------+--------------------------------+-------+
#         | ``%j``    | Day of the year as a decimal   |       |
#         |           | number [001,366].              |       |
#         +-----------+--------------------------------+-------+
#         | ``%m``    | Month as a decimal number      |       |
#         |           | [01,12].                       |       |
#         +-----------+--------------------------------+-------+
#         | ``%M``    | Minute as a decimal number     |       |
#         |           | [00,59].                       |       |
#         +-----------+--------------------------------+-------+
#         | ``%p``    | Locale's equivalent of either  | \(3)  |
#         |           | AM or PM.                      |       |
#         +-----------+--------------------------------+-------+
#         | ``%q``    | Quarter as a decimal number    |       |
#         |           | [1,4]                          |       |
#         +-----------+--------------------------------+-------+
#         | ``%S``    | Second as a decimal number     | \(4)  |
#         |           | [00,61].                       |       |
#         +-----------+--------------------------------+-------+
#         | ``%l``    | Millisecond as a decimal number|       |
#         |           | [000,999].                     |       |
#         +-----------+--------------------------------+-------+
#         | ``%u``    | Microsecond as a decimal number|       |
#         |           | [000000,999999].               |       |
#         +-----------+--------------------------------+-------+
#         | ``%n``    | Nanosecond as a decimal number |       |
#         |           | [000000000,999999999].         |       |
#         +-----------+--------------------------------+-------+
#         | ``%U``    | Week number of the year        | \(5)  |
#         |           | (Sunday as the first day of    |       |
#         |           | the week) as a decimal number  |       |
#         |           | [00,53].  All days in a new    |       |
#         |           | year preceding the first       |       |
#         |           | Sunday are considered to be in |       |
#         |           | week 0.                        |       |
#         +-----------+--------------------------------+-------+
#         | ``%w``    | Weekday as a decimal number    |       |
#         |           | [0(Sunday),6].                 |       |
#         +-----------+--------------------------------+-------+
#         | ``%W``    | Week number of the year        | \(5)  |
#         |           | (Monday as the first day of    |       |
#         |           | the week) as a decimal number  |       |
#         |           | [00,53].  All days in a new    |       |
#         |           | year preceding the first       |       |
#         |           | Monday are considered to be in |       |
#         |           | week 0.                        |       |
#         +-----------+--------------------------------+-------+
#         | ``%x``    | Locale's appropriate date      |       |
#         |           | representation.                |       |
#         +-----------+--------------------------------+-------+
#         | ``%X``    | Locale's appropriate time      |       |
#         |           | representation.                |       |
#         +-----------+--------------------------------+-------+
#         | ``%y``    | Year without century as a      |       |
#         |           | decimal number [00,99].        |       |
#         +-----------+--------------------------------+-------+
#         | ``%Y``    | Year with century as a decimal |       |
#         |           | number.                        |       |
#         +-----------+--------------------------------+-------+
#         | ``%Z``    | Time zone name (no characters  |       |
#         |           | if no time zone exists).       |       |
#         +-----------+--------------------------------+-------+
#         | ``%%``    | A literal ``'%'`` character.   |       |
#         +-----------+--------------------------------+-------+

#         Notes
#         -----

#         (1)
#             The ``%f`` directive is the same as ``%y`` if the frequency is
#             not quarterly.
#             Otherwise, it corresponds to the 'fiscal' year, as defined by
#             the :attr:`qyear` attribute.

#         (2)
#             The ``%F`` directive is the same as ``%Y`` if the frequency is
#             not quarterly.
#             Otherwise, it corresponds to the 'fiscal' year, as defined by
#             the :attr:`qyear` attribute.

#         (3)
#             The ``%p`` directive only affects the output hour field
#             if the ``%I`` directive is used to parse the hour.

#         (4)
#             The range really is ``0`` to ``61``; this accounts for leap
#             seconds and the (very rare) double leap seconds.

#         (5)
#             The ``%U`` and ``%W`` directives are only used in calculations
#             when the day of the week and the year are specified.

#         Examples
#         --------

#         >>> a = Period(freq='Q-JUL', year=2006, quarter=1)
#         >>> a.strftime('%F-Q%q')
#         '2006-Q1'
#         >>> # Output the last month in the quarter of this date
#         >>> a.strftime('%b-%Y')
#         'Oct-2005'
#         >>>
#         >>> a = Period(freq='D', year=2001, month=1, day=1)
#         >>> a.strftime('%d-%b-%Y')
#         '01-Jan-2001'
#         >>> a.strftime('%b. %d, %Y was a %A')
#         'Jan. 01, 2001 was a Monday'
#         """
#         base = self._dtype._dtype_code
#         return period_format(self.ordinal, base, fmt)

# def is_period_object(obj):
#     return isinstance(obj, _Period)
