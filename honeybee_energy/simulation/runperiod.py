# coding=utf-8
"""EnergyPlus Simulation Run Period."""
from __future__ import division

from .daylightsaving import DaylightSavingTime
from ..reader import parse_idf_string
from ..writer import generate_idf_string

from honeybee.typing import valid_string

from ladybug.analysisperiod import AnalysisPeriod
from ladybug.dt import Date


class RunPeriod(object):
    """EnergyPlus Simulation Run Period.

    Properties:
        * start_date
        * end_date
        * start_day_of_week
        * holidays
        * daylight_saving_time
        * is_leap_year
    """
    __slots__ = ('_start_date', '_end_date', '_start_day_of_week', '_holidays',
                 '_daylight_saving_time')
    DAYS_OF_THE_WEEK = (
        'Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday')

    def __init__(self, start_date=Date(1, 1), end_date=Date(12, 31),
                 start_day_of_week='Sunday', holidays=None, daylight_saving_time=None):
        """Initialize RunPeriod.

        Args:
            start_date: A ladybug Date object for the start of the run period.
                Must be before the end date and have a leap_year property matching the
                end_date. Default: 1 Jan
            end_date: A ladybug Date object for the end of the run period.
                Must be after the start date and have a leap_year property matching the
                start_date. Default: 31 Dec
            start_day_of_week: Text for the day of the week on which the simulation
                starts. Default: 'Sunday'. Choose from the following:
                    * Sunday
                    * Monday
                    * Tuesday
                    * Wednesday
                    * Thursday
                    * Friday
                    * Saturday
            holidays: A list of Ladybug Date objects for the holidays within the
                simulation. If None, no folidays are applied. Default: None.
            daylight_saving_time: A DaylightSavingTime object to dictate the start and
                end dates of daylight saving time. If None, no daylight saving time is
                applied to the simulation. Default: None.
        """
        # process the dates
        if start_date is not None:
            self._check_date(start_date, 'start_date')
            self._start_date = start_date
        else:
            self._start_date = Date(1, 1)
        self.end_date = end_date

        self.start_day_of_week = start_day_of_week
        self.holidays = holidays
        self.daylight_saving_time = daylight_saving_time

    @property
    def start_date(self):
        """Get or set a ladybug Date object for the start of the run period."""
        return self._start_date

    @start_date.setter
    def start_date(self, value):
        if value is not None:
            self._check_date(value, 'start_date')
            self._start_date = value
        else:
            self._start_date = Date(1, 1)
        self._check_start_before_end()

    @property
    def end_date(self):
        """Get or set a ladybug Date object for the end of the run period."""
        return self._end_date

    @end_date.setter
    def end_date(self, value):
        if value is not None:
            self._check_date(value, 'start_date')
            self._end_date = value
        else:
            self._end_date = Date(12, 31)
        self._check_start_before_end()

    @property
    def start_day_of_week(self):
        """Get or set text for the day of the week on which the simulation starts.

        Choose from the following:
            * Sunday
            * Monday
            * Tuesday
            * Wednesday
            * Thursday
            * Friday
            * Saturday
        """
        return self._start_day_of_week

    @start_day_of_week.setter
    def start_day_of_week(self, value):
        clean_input = valid_string(value).lower()
        for key in self.DAYS_OF_THE_WEEK:
            if key.lower() == clean_input:
                value = key
                break
        else:
            raise ValueError(
                'start_day_of_week {} is not recognized.\nChoose from the '
                'following:\n{}'.format(value, self.DAYS_OF_THE_WEEK))
        self._start_day_of_week = value

    @property
    def holidays(self):
        """Get or set a list of ladybug Date objects for holidays."""
        return self._holidays

    @holidays.setter
    def holidays(self, value):
        if value is not None:
            if not isinstance(value, tuple):
                value = tuple(value)
            for date in value:
                assert isinstance(date, Date), 'Expected ladybug Date for ' \
                    'RunPeriod holiday. Got {}.'.format(type(date))
        self._holidays = value

    @property
    def daylight_saving_time(self):
        """Get or set a DaylightSavingTime object for start and end of daylight savings.
        """
        return self._daylight_saving_time

    @daylight_saving_time.setter
    def daylight_saving_time(self, value):
        if value is not None:
            assert isinstance(value, DaylightSavingTime), 'Expected DaylightSavingTime' \
                ' for RunPeriod run_period. Got {}.'.format(type(value))
            if value.start_date.leap_year is not self.start_date.leap_year:
                leap = self.start_date.leap_year
                value._start_date = Date(value._start_date.month,
                                         value._start_date.day, leap)
                value._end_date = Date(value._end_date.month,
                                       value._end_date.day, leap)
        self._daylight_saving_time = value

    @property
    def is_leap_year(self):
        """Get or set a boolean noting whether the RunPeriod is for a leap year simulation.
        """
        return self.start_date.leap_year

    @is_leap_year.setter
    def is_leap_year(self, value):
        value = bool(value)
        self._start_date = Date(self._start_date.month, self._start_date.day, value)
        self._end_date = Date(self._end_date.month, self._end_date.day, value)
        if self._daylight_saving_time is not None:
            st_dt = self._daylight_saving_time._start_date
            ed_dt = self._daylight_saving_time._end_date
            self._daylight_saving_time._start_date = Date(st_dt.month, st_dt.day, value)
            self._daylight_saving_time._end_date = Date(ed_dt.month, ed_dt.day, value)

    @classmethod
    def from_analysis_period(cls, analysis_period=None, start_day_of_week='Sunday',
                             holidays=None, daylight_saving_time=None):
        """Initialize a RunPeriod object from a ladybug AnalysisPeriod.

        Note that the st_hour and end_hour properties of the AnalysisPeriod are
        completely ignored when using this classmethod since EnergyPlus cannot start
        or end a simulation at an interval less than a day.

        Args:
            analysis_period: A ladybug AnalysisPeriod object that has the start
                and end dates for the simulation. Default: an AnalysisPeriod for the
                whole year.
            start_day_of_week: Text for the day of the week on which the simulation
                starts. Default: 'Sunday'. Choose from the following:
                    * Sunday
                    * Monday
                    * Tuesday
                    * Wednesday
                    * Thursday
                    * Friday
                    * Saturday
            holidays: A list of Ladybug Date objects for the holidays within the
                simulation. If None, no folidays are applied. Default: None.
            daylight_saving_time: A DaylightSavingTime object to dictate the start and
                end dates of daylight saving time. If None, no daylight saving time is
                applied to the simulation. Default: None.
        """
        assert isinstance(analysis_period, AnalysisPeriod), 'Expected AnalysisPeriod ' \
            'for RunPeriod.from_analysis_period. Got {}.'.format(type(analysis_period))
        st_date = Date(analysis_period.st_month, analysis_period.st_date,
                       analysis_period.is_leap_year)
        end_date = Date(analysis_period.end_month, analysis_period.end_date,
                        analysis_period.is_leap_year)
        return cls(st_date, end_date, start_day_of_week, holidays, daylight_saving_time)

    @classmethod
    def from_idf(cls, idf_string, holiday_strings=None, daylight_saving_string=None):
        """Create a RunPeriod object from an EnergyPlus IDF text string.

        Args:
            idf_string: A text string fully describing an EnergyPlus RunPeriod
                definition.
            holiday_strings: A list of IDF RunPeriodControl:SpecialDays strings
                that represent the holidays applied to the simulation.
            daylight_saving_string: An IDF RunPeriodControl:DaylightSavingTime string
                that notes the start and ends dates of Daylight Savings time.
        """
        # check the inputs
        ep_strs = parse_idf_string(idf_string, 'RunPeriod,')

        # extract the required properties
        start_year = int(ep_strs[3]) if ep_strs[3] != '' else 2017
        leap_year = True if start_year % 4 == 0 else False
        start_date = Date(int(ep_strs[1]), int(ep_strs[2]), leap_year)
        end_date = Date(int(ep_strs[4]), int(ep_strs[5]), leap_year)

        # extract the optional properties
        start_day_of_week = 'Sunday'
        try:
            start_day_of_week = ep_strs[7] if ep_strs[7] != '' else 'Sunday'
        except IndexError:
            pass  # shorter RunPeriod definition
        holidays = None
        if holiday_strings is not None:
            holidays = []
            for hol_str in holiday_strings:
                ep_hol_str = parse_idf_string(hol_str, 'RunPeriodControl:SpecialDays,')
                hol_vals = ep_hol_str[1].split('/')
                holidays.append(Date(int(hol_vals[0]), int(hol_vals[1]), leap_year))
        daylight_saving = DaylightSavingTime.from_idf(daylight_saving_string) if \
            daylight_saving_string is not None else None

        return cls(start_date, end_date, start_day_of_week, holidays, daylight_saving)

    @classmethod
    def from_dict(cls, data):
        """Create a RunPeriod object from a dictionary.

        Args:
            data: A RunPeriod dictionary in following the format below.

        .. code-block:: python

            {
            "type": "RunPeriod",
            "start_date": {month: 1, day: 1},
            "end_date": {month: 12, day: 31},
            "start_day_of_week": 'Monday',
            "holidays": [{month: 1, day: 1}, {month: 7, day: 4}],
            "daylight_saving_time": {} // DaylightSavingTime dictionary representation
            }
        """
        assert data['type'] == 'RunPeriod', \
            'Expected RunPeriod dictionary. Got {}.'.format(data['type'])
        start_date = Date.from_dict(data['start_date']) if \
            'start_date' in data else Date(1, 1)
        end_date = Date.from_dict(data['end_date']) if \
            'end_date' in data else Date(12, 31)
        start_day_of_week = data['start_day_of_week'] if \
            'start_day_of_week' in data else 'Sunday'
        holidays = None
        if 'holidays' in data and data['holidays'] is not None:
            holidays = tuple(Date.from_dict(hol) for hol in data['holidays'])
        daylight_saving = None
        if 'daylight_saving_time' in data and data['daylight_saving_time'] is not None:
            daylight_saving = DaylightSavingTime.from_dict(data['daylight_saving_time'])
        return cls(start_date, end_date, start_day_of_week, holidays, daylight_saving)

    def to_idf(self):
        """Get an EnergyPlus string representation of the RunPeriod.

        Returns:
            run_period: An IDF string representation of the RunPeriod object.
            holidays: A list of IDF RunPeriodControl:SpecialDays strings that represent
                the holidays applied to the simulation. Will be None if no holidays
                are applied to this RunPeriod.
            daylight_saving_time: An IDF RunPeriodControl:DaylightSavingTime string
                that notes the start and ends dates of Daylight Savings time. Will be
                None if no daylight_saving_time is applied to this RunPeriod.
        """
        year = 2016 if self.is_leap_year else 2017
        values = ('CustomRunPeriod', self.start_date.month, self.start_date.day, year,
                  self.end_date.month, self.end_date.day, year,
                  self.start_day_of_week, 'Yes', 'Yes')
        comments = ('name', 'start month', 'start day', 'start year',
                    'end month', 'end day', 'end year', 'start day of week',
                    'use weather file holidays', 'use weather file daylight savings')
        run_period = generate_idf_string('RunPeriod', values, comments)

        holidays = [self._holiday_to_idf(hol, i) for i, hol in
                    enumerate(self.holidays)] if self.holidays is not None else None

        daylight_saving_time = self.daylight_saving_time.to_idf() if \
            self.daylight_saving_time is not None else None

        return run_period, holidays, daylight_saving_time

    def to_dict(self):
        """RunPeriod dictionary representation."""
        base = {
            'type': 'RunPeriod',
            'start_date': self.start_date.to_dict(),
            'end_date': self.end_date.to_dict(),
            'start_day_of_week': self.start_day_of_week
        }
        if self.holidays is not None:
            base['holidays'] = [hol.to_dict() for hol in self.holidays]
        if self.daylight_saving_time is not None:
            base['daylight_saving_time'] = self.daylight_saving_time.to_dict()
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def _check_start_before_end(self):
        """Check that the start_date is before the end_date."""
        assert self.start_date.leap_year is self.end_date.leap_year, \
            'RunPeriod start_date.leap_year must match the end_date.leap_year'
        assert self._start_date < self._end_date, 'RunPeriod start_date must come ' \
            'before end_date. {} comes after {}.'.format(self.start_date, self.end_date)

    @staticmethod
    def _check_date(date, date_name='date'):
        assert isinstance(date, Date), 'Expected ladybug Date for ' \
            'RunPeriod {}. Got {}.'.format(date_name, type(date))

    @staticmethod
    def _holiday_to_idf(date, count):
        """Convert a ladybug Date object to an IDF holiday string."""
        values = ('Holiday_{}'.format(count), '{}/{}'.format(date.month, date.day))
        comments = ('name', 'date')
        return generate_idf_string('RunPeriodControl:SpecialDays', values, comments)

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __copy__(self):
        dst = self.daylight_saving_time.duplicate() if self.daylight_saving_time \
            is not None else None
        return RunPeriod(self.start_date, self.end_date, self.start_day_of_week,
                         self.holidays, dst)

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        hol_tup = tuple(hash(hol) for hol in self.holidays) if \
            self.holidays is not None else (None,)
        return (hash(self.start_date), hash(self.end_date), self.start_day_of_week,
                hash(self.daylight_saving_time)) + hol_tup

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, RunPeriod) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return self.to_idf()[0]
