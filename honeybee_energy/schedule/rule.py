# coding=utf-8
"""Object storing rules for how a given ScheduleDay gets applied over a year."""
from __future__ import division

from .day import ScheduleDay
from ..reader import parse_idf_string

from honeybee._lockable import lockable

from ladybug.dt import Date


@lockable
class ScheduleRule(object):
    """Schedule rule including a DaySchedule and when it should be applied.

    Note that a ScheduleRule cannot be assigned to Rooms, Shades, etc.  The
    ScheduleRule must be added to a ScheduleRuleset and then the ScheduleRuleset
    can be applied to such objects.

    Properties:
        schedule_day
        apply_sunday
        apply_monday
        apply_tuesday
        apply_wednesday
        apply_thursday
        apply_friday
        apply_saturday
        apply_holiday
        start_date
        end_date
        apply_weekday
        apply_weekend
        apply_all
        days_applied
        week_apply_tuple
    """
    __slots__ = ('_schedule_day', '_apply_sunday', '_apply_monday', '_apply_tuesday',
                 '_apply_wednesday', '_apply_thursday', '_apply_friday',
                 '_apply_saturday', '_apply_holiday', '_start_date', '_end_date',
                 '_start_doy', '_end_doy', '_locked')

    _year_start = Date(1, 1)
    _year_end = Date(12, 31)

    def __init__(self, schedule_day, apply_sunday=False, apply_monday=False,
                 apply_tuesday=False, apply_wednesday=False, apply_thursday=False,
                 apply_friday=False, apply_saturday=False, apply_holiday=False,
                 start_date=None, end_date=None):
        """Initialize Schedule Rule.

        Args:
            schedule_day: A ScheduleDay object associated with this rule.
            apply_sunday: Boolean noting whether to apply schedule_day on Sundays.
            apply_monday: Boolean noting whether to apply schedule_day on Mondays.
            apply_tuesday: Boolean noting whether to apply schedule_day on Tuesdays.
            apply_wednesday: Boolean noting whether to apply schedule_day on Wednesdays.
            apply_thursday: Boolean noting whether to apply schedule_day on Thursdays.
            apply_friday: Boolean noting whether to apply schedule_day on Fridays.
            apply_saturday: Boolean noting whether to apply schedule_day on Saturdays.
            apply_holiday: Boolean noting whether to apply schedule_day on Holidays.
            start_date: A ladybug Date object for the start of the period over which
                the schedule_day will be applied. If None, Jan 1 will be used.
            end_date: A ladybug Date object for the end of the period over which
                the schedule_day will be applied. If None, Dec 31 will be used.
        """
        self._locked = False  # unlocked by default
        self.schedule_day = schedule_day
        self.apply_sunday = apply_sunday
        self.apply_monday = apply_monday
        self.apply_tuesday = apply_tuesday
        self.apply_wednesday = apply_wednesday
        self.apply_thursday = apply_thursday
        self.apply_friday = apply_friday
        self.apply_saturday = apply_saturday
        self.apply_holiday = apply_holiday

        # process the start date and end date
        if start_date is not None:
            self._check_date(start_date, 'start_date')
            self._start_date = start_date
        else:
            self._start_date = self._year_start
        self._start_doy = self._doy_non_leap_year(self._start_date)
        self.end_date = end_date

    @property
    def schedule_day(self):
        """Get or set the ScheduleDay object associated with this rule.."""
        return self._schedule_day

    @schedule_day.setter
    def schedule_day(self, value):
        assert isinstance(value, ScheduleDay), \
            'Expected ScheduleDay for ScheduleRule. Got {}.'.format(type(value))
        self._schedule_day = value

    @property
    def apply_sunday(self):
        """Get or set a boolean noting whether to apply schedule_day on Sundays."""
        return self._apply_sunday

    @apply_sunday.setter
    def apply_sunday(self, value):
        self._apply_sunday = bool(value)

    @property
    def apply_monday(self):
        """Get or set a boolean noting whether to apply schedule_day on Mondays."""
        return self._apply_monday

    @apply_monday.setter
    def apply_monday(self, value):
        self._apply_monday = bool(value)

    @property
    def apply_tuesday(self):
        """Get or set a boolean noting whether to apply schedule_day on Tuesdays."""
        return self._apply_tuesday

    @apply_tuesday.setter
    def apply_tuesday(self, value):
        self._apply_tuesday = bool(value)

    @property
    def apply_wednesday(self):
        """Get or set a boolean noting whether to apply schedule_day on Wednesdays."""
        return self._apply_wednesday

    @apply_wednesday.setter
    def apply_wednesday(self, value):
        self._apply_wednesday = bool(value)

    @property
    def apply_thursday(self):
        """Get or set a boolean noting whether to apply schedule_day on Thursdays."""
        return self._apply_thursday

    @apply_thursday.setter
    def apply_thursday(self, value):
        self._apply_thursday = bool(value)

    @property
    def apply_friday(self):
        """Get or set a boolean noting whether to apply schedule_day on Fridays."""
        return self._apply_friday

    @apply_friday.setter
    def apply_friday(self, value):
        self._apply_friday = bool(value)

    @property
    def apply_saturday(self):
        """Get or set a boolean noting whether to apply schedule_day on Saturdays."""
        return self._apply_saturday

    @apply_saturday.setter
    def apply_saturday(self, value):
        self._apply_saturday = bool(value)

    @property
    def apply_holiday(self):
        """Get or set a boolean noting whether to apply schedule_day on Holidays."""
        return self._apply_holiday

    @apply_holiday.setter
    def apply_holiday(self, value):
        self._apply_holiday = bool(value)

    @property
    def apply_weekday(self):
        """Get or set a boolean noting whether to apply schedule_day on week days."""
        return self._apply_monday and self._apply_tuesday and self._apply_wednesday and \
            self._apply_thursday and self._apply_friday

    @apply_weekday.setter
    def apply_weekday(self, value):
        self._apply_monday = self._apply_tuesday = self._apply_wednesday = \
            self._apply_thursday = self._apply_friday = bool(value)

    @property
    def apply_weekend(self):
        """Get or set a boolean noting whether to apply schedule_day on weekends."""
        return self._apply_sunday and self._apply_saturday

    @apply_weekend.setter
    def apply_weekend(self, value):
        self._apply_sunday = self._apply_saturday = bool(value)

    @property
    def apply_all(self):
        """Get or set a boolean noting whether to apply schedule_day on all days."""
        return self._apply_sunday and self._apply_monday and self._apply_tuesday and \
            self._apply_wednesday and self._apply_thursday and self._apply_friday and \
            self._apply_saturday and self._apply_holiday

    @apply_all.setter
    def apply_all(self, value):
        self._apply_sunday = self._apply_monday = self._apply_tuesday = \
            self._apply_wednesday = self._apply_thursday = self._apply_friday = \
            self._apply_saturday = self._apply_holiday = bool(value)

    @property
    def start_date(self):
        """Get or set a ladybug Date object for the start of the period."""
        return self._start_date

    @start_date.setter
    def start_date(self, value):
        if value is not None:
            self._check_date(value, 'start_date')
            self._start_date = value
        else:
            self._start_date = self._year_start
        self._check_start_before_end()
        self._start_doy = self._doy_non_leap_year(self._start_date)

    @property
    def end_date(self):
        """Get or set a ladybug Date object for the end of the period."""
        return self._end_date

    @end_date.setter
    def end_date(self, value):
        if value is not None:
            self._check_date(value, 'end_date')
            self._end_date = value
        else:
            self._end_date = self._year_end
        self._check_start_before_end()
        self._end_doy = self._doy_non_leap_year(self._end_date)

    @property
    def days_applied(self):
        """Get a list of text values for the days applied."""
        day_names = ('sunday', 'monday', 'tuesday', 'wednesday', 'thursday',
                     'friday', 'saturday')
        days = [name for name, apply in zip(day_names, self.week_apply_tuple) if apply]
        if self.apply_holiday:
            days.append('holiday')
        return days

    @property
    def week_apply_tuple(self):
        """Get a tuple of 7 booleans for each of the days of the week."""
        return (self._apply_sunday, self._apply_monday, self._apply_tuesday,
                self._apply_wednesday, self._apply_thursday, self._apply_friday,
                self._apply_saturday)

    def apply_day_by_name(self, day_name):
        """Set the rule to apply to the day of the week (or holidays) by its name.

        Args:
            day_name: A text string for the day on which this rule should be applied.
                The following options are acceptable:
                'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
                'saturday', 'holiday', 'weekday', 'weekend', 'all'
        """
        day_name = day_name.lower()
        if day_name == 'sunday':
            self.apply_sunday = True
        elif day_name == 'monday':
            self.apply_monday = True
        elif day_name == 'tuesday':
            self.apply_tuesday = True
        elif day_name == 'wednesday':
            self.apply_wednesday = True
        elif day_name == 'thursday':
            self.apply_thursday = True
        elif day_name == 'friday':
            self.apply_friday = True
        elif day_name == 'saturday':
            self.apply_saturday = True
        elif day_name == 'holiday':
            self.apply_holiday = True
        elif day_name == 'weekday':
            self.apply_weekday = True
        elif day_name == 'weekend':
            self.apply_weekend = True
        elif day_name == 'all':
            self.apply_all = True
        else:
            raise ValueError('ScheduleRule input "{}" is not an acceptable '
                             'day name.'.format(day_name))

    def apply_day_by_dow(self, dow):
        """Set the rule to apply to the day of the week (or holidays) by its dow integer.

        Args:
            week_day_index: An integer from 1-8 for the day of the week (or the
                holiday). Values correspond to the following:
                    1 - Sunday
                    2 - Monday
                    3 - Tuesday
                    4 - Wednesday
                    5 - Thursday
                    6 - Friday
                    7 - Saturday
                    8 - Holiday
        """
        if dow == 1:
            self.apply_sunday = True
        elif dow == 2:
            self.apply_monday = True
        elif dow == 3:
            self.apply_tuesday = True
        elif dow == 4:
            self.apply_wednesday = True
        elif dow == 5:
            self.apply_thursday = True
        elif dow == 6:
            self.apply_friday = True
        elif dow == 7:
            self.apply_saturday = True
        elif dow == 8:
            self.apply_holiday = True
        else:
            raise ValueError('ScheduleRule input "{}" is not an acceptable '
                             'dow integer.'.format(dow))

    def does_rule_apply(self, doy, dow=None):
        """Check if this rule applies to a given day of the year and day of the week.

        Args:
            doy: An integer between 1 anf 365 for the day of the year to test.
            dow: An integer between 1 anf 7 for the day of the week to test. If None,
                this value will be derived from the doy, assuming the first day of
                the year is a Sunday.
        """
        dow = dow if dow is not None else doy % 7
        return self.does_rule_apply_doy(doy) and self.week_apply_tuple[dow - 1]

    def does_rule_apply_leap_year(self, doy, dow=None):
        """Check if this rule applies to a given day of a leap year and day of the week.

        Args:
            doy: An integer between 1 anf 366 for the day of the leap year to test.
            dow: An integer between 1 anf 7 for the day of the week to test. If None,
                this value will be derived from the doy, assuming the first day of
                the year is a Sunday.
        """
        dow = dow if dow is not None else doy % 7
        return self.does_rule_apply_doy_leap_year(doy) and self.week_apply_tuple[dow - 1]

    def does_rule_apply_doy(self, doy):
        """Check if this rule applies to a given day of the year.

        Args:
            doy: An integer between 1 anf 365 for the day of the year to test.
        """
        return self._start_doy <= doy <= self._end_doy

    def does_rule_apply_doy_leap_year(self, doy):
        """Check if this rule applies to a given day of a leap year.

        Args:
            doy: An integer between 1 anf 366 for the day of the leap year to test.
        """
        st_doy = self._start_doy if self._start_date.month <= 2 else self._start_doy + 1
        end_doy = self._end_doy if self._end_date.month <= 2 else self._end_doy + 1
        return st_doy <= doy <= end_doy

    @classmethod
    def from_days_applied(cls, schedule_day, applicable_days=None,
                          start_date=None, end_date=None):
        """Initialize a ScheduleRule using a list of days when the rule is applied.

        Args:
            schedule_day: A ScheduleDay object associated with this rule.
            applicable_days: A list of text strings for the days when theScheduleRule
                will be applied. For example ['holiday', 'weekend'].
                The following options are acceptable:
                'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
                'saturday', 'holiday', 'weekday', 'weekend', 'all'
            start_date: A ladybug Date object for the start of the period over which
                the schedule_day will be applied. If None, Jan 1 will be used.
            end_date: A ladybug Date object for the end of the period over which
                the schedule_day will be applied. If None, Dec 31 will be used.
        """
        rule = cls(schedule_day, start_date=start_date, end_date=end_date)
        if applicable_days is not None:
            for day in applicable_days:
                rule.apply_day_by_name(day)
        return rule

    @classmethod
    def from_dict(cls, data):
        """Create a ScheduleRule from a dictionary.

        Args:
            data: ScheduleRule dictionary following the format below.

        .. code-block:: json

            {
            "type": 'ScheduleRule'
            "schedule_day": {
                "type": 'ScheduleDay',
                "name": 'Office Occupancy',
                "values": [0, 1, 0],
                "times": [(0, 0), (9, 0), (17, 0)],
                "interpolate": False
                }
            "apply_sunday": False,
            "apply_monday": True,
            "apply_tuesday": True,
            "apply_wednesday": True,
            "apply_thursday": True,
            "apply_friday": True,
            "apply_saturday": False,
            "apply_holiday": False,
            "start_date": (1, 1),
            "end_date": (12, 31)
            }
        """
        assert data['type'] == 'ScheduleRule', \
            'Expected ScheduleRule. Got {}.'.format(data['type'])

        schedule_day = ScheduleDay.from_dict(data['schedule_day'])
        apply_sunday = data['apply_sunday'] if 'apply_sunday' in data else False
        apply_monday = data['apply_monday'] if 'apply_monday' in data else False
        apply_tuesday = data['apply_tuesday'] if 'apply_tuesday' in data else False
        apply_wednesday = data['apply_wednesday'] if 'apply_wednesday' in data else False
        apply_thursday = data['apply_thursday'] if 'apply_thursday' in data else False
        apply_friday = data['apply_friday'] if 'apply_friday' in data else False
        apply_saturday = data['apply_saturday'] if 'apply_saturday' in data else False
        apply_holiday = data['apply_holiday'] if 'apply_holiday' in data else False
        start_date = Date.from_array(data['start_date']) if \
            'start_date' in data else cls._year_start
        end_date = Date.from_array(data['end_date']) if \
            'end_date' in data else cls._year_end

        return cls(schedule_day, apply_sunday, apply_monday, apply_tuesday,
                   apply_wednesday, apply_thursday, apply_friday, apply_saturday,
                   apply_holiday, start_date, end_date)

    def to_dict(self):
        """ScheduleRule dictionary representation."""
        return {'type': 'ScheduleRule',
                'schedule_day': self.schedule_day.to_dict(),
                'apply_sunday': self.apply_sunday,
                'apply_monday': self.apply_monday,
                'apply_tuesday': self.apply_tuesday,
                'apply_wednesday': self.apply_wednesday,
                'apply_thursday': self.apply_thursday,
                'apply_friday': self.apply_friday,
                'apply_saturday': self.apply_saturday,
                'apply_holiday': self.apply_holiday,
                'start_date': self.start_date.to_array(),
                'end_date': self.end_date.to_array()
                }

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def lock(self):
        """The lock() method will also lock the schedule_day."""
        self._locked = True
        self.schedule_day.lock()

    def unlock(self):
        """The unlock() method will also unlock the schedule_day."""
        self._locked = False
        self.schedule_day.unlock()

    @staticmethod
    def extract_all_from_schedule_week(week_idf_string, day_schedule_dict,
                                       start_date=None, end_date=None):
        """Extract all ScheduleRule objects from an IDF string of a Schedule:Week.

        Args:
            week_idf_string: A text string fully describing an EnergyPlus
                Schedule:Week:Daily or Schedule:Week:Compact.
            day_schedule_dict: A dictionary with the names of ScheduleDay objects as
                keys and the corresponding ScheduleDay objects as values. These objects
                will be used to build the ScheduleRules using the week_idf_string.
            start_date: A ladybug Date object for the start of the period over which
                the ScheduleRules apply. If None, Jan 1 will be used.
            end_date: A ladybug Date object for the end of the period over which
                the ScheduleRules apply. If None, Dec 31 will be used.

        Returns:
            schedule_rules: A list of ScheduleRule objects that together describe
                the Schedule:Week.
        """
        schedule_rules = []
        if week_idf_string.startswith('Schedule:Week:Daily,'):
            ep_strs = parse_idf_string(week_idf_string)
            applied_day_names = []
            for i, day_sch_name in enumerate(ep_strs[1:9]):
                if day_sch_name not in applied_day_names:  # make a new rule
                    rule = ScheduleRule(day_schedule_dict[day_sch_name],
                                        start_date=start_date, end_date=end_date)
                    rule.apply_day_by_dow(i + 1)
                    schedule_rules.append(rule)
                    applied_day_names.append(day_sch_name)
                else:  # edit one of the existing rules to apply it to the new day
                    sch_rule_index = applied_day_names.index(day_sch_name)
                    rule = schedule_rules[sch_rule_index]
                    rule.apply_day_by_dow(i + 1)
        else:
            ep_strs = parse_idf_string(week_idf_string, 'Schedule:Week:Compact,')
            for i in range(1, len(ep_strs), 2):
                day_type, day_sch_name = ep_strs[i].lower(), ep_strs[i + 1]
                rule = ScheduleRule(day_schedule_dict[day_sch_name])
                if 'alldays' in day_type:
                    rule.apply_all = True
                elif 'weekdays' in day_type:
                    rule.apply_weekday = True
                elif 'weekends' in day_type:
                    rule.apply_weekend = True
                elif 'sunday' in day_type:
                    rule.apply_sunday = True
                elif 'monday' in day_type:
                    rule.apply_monday = True
                elif 'tuesday' in day_type:
                    rule.apply_tuesday = True
                elif 'wednesday' in day_type:
                    rule.apply_wednesday = True
                elif 'thursday' in day_type:
                    rule.apply_thursday = True
                elif 'friday' in day_type:
                    rule.apply_friday = True
                elif 'saturday' in day_type:
                    rule.apply_saturday = True
                elif 'holiday' in day_type:
                    rule.apply_holiday = True
                elif 'allotherdays' in day_type:
                    apply_mtx = [rul.week_apply_tuple for rul in schedule_rules]
                    for j, dow in enumerate(zip(*apply_mtx)):
                        if not any(dow):
                            rule.apply_day_by_dow(j + 1)
                    apply_hol = [rul.apply_holiday for rul in schedule_rules]
                    if not any(apply_hol):
                        rule.apply_holiday = True
                if len(rule.days_applied) != 0:
                    schedule_rules.append(rule)
        return schedule_rules

    def _check_start_before_end(self):
        """Check that the start_date is before the end_date."""
        assert self._start_date < self._end_date, 'ScheduleRule start_date must come ' \
            'before end_date. {} comes after {}.'.format(self.start_date, self.end_date)

    @staticmethod
    def _check_date(date, date_name='date'):
        assert isinstance(date, Date), 'Expected ladybug Date for ' \
            'ScheduleRule {}. Got {}.'.format(date_name, type(date))

    @staticmethod
    def _doy_non_leap_year(date):
        """Get a doy for a non-leap-year even when the input date is for a leap year."""
        if not date.leap_year:
            return date.doy
        else:
            return date.doy if date <= Date(2, 29, True) else date.doy - 1

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (hash(self.schedule_day), self.schedule_day, self.apply_sunday,
                self.apply_monday, self.apply_tuesday, self.apply_wednesday,
                self.apply_thursday, self.apply_friday, self.apply_saturday,
                self.apply_holiday, hash(self.start_date), hash(self.end_date))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, ScheduleRule) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __copy__(self):
        return ScheduleRule(
            self.schedule_day.duplicate(), self.apply_sunday,
            self.apply_monday, self.apply_tuesday, self.apply_wednesday,
            self.apply_thursday, self.apply_friday, self.apply_saturday,
            self.apply_holiday, self.start_date, self.end_date)

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        return 'ScheduleRule:\n schedule_day: {}\n days applied: {}\n date_range: {} - {}'.format(
            self.schedule_day.name, ', '.join(self.days_applied), self.start_date, self.end_date)
