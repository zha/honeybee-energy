# coding=utf-8
"""Complete annual schedule object built from ScheduleDay and rules for applying them."""
from __future__ import division

from .day import ScheduleDay
from .rule import ScheduleRule
from .typelimit import ScheduleTypeLimit
from ..reader import parse_idf_string
from ..writer import generate_idf_string

from honeybee._lockable import lockable
from honeybee.typing import valid_ep_string, tuple_with_length

from ladybug.datacollection import HourlyContinuousCollection
from ladybug.header import Header
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.dt import Date
from ladybug.datatype.generic import GenericType

import re
import os


@lockable
class ScheduleRuleset(object):
    """A complete schedule assembled from DaySchedules and ScheduleRules.

    Properties:
        name
        default_day_schedule
        schedule_rules
        schedule_type_limit
        summer_designday_schedule
        winter_designday_schedule
        day_schedules
        is_constant
        is_single_week
    """
    __slots__ = ('_name', '_default_day_schedule', '_summer_designday_schedule',
                 '_winter_designday_schedule', '_schedule_rules',
                 '_schedule_type_limit', '_locked')
    _dow_text_to_int = {'sunday': 1, 'monday': 2, 'tuesday': 3, 'wednesday': 4,
                        'thursday': 2, 'friday': 3, 'saturday': 7}
    _schedule_week_comments = (
        'name', 'sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
        'saturday', 'holiday', 'summer design day', 'winter design day',
        'custom day 1', 'custom day 2')

    def __init__(self, name, default_day_schedule, schedule_rules=None,
                 schedule_type_limit=None, summer_designday_schedule=None,
                 winter_designday_schedule=None):
        """Initialize Schedule Ruleset.

        Args:
            name: Text string for the schedule name. Must be <= 100 characters.
                Can include spaces but special characters will be stripped out.
            default_day_schedule: A DaySchedule object that will be used for all
                days where there is no ScheduleRule applied.
            schedule_rules: A list of ScheduleRule objects that note exceptions
                to the default_day_schedule. These rules should be ordered from
                highest to lowest priority.
            schedule_type_limit: A ScheduleTypeLimit object that will be used to
                validate schedule values against upper/lower limits and assign units
                to the schedule values. If None, no validation will occur.
            summer_designday_schedule: A DaySchedule object that will be used for
                the summer design day (used to size the cooling system).
            winter_designday_schedule: A DaySchedule object that will be used for
                the winter design day (used to size the heating system).
        """
        self._locked = False  # unlocked by default
        self.name = name
        self.default_day_schedule = default_day_schedule
        self.schedule_rules = schedule_rules
        self.schedule_type_limit = schedule_type_limit
        self.summer_designday_schedule = summer_designday_schedule
        self.winter_designday_schedule = winter_designday_schedule

    @property
    def name(self):
        """Get or set the text string for schedule name."""
        return self._name

    @name.setter
    def name(self, name):
        self._name = valid_ep_string(name, 'schedule ruleset name')

    @property
    def default_day_schedule(self):
        """Get or set the DaySchedule object that will be used by default."""
        return self._default_day_schedule

    @default_day_schedule.setter
    def default_day_schedule(self, schedule):
        assert isinstance(schedule, ScheduleDay), 'Expected ScheduleDay for ' \
            'ScheduleRuleset default_day_schedule. Got {}.'.format(type(schedule))
        self._check_schedule_parent(schedule, 'default_day_schedule')
        self._default_day_schedule = schedule

    @property
    def schedule_rules(self):
        """Get or set an array of ScheduleRules that note exceptions to the default.

        These rules are ordered from highest priority to lowest priority meaning that,
        if two rules cover the same date range and day of the week, the rule that comes
        first in this list will take precedence. Following this logic, you typically
        want rules that only apply for part of a year to preceed rules that are
        applied over the whole year. This way, the schedule over the whole year doesn't
        overwrite the partial-year schedule underneath it.
        """
        return tuple(self._schedule_rules)

    @schedule_rules.setter
    def schedule_rules(self, rules):
        self._schedule_rules = self._check_schedule_rules(rules)

    @property
    def schedule_type_limit(self):
        """Get or set a ScheduleTypeLimit object used to assign units to schedule values.
        """
        return self._schedule_type_limit

    @schedule_type_limit.setter
    def schedule_type_limit(self, schedule_type):
        if schedule_type is not None:
            assert isinstance(schedule_type, ScheduleTypeLimit), 'Expected ' \
                'ScheduleTypeLimit for ScheduleRuleset schedule_type_limit. ' \
                'Got {}.'.format(type(schedule_type))
        self._schedule_type_limit = schedule_type

    @property
    def summer_designday_schedule(self):
        """Get or set the DaySchedule that will be used for the summer design day.

        Note that, if this property is None, the default_day_schedule is what is
        ultimately written into the IDF for the summer design day.
        """
        return self._summer_designday_schedule

    @summer_designday_schedule.setter
    def summer_designday_schedule(self, schedule):
        if schedule is not None:
            assert isinstance(schedule, ScheduleDay), 'Expected ScheduleDay for ' \
                'ScheduleRuleset summer_designday_schedule. Got {}.'.format(
                    type(schedule))
            self._check_schedule_parent(schedule, 'summer_designday_schedule')
        self._summer_designday_schedule = schedule

    @property
    def winter_designday_schedule(self):
        """Get or set the DaySchedule that will be used for the winter design day.

        Note that, if this property is None, the default_day_schedule is what is
        ultimately written into the IDF for the winter design day.
        """
        return self._winter_designday_schedule

    @winter_designday_schedule.setter
    def winter_designday_schedule(self, schedule):
        if schedule is not None:
            assert isinstance(schedule, ScheduleDay), 'Expected ScheduleDay for ' \
                'ScheduleRuleset winter_designday_schedule. Got {}.'.format(
                    type(schedule))
            self._check_schedule_parent(schedule, 'summer_designday_schedule')
        self._winter_designday_schedule = schedule

    @property
    def day_schedules(self):
        """Get a list of all unique ScheduleDay objects used in this ScheduleRuleset."""
        day_scheds = [self.default_day_schedule]
        if self._summer_designday_schedule is not None:
            day_scheds.append(self._summer_designday_schedule)
        if self._winter_designday_schedule is not None:
            day_scheds.append(self._winter_designday_schedule)
        for rule in self.schedule_rules:
            day_scheds.append(rule._schedule_day)
        return list(set(day_scheds))  # Since I disabled _check_schedule_parent, I need to remove duplicate

    @property
    def is_constant(self):
        """Boolean noting whether the schedule is representable with a single value."""
        return self.default_day_schedule.is_constant and self._schedule_rules == [] and \
            self._summer_designday_schedule is None and \
            self._winter_designday_schedule is None

    @property
    def is_single_week(self):
        """Boolean noting whether this schedule is representable with one week schedule.
        """
        if self._schedule_rules == []:
            return True
        elif all([sch._start_doy == 1 and sch._end_doy == 365
                  for sch in self._schedule_rules]):
            return True
        return False

    def add_rule(self, rule):
        """Add a ScheduleRule to this ScheduleRuleset.

        Note that adding a rule here will add it as highest priorty in the full list
        of schedule_rules, meaning it may overwrite other rules underneath it.

        Args:
            rule: A ScheduleRule object to be added to this ScheduleRuleset.
                ScheduleRule objects note the exceptions to the default_day_schedule.
        """
        self._check_rule(rule)
        self._check_schedule_parent(rule.schedule_day, 'schedule_rule')
        self._schedule_rules.insert(0, rule)

    def remove_rule(self, rule_index):
        """Remove a ScheduleRule from the schedule by its index in schedule_rules.

        Args:
            rule_index: An integer for the index of the rule to remove.
        """
        self._schedule_rules[rule_index].schedule_day._parent = None
        del self._schedule_rules[rule_index]

    def reorder_rule(self, rule_index, new_index=0):
        """Change the priority of a ScheduleRule in the full schedule_rules list.

        Lower indices (ordered first) in the schedule_rules indicate the rule has
        a higher priority.

        Args:
            rule_index: An integer for the index of the rule to reorder.
            new_index: An integer for the new index of the rule. The default is 0,
                which will re-insert the selected rule at the top of the
                priority list.
        """
        self._schedule_rules.insert(new_index, self._schedule_rules.pop(rule_index))

    def values(self, timestep=1, start_date=Date(1, 1), end_date=Date(12, 31),
               start_dow='Sunday', holidays=None, leap_year=False):
        """Get a list of sequential schedule values over the year at a given timestep.

        Note that there are two possible ways that these values can be mapped to
        corresponding times. See the ScheduleDay.values_at_timestep method
        documentation for a complete description of these two interpretations.

        Args:
            timestep: An integer for the number of steps per hour at which to return
                the resulting values.
            start_date: An optional ladybug Date object for when to start the list
                of values. Default: 1 Jan.
            end_date: An optional ladybug Date object for when to end the list
                of values. Default: 31 Dec.
            start_dow: An optional text string for the starting day of the week.
                Default: Sunday.
            holidays: An optional list of ladybug Date objects for the holidays. For
                any holiday in this list, schedule rules set to apply_holiday will
                take effect.
            leap_year: Boolean to note whether the generated values should be for a
                leap year (True) or a non-leap year (False). Default: False.
        """
        # get the values over the day for each of the ScheduleDay objects
        sch_day_vals = [rule.schedule_day.values_at_timestep(timestep)
                        for rule in self._schedule_rules]
        sch_day_vals.append(self.default_day_schedule.values_at_timestep(timestep))
        # ensure that everything is consistent across leap years
        if start_date.leap_year is not leap_year:
            start_date = Date(start_date.month, start_date.day, leap_year)
        if end_date.leap_year is not leap_year:
            end_date = Date(end_date.month, end_date.day, leap_year)
        # ensure start date is before end date
        assert start_date <= end_date, 'ScheduleRuleset values() start_date must come ' \
            'before end_date. {} comes after {}.'.format(start_date, end_date)
        # process the holidays if they are input
        if holidays is not None:
            hol_doy = []
            for hol in holidays:
                if hol.leap_year is not leap_year:
                    hol = Date(hol.month, hol.day, leap_year)
                hol_doy.append(hol.doy)
        else:
            hol_doy = []
        # process the start_dow into an integer.
        dow = self._dow_text_to_int[start_dow.lower()]
        # generate the full list of annual values
        if not leap_year:
            return self._get_sch_values(
                sch_day_vals, dow, start_date, end_date, hol_doy)
        else:
            return self._get_sch_values_leap_year(
                sch_day_vals, dow, start_date, end_date, hol_doy)

    def data_collection(self, timestep=1, start_date=Date(1, 1), end_date=Date(12, 31),
                        start_dow='Sunday', holidays=None, leap_year=False):
        """Get a ladybug DataCollection representing this schedule at a given timestep.

        Note that ladybug DataCollections always follow the "Ladybug Tools
        Interpretation" of date time values as noted in the
        ScheduleDay.values_at_timestep documentation.

        Args:
            timestep: An integer for the number of steps per hour at which to make
                the resulting DataCollection.
            start_date: An optional ladybug Date object for when to start the
                DataCollection. Default: 1 Jan.
            end_date: An optional ladybug Date object for when to end the
                DataCollection. Default: 31 Dec.
            start_dow: An optional text string for the starting day of the week.
                Default: Sunday.
            holidays: An optional list of ladybug Date objects for the holidays. For
                any holiday in this list, schedule rules set to apply_holiday will
                take effect.
            leap_year: Boolean to note whether the generated values should be for a
                leap year (True) or a non-leap year (False). Default: False.
        """
        a_period = AnalysisPeriod(start_date.month, start_date.day, 0,
                                  end_date.month, end_date.day, 23, timestep, leap_year)
        if self.schedule_type_limit is not None:
            data_type = self.schedule_type_limit.data_type
            unit = self.schedule_type_limit.unit
        else:
            unit = 'unknown'
            data_type = GenericType('Unknown Data Type', unit)
        header = Header(data_type, unit, a_period, metadata={'schedule': self.name})
        values = self.values(timestep, start_date, end_date, start_dow,
                             holidays, leap_year)
        return HourlyContinuousCollection(header, values)

    @classmethod
    def from_constant_value(cls, name, value, schedule_type_limit=None):
        """Create a ScheduleRuleset fromm a single constant value.

        Args:
            name: Text string for the schedule name. Must be <= 100 characters.
                Can include spaces but special characters will be stripped out.
            value: A single constant value to be applied throughout the whole year.
            schedule_type_limit: A ScheduleTypeLimit object that will be used to
                validate schedule values against upper/lower limits and assign
                units to the schedule values.
        """
        default_sched = ScheduleDay('{}_Day Schedule'.format(name), [value])
        return cls(name, default_sched, None, schedule_type_limit)

    @classmethod
    def from_daily_values(cls, name, daily_values, timestep=1, schedule_type_limit=None):
        """Create a ScheduleRuleset from a list of repeating daily values at a timestep.

        Args:
            name: Text string for the schedule name. Must be <= 100 characters.
                Can include spaces but special characters will be stripped out.
            daily_values: A list of [24 * timestep] numbers for schedule values.
            timestep: An integer for the number of steps per hour that the input
                values correspond to.  For example, if each value represents 30
                minutes, the timestep is 2. For 15 minutes, it is 4. Default is 1,
                meaning each value represents a single hour. Must be one of the
                following: (1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60).
            schedule_type_limit: A ScheduleTypeLimit object that will be used to
                validate schedule values against upper/lower limits and assign units
                to the schedule values.
        """
        default_sched = ScheduleDay.from_values_at_timestep(
            '{}_Day Schedule'.format(name), daily_values, timestep)
        return cls(name, default_sched, None, schedule_type_limit)

    @classmethod
    def from_week_daily_values(
            cls, name, sunday_values, monday_values, tuesday_values, wednesday_values,
            thursday_values, friday_values, saturday_values, holiday_values,
            timestep=1, schedule_type_limit=None,
            summer_designday_values=None, winter_designday_values=None):
        """Create a ScheduleRuleset from lists of daily values for each day of the week.

        Args:
            name: Text string for the schedule name. Must be <= 100 characters.
                Can include spaces but special characters will be stripped out.
            sunday_values: A list of [24 * timestep] numerical values for Sundays.
            monday_values: A list of [24 * timestep] numerical values for Mondays.
            tuesday_values: A list of [24 * timestep] numerical values for Tuesdays.
            wednesday_values: A list of [24 * timestep] numerical values for Wednesdays.
            thursday_values: A list of [24 * timestep] numerical values for Thursdays.
            friday_values: A list of [24 * timestep] numerical values for Fridays.
            saturday_values: A list of [24 * timestep] numerical values for Saturdays.
            holiday_values: A list of [24 * timestep] numerical values for Holidays.
            timestep: An integer for the number of steps per hour that the input
                values correspond to.  For example, if each value represents 30
                minutes, the timestep is 2. For 15 minutes, it is 4. Default is 1,
                meaning each value represents a single hour. Must be one of the
                following: (1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30, 60).
            schedule_type_limit: A ScheduleTypeLimit object that will be used to
                validate schedule values against upper/lower limits and assign
                units to the schedule values.
            summer_designday_values: A list of [24 * timestep] numerical values for
                the summer design day. If None, the daily schedule with the highest
                average value will be used.
            winter_designday_values: A list of [24 * timestep] numerical values for
                the winter design day. If None, the daily schedule with the lowest
                average value will be used.
        """
        # process the rules for the days of the week and holidays
        schedule_rules = []
        applied_day_values = []
        all_vals = (sunday_values, monday_values, tuesday_values, wednesday_values,
                    thursday_values, friday_values, saturday_values, holiday_values)
        for i, day_vals in enumerate(all_vals):
            if day_vals not in applied_day_values:  # make a new ScheduleDay and rule
                d_name = '{}_{}'.format(name, cls._schedule_week_comments[i + 1].title())
                sch_day = ScheduleDay.from_values_at_timestep(d_name, day_vals, timestep)
                rule = ScheduleRule(sch_day)
                rule.apply_day_by_dow(i + 1)
                schedule_rules.append(rule)
                applied_day_values.append(day_vals)
            else:  # edit one of the existing rules to apply it to the new day
                for count, sch in enumerate(applied_day_values):
                    if day_vals == sch:
                        sch_rule_index = count
                rule = schedule_rules[sch_rule_index]
                rule.apply_day_by_dow(i + 1)

        # get ScheduleDay for summer and winter design days
        avg_day_vals = [sum(vals) / len(vals) for vals in applied_day_values]
        if summer_designday_values is None:
            sch_i = avg_day_vals.index(max(avg_day_vals))
            summer = schedule_rules[sch_i]._schedule_day.duplicate()
            summer.name = '{}_SmrDsn'.format(summer.name)
        else:
            summer = ScheduleDay.from_values_at_timestep(
                '{}_SmrDsn'.format(name), summer_designday_values, timestep)
        if winter_designday_values is None:
            sch_i = avg_day_vals.index(min(avg_day_vals))
            winter = schedule_rules[sch_i]._schedule_day.duplicate()
            summer.name = '{}_WntrDsn'.format(summer.name)
        else:
            winter = ScheduleDay.from_values_at_timestep(
                '{}_WntrDsn'.format(name), winter_designday_values, timestep)

        return cls(name, schedule_rules[0].schedule_day, schedule_rules[1:],
                   schedule_type_limit, summer, winter)

    @classmethod
    def from_week_day_schedules(
            cls, name, sunday_schedule, monday_schedule, tuesday_schedule,
            wednesday_schedule, thursday_schedule, friday_schedule, saturday_schedule,
            holiday_schedule, summer_designday_schedule, winter_designday_schedule,
            schedule_type_limit=None):
        """Create a ScheduleRuleset from ScheduleDay objects for each day of the week.

        Args:
            name: Text string for the schedule name. Must be <= 100 characters.
                Can include spaces but special characters will be stripped out.
            sunday_schedule: A ScheduleDay for Sundays.
            monday_schedule: A ScheduleDay for Mondays.
            tuesday_schedule: A ScheduleDay for Tuesdays.
            wednesday_schedule: A ScheduleDay for Wednesdays.
            thursday_schedule: A ScheduleDay for Thursdays.
            friday_schedule: A ScheduleDay for Fridays.
            saturday_schedule: A ScheduleDay for Saturdays.
            holiday_schedule: A ScheduleDay for Holidays.
            summer_designday_schedule: A ScheduleDay for the summer design day.
            winter_designday_schedule: A ScheduleDay for the winter design day.
            schedule_type_limit: A ScheduleTypeLimit object that will be used to
                validate schedule values against upper/lower limits and assign
                units to the schedule values.
        """
        schedule_rules = []
        applied_day_names = []
        all_sched = (sunday_schedule, monday_schedule, tuesday_schedule,
                     wednesday_schedule, thursday_schedule, friday_schedule,
                     saturday_schedule, holiday_schedule)
        for i, day_sch in enumerate(all_sched):
            if day_sch.name not in applied_day_names:  # make a new rule
                rule = ScheduleRule(day_sch)
                rule.apply_day_by_dow(i + 1)
                schedule_rules.append(rule)
                applied_day_names.append(day_sch.name)
            else:  # edit one of the existing rules to apply it to the new day
                sch_rule_index = applied_day_names.index(day_sch.name)
                rule = schedule_rules[sch_rule_index]
                rule.apply_day_by_dow(i + 1)
        if summer_designday_schedule.name in applied_day_names:  # avoid duplicate
            summer_designday_schedule = summer_designday_schedule.duplicate()
            summer_designday_schedule.name = \
                '{}_SmrDsn'.format(summer_designday_schedule.name)
        if winter_designday_schedule.name in applied_day_names:    # avoid duplicate
            winter_designday_schedule = winter_designday_schedule.duplicate()
            winter_designday_schedule.name = \
                '{}_WntrDsn'.format(winter_designday_schedule.name)
        return cls(name, schedule_rules[0].schedule_day, schedule_rules[1:],
                   schedule_type_limit, summer_designday_schedule,
                   winter_designday_schedule)

    @classmethod
    def from_idf(cls, year_idf_string, week_idf_strings, day_idf_strings,
                 type_idf_string=None):
        """Create a ScheduleRuleset from an EnergyPlus IDF text strings.

        Args:
            year_idf_string: A text string fully describing an EnergyPlus
                Schedule:Year.
            week_idf_strings: A list of text strings for all of the Schedule:Week
                objects used in the Schedule:Year.
            day_idf_strings: A list of text strings for all of the Schedule:Day
                objects used in the week_idf_strings.
            type_idf_string: An optional text string for the ScheduleTypeLimits.
                If None, the resulting schedule will have no ScheduleTypeLimit.
        """
        # process the schedule components
        day_schedule_dict = cls._idf_day_schedule_dictionary(day_idf_strings)
        week_sch_dict, week_dd_dict = cls._idf_week_schedule_dictionary(
            week_idf_strings, day_schedule_dict)
        schedule_type = ScheduleTypeLimit.from_idf(type_idf_string) if type_idf_string \
            is not None else None

        # use the year schedule to bring it all together
        year_sch = parse_idf_string(year_idf_string)
        all_rules = []
        for i in range(2, len(year_sch), 5):
            rules = week_sch_dict[year_sch[i]]
            st_date = Date(int(year_sch[i + 1]), int(year_sch[i + 2]))
            end_date = Date(int(year_sch[i + 3]), int(year_sch[i + 4]))
            for rule in rules:
                rule.start_date = st_date
                rule.end_date = end_date
            all_rules.extend(rules)
        default_day_schedule = all_rules[0].schedule_day
        summer_dd_sch, winter_dd_sch = week_dd_dict[year_sch[2]]
        sched = cls(year_sch[0], default_day_schedule, all_rules[1:], schedule_type)
        cls._apply_designdays_with_check(sched, summer_dd_sch, winter_dd_sch)
        return sched

    @classmethod
    def from_dict(cls, data):
        """Create a ScheduleRuleset from a dictionary.

        Note that the dictionary must be a non-abridged version for this
        classmethod to work.

        Args:
            data: ScheduleRuleset dictionary following the format below.

        .. code-block:: json

            {
            "type": 'ScheduleRuleset',
            "name": 'Office Occupancy',
            "default_day_schedule": {}, // ScheduleDay dictionary representation
            "schedule_rules": [], // list of ScheduleRule dictionaries
            "schedule_type_limit": {}, // ScheduleTypeLimit dictionary representation
            "summer_designday_schedule": {}, // ScheduleDay dictionary representation
            "winter_designday_schedule": {} // ScheduleDay dictionary representation
            }
        """
        assert data['type'] == 'ScheduleRuleset', \
            'Expected ScheduleRuleset. Got {}.'.format(data['type'])

        default_sched = ScheduleDay.from_dict(data['default_day_schedule'])
        rules = None
        if 'schedule_rules' in data and data['schedule_rules'] is not None:
            rules = [ScheduleRule.from_dict(rule) for rule in data['schedule_rules']]
        sched_type = None
        if 'schedule_type_limit' in data and data['schedule_type_limit'] is not None:
            sched_type = ScheduleTypeLimit.from_dict(data['schedule_type_limit'])
        summer_sched = None
        if 'summer_designday_schedule' in data and \
                data['summer_designday_schedule'] is not None:
            summer_sched = ScheduleDay.from_dict(data['summer_designday_schedule'])
        winter_sched = None
        if 'winter_designday_schedule' in data and \
                data['winter_designday_schedule'] is not None:
            winter_sched = ScheduleDay.from_dict(data['winter_designday_schedule'])

        return cls(data['name'], default_sched, rules, sched_type,
                   summer_sched, winter_sched)

    def to_rules(self, start_date, end_date):
        """Get all of rules needed to implement this ScheduleRuleset over a date range.

        This is useful when you want to apply this entire ScheduleRuleset over a
        particular time period of another ScheduleRuleset.

        Args:
            start_date: A ladybug Date object for the start of the period that rules
                should be obtained.
            end_date: A ladybug Date object for the end of the period that rules
                should be obtained.
        """
        # check the date inputs
        ScheduleRule._check_date(start_date)
        ScheduleRule._check_date(end_date)
        st_doy = ScheduleRule._doy_non_leap_year(start_date)
        end_doy = ScheduleRule._doy_non_leap_year(end_date)

        # assemble all of the rules already applied to this ScheduleRuleset
        rules = []
        for rule in self._schedule_rules:
            if (rule._start_doy < st_doy and rule._end_doy < st_doy) or \
                    (rule._start_doy > st_doy and rule._end_doy > end_doy):
                pass  # no overlap with input period
            else:
                new_rule = rule.duplicate()
                if rule._start_doy < st_doy:
                    new_rule.start_date = start_date
                if rule._end_doy > end_doy:
                    new_rule.end_date = end_date
                rules.append(new_rule)

        # add the default_day_schedule for all days not covered by rules
        default_rule = ScheduleRule(self.default_day_schedule.duplicate(),
                                    start_date=start_date, end_date=end_date)
        for dow in range(7):
            for rule in rules:
                if rule.week_apply_tuple[dow]:
                    break
            else:  # no rule applies; use default_day_schedule.
                default_rule.apply_day_by_dow(dow + 1)
        # check rules that apply on holidays
        for rule in rules:  # see if rules apply
            if rule.apply_holiday:
                break
        else:  # no rule applies; use default_day_schedule.
            default_rule.apply_holiday = True
        rules.append(default_rule)

        return rules

    def to_idf(self):
        """IDF string representation of the schedule.

        Note that this method only outputs Schedule:Year and Schedule:Week objects
        (or a Schedule:Constant object if applicable). However, to write the full
        schedule into an IDF, the schedules's day_schedules must also be
        written as well as the ScheduleTypeLimit object.

        The method is set up this way primarily to give better control over the export
        process. For example, you usually want to see if there are other schedules
        in a model using the same ScheduleTypeLimit object and then write it into
        the IDF only once rather than writing it multiple times for each schedule
        that references it. ScheduleDay objects can (sometimes) follow a similar
        logic where the same ScheduleDay objects are used by multiple ScheduleRulesets,
        though this is less common than sharing ScheduleTypeLimit objects.

        Returns:
            year_schedule: Text string representation of the Schedule:Year
                describing this schedule. This will be a Schedule:Constant if this
                schedule can be described as such.
            week_schedules: A list of Schedule:Week:Daily test strings that are
                referenced in the year_schedule. Will be None when year_schedule is
                a Schedule:Constant.
        """
        # beginning fields used for all schedules
        year_fields = [self.name]
        shc_typ = self._schedule_type_limit.name if \
            self._schedule_type_limit is not None else ''
        year_fields.append(shc_typ)
        year_comments = ['schedule name', 'schedule type limits']

        # check if this schedule can simply be represented with a Schedule:Constant
        if self.is_constant:
            year_fields.append(self.default_day_schedule[0])
            year_comments.append('value')
            year_schedule = generate_idf_string(
                'Schedule:Constant', year_fields, year_comments)
            return year_schedule, None

        # prepare to create a full Schedule:Year
        date_comments = ['start month {}', 'start day {}', 'end month {}', 'end day {}']
        week_schedules = []

        if self.is_single_week:  # create the only one week schedule
            wk_sch, wk_sch_name = \
                self._idf_week_schedule_from_rule_indices(range(len(self)), 1)
            week_schedules.append(wk_sch)
            yr_wk_s_names = [wk_sch_name]
            yr_wk_dt_range = [[Date(1, 1), Date(12, 31)]]
        else:  # create a set of week schedules throughout the year
            # loop through 365 days of the year to find unique combinations of rules
            rules_each_day = []
            for doy in range(1, 366):
                rules_on_doy = tuple(i for i, rule in enumerate(self._schedule_rules)
                                     if rule._start_doy <= doy <= rule._end_doy)
                rules_each_day.append(rules_on_doy)
            unique_rule_sets = set(rules_each_day)
            # check if any combination yield the same week schedule and remove duplicates
            week_tuples = [tuple(self._get_week_list(rule_set))
                           for rule_set in unique_rule_sets]
            unique_week_tuples = list(set(week_tuples))
            # create the unique week schedules from the combinations of rules
            week_sched_names = []
            for i, week_list in enumerate(unique_week_tuples):
                wk_schedule, wk_sch_name = \
                    self._idf_week_schedule_from_week_list(week_list, i + 1)
                week_schedules.append(wk_schedule)
                week_sched_names.append(wk_sch_name)
            # create a disctionary mapping unique rule index lists to week schedule names
            rule_set_map = {}
            for rule_i, week_list in zip(unique_rule_sets, week_tuples):
                unique_week_i = unique_week_tuples.index(week_list)
                rule_set_map[rule_i] = week_sched_names[unique_week_i]
            # loop through all 365 days of the year to find when rules change
            yr_wk_s_names = []
            yr_wk_dt_range = []
            prev_week_sched = None
            for doy in range(1, 366):
                week_sched = rule_set_map[rules_each_day[doy - 1]]
                if week_sched != prev_week_sched:  # change to a new rule set
                    yr_wk_s_names.append(week_sched)
                    if doy != 1:
                        yr_wk_dt_range[-1].append(Date.from_doy(doy - 1))
                        yr_wk_dt_range.append([Date.from_doy(doy)])
                    else:
                        yr_wk_dt_range.append([Date(1, 1)])
                    prev_week_sched = week_sched
            yr_wk_dt_range[-1].append(Date(12, 31))

        # create the year fields and comments
        for i, (wk_sch_name, dt_range) in enumerate(zip(yr_wk_s_names, yr_wk_dt_range)):
            year_fields.append(wk_sch_name)
            count = i + 1
            year_comments.append('week schedule name {}'.format(count))
            year_fields.extend([dt_range[0].month, dt_range[0].day,
                                dt_range[1].month, dt_range[1].day])
            for com in date_comments:
                year_comments.append(com.format(count))

        year_schedule = generate_idf_string('Schedule:Year', year_fields, year_comments)
        return year_schedule, week_schedules

    def to_dict(self, abridged=False):
        """Schedule Ruleset dictionary representation.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True),
                which only specifies the name of the ScheduleTypeLimit. Default: False.
        """
        # required properties
        base = {'type': 'ScheduleRuleset'} if not \
            abridged else {'type': 'ScheduleRulesetAbridged'}
        base['name'] = self.name
        base['default_day_schedule'] = self.default_day_schedule.to_dict()

        # optional properties
        if len(self._schedule_rules) != 0:
            base['schedule_rules'] = [rule.to_dict() for rule in self._schedule_rules]
        if self._summer_designday_schedule is not None:
            base['summer_designday_schedule'] = self._summer_designday_schedule.to_dict()
        if self._winter_designday_schedule is not None:
            base['winter_designday_schedule'] = self._winter_designday_schedule.to_dict()

        # optional properties that can be abridged
        if self._schedule_type_limit is not None:
            if not abridged:
                base['schedule_type_limit'] = self._schedule_type_limit.to_dict()
            else:
                base['schedule_type_limit'] = self._schedule_type_limit.name
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def lock(self):
        """The lock() method also locks the ScheduleDay and ScheduleRule objects."""
        self._locked = True
        self._default_day_schedule.lock()
        if self._summer_designday_schedule is not None:
            self._summer_designday_schedule.lock()
        if self._winter_designday_schedule is not None:
            self._winter_designday_schedule.lock()
        for rule in self._schedule_rules:
            rule.lock()

    def unlock(self):
        """The unlock() method also unlocks the ScheduleDay and ScheduleRule objects."""
        self._locked = False
        self._default_day_schedule.unlock()
        if self._summer_designday_schedule is not None:
            self._summer_designday_schedule.unlock()
        if self._winter_designday_schedule is not None:
            self._winter_designday_schedule.unlock()
        for rule in self._schedule_rules:
            rule.unlock()

    @staticmethod
    def extract_all_from_idf_file(idf_file):
        """Extract all ScheduleRuleset objects from an EnergyPlus IDF file.

        Args:
            idf_file: A path to an IDF file containing objects for Schedule:Year and
                corresponding Schedule:Week and Schedule:Day objects. The Schedule:Year
                will be used to assemble all of these into a ScheduleRuleset.

        Returns:
            schedules: A list of all Schedule:Year objects in the IDF file as
                honeybee_energy ScheduleRuleset objects.
        """
        # check the file
        assert os.path.isfile(idf_file), 'Cannot find an idf file at {}'.format(idf_file)
        with open(idf_file, 'r') as ep_file:
            file_contents = ep_file.read()
        # extract all of the ScheduleDay objects
        day_pattern1 = re.compile(r"(?i)(Schedule:Day:Interval,[\s\S]*?;)")
        day_pattern2 = re.compile(r"(?i)(Schedule:Day:Hourly,[\s\S]*?;)")
        day_pattern3 = re.compile(r"(?i)(Schedule:Day:List,[\s\S]*?;)")
        day_sch_str = day_pattern1.findall(file_contents) + \
            day_pattern2.findall(file_contents) + day_pattern3.findall(file_contents)
        day_schedule_dict = ScheduleRuleset._idf_day_schedule_dictionary(day_sch_str)
        # extract all of the Schedule:Week objects
        week_pattern_1 = re.compile(r"(?i)(Schedule:Week:Daily,[\s\S]*?;)")
        week_pattern_2 = re.compile(r"(?i)(Schedule:Week:Compact,[\s\S]*?;)")
        week_sch_str = week_pattern_1.findall(file_contents) + week_pattern_2.findall(file_contents)
        week_sch_dict, week_dd_dict = ScheduleRuleset._idf_week_schedule_dictionary(
            week_sch_str, day_schedule_dict)
        # extract all of the ScheduleTypeLimit objects
        type_pattern = re.compile(r"(?i)(ScheduleTypeLimits,[\s\S]*?;)")
        sch_type_str = type_pattern.findall(file_contents)
        sch_type_dict = ScheduleRuleset._idf_schedule_type_dictionary(sch_type_str)
        # extract all of the Schedule:Year objects and convert to ScheduleRuleset
        year_pattern = re.compile(r"(?i)(Schedule:Year,[\s\S]*?;)")
        year_props = tuple(parse_idf_string(idf_string) for
                           idf_string in year_pattern.findall(file_contents))
        # extract all of the Schedule:Constant objects and convert to ScheduleRuleset
        constant_pattern = re.compile(r"(?i)(Schedule:Constant,[\s\S]*?;)")
        constant_props = tuple(parse_idf_string(idf_string) for
                               idf_string in constant_pattern.findall(file_contents))
        # compile all of the ScheduleRuleset objects from extracted properties
        schedules = []
        for year_sch in year_props:
            all_rules = []
            for i in range(2, len(year_sch), 5):
                rules = week_sch_dict[year_sch[i]]
                st_date = Date(int(year_sch[i + 1]), int(year_sch[i + 2]))
                end_date = Date(int(year_sch[i + 3]), int(year_sch[i + 4]))
                for rule in rules:
                    rule.start_date = st_date
                    rule.end_date = end_date
                all_rules.extend(rules)
            default_day_schedule = all_rules[0].schedule_day
            summer_dd_sch, winter_dd_sch = week_dd_dict[year_sch[2]]
            schedule_type = sch_type_dict[year_sch[1]] if year_sch[1] != '' else None
            sch_ruleset = ScheduleRuleset(
                year_sch[0], default_day_schedule, all_rules[1:], schedule_type)
            ScheduleRuleset._apply_designdays_with_check(
                sch_ruleset, summer_dd_sch, winter_dd_sch)
            schedules.append(sch_ruleset)
        for const_sch in constant_props:
            sched_val = float(const_sch[2]) if const_sch[2] != '' else 0
            schedule_type = sch_type_dict[const_sch[1]] if const_sch[1] != '' else None
            sch_ruleset = ScheduleRuleset.from_constant_value(
                const_sch[0], sched_val, schedule_type)
            schedules.append(sch_ruleset)
        return schedules

    @staticmethod
    def average_schedules(name, schedules, weights=None, timestep_resolution=1):
        """Create a ScheduleRuleset that is a weighted average between other ScheduleRulesets.

        Args:
            name: A name for the new averaged ScheduleRuleset.
            schedules: A list of ScheduleRuleset objects that will be averaged together
                to make a new ScheduleRuleset.
            weights: An optional list of fractioanl numbers with the same length
                as the input schedules that sum to 1. These will be used to weight
                each of the ScheduleRuleset objects in the resulting average schedule.
                If None, the individual schedules will be weighted equally.
            timestep_resolution: An optional integer for the timestep resolution
                at which the schedules will be averaged. Any schedule details
                smaller than this timestep will be lost in the averaging process.
                Default: 1.
        """
        # check the inputs
        assert isinstance(schedules, (list, tuple)), 'Expected a list of ScheduleDay ' \
            'objects for average_schedules. Got {}.'.format(type(schedules))
        if weights is None:
            weight = 1 / len(schedules)
            weights = [weight for i in schedules]
        else:
            weights = tuple_with_length(weights, len(schedules), float,
                                        'average schedules weights')
            assert sum(weights) == 1, 'Average schedule weights must sum to 1. ' \
                'Got {}.'.format(sum(weights))

        # if all input shcedules are single week, the averaging process is a lot simpler
        if all([sched.is_single_week for sched in schedules]):
            rule_indices = [range(len(sched)) for sched in schedules]
            return ScheduleRuleset._get_avg_week(name, schedules, weights, timestep_resolution,
                                                 rule_indices)
        else:
            # loop through 365 days of the year to find unique combinations of rules
            rules_each_day = []
            for doy in range(1, 366):
                rules_on_doy = tuple(tuple(
                    i for i, rule in enumerate(sched._schedule_rules)
                    if rule._start_doy <= doy <= rule._end_doy)
                    for sched in schedules)
                rules_each_day.append(rules_on_doy)
            unique_rule_sets = set(rules_each_day)
            # create the average week schedules from the unique combinations of rules
            week_schedules = []
            for i, rule_indices in enumerate(unique_rule_sets):
                week_name = '{}_{}'.format(name, i)
                week_sched = ScheduleRuleset._get_avg_week(week_name, schedules, weights,
                                                           timestep_resolution, rule_indices)
                week_schedules.append(week_sched)
            # create a disctionary mapping unique rule index lists to average week schedules
            rule_set_map = {}
            for rule_i, week_sched in zip(unique_rule_sets, week_schedules):
                rule_set_map[rule_i] = week_sched
            # loop through all 365 days of the year to find when rules change
            yr_wk_scheds = []
            yr_wk_dt_range = []
            prev_week_rules = None
            for doy in range(1, 366):
                week_rules = rules_each_day[doy - 1]
                if week_rules != prev_week_rules:  # change to a new rule set
                    yr_wk_scheds.append(rule_set_map[week_rules])
                    if doy != 1:
                        yr_wk_dt_range[-1].append(Date.from_doy(doy - 1))
                        yr_wk_dt_range.append([Date.from_doy(doy)])
                    else:
                        yr_wk_dt_range.append([Date(1, 1)])
                    prev_week_rules = week_rules
            yr_wk_dt_range[-1].append(Date(12, 31))

            # convert week ScheduleRulesets to_rules and assign start + end dates
            final_rules = []
            for wk_sch, dt_range in zip(yr_wk_scheds, yr_wk_dt_range):
                final_rules.extend(wk_sch.to_rules(dt_range[0], dt_range[1]))

            # add all rules to a final average SheduleRuleset
            default_day_schedule = final_rules[0].schedule_day
            summer_dd_sch = yr_wk_scheds[0].summer_designday_schedule.duplicate()
            winter_dd_sch = yr_wk_scheds[0].winter_designday_schedule.duplicate()
            schedule_type = schedules[0].schedule_type_limit
            return ScheduleRuleset(name, default_day_schedule, final_rules[1:],
                                   schedule_type, summer_dd_sch, winter_dd_sch)

    def _get_sch_values(self, sch_day_vals, dow, start_date, end_date, hol_doy):
        """Get a list of values over a date range for a typical year."""
        values = []
        for doy in range(start_date.doy, end_date.doy + 1):
            if dow > 7:  # reset the day of the week to sunday
                dow = 1
            if doy in hol_doy:
                for i, rule in enumerate(self._schedule_rules):  # see if rules apply
                    if rule.apply_holiday and rule.does_rule_apply_doy(doy):
                        values.extend(sch_day_vals[i])
                        break
                else:  # no rule applies; use default_day_schedule.
                    values.extend(sch_day_vals[-1])
            else:
                for i, rule in enumerate(self._schedule_rules):  # see if rules apply
                    if rule.does_rule_apply(doy, dow):
                        values.extend(sch_day_vals[i])
                        break
                else:  # no rule applies; use default_day_schedule.
                    values.extend(sch_day_vals[-1])
            dow += 1
        return values

    def _get_sch_values_leap_year(self, sch_day_vals, dow,
                                  start_date, end_date, hol_doy):
        """Get a list of values over a date range for a leap year."""
        values = []
        for doy in range(start_date.doy, end_date.doy + 1):
            if dow > 7:  # reset the day of the week to sunday
                dow = 1
            if doy in hol_doy:
                for i, rule in enumerate(self._schedule_rules):  # see if rules apply
                    if rule.apply_holiday and rule.does_rule_apply_doy_leap_year(doy):
                        values.extend(sch_day_vals[i])
                        break
                else:  # no rule applies; use default_day_schedule.
                    values.extend(sch_day_vals[-1])
            else:
                for i, rule in enumerate(self._schedule_rules):  # see if rules apply
                    if rule.does_rule_apply_leap_year(doy, dow):
                        values.extend(sch_day_vals[i])
                        break
                else:  # no rule applies; use default_day_schedule.
                    values.extend(sch_day_vals[-1])
            dow += 1
        return values

    def _get_week_list(self, rule_indices):
        """Get a list of the ScheduleDay names applied on each day of the week."""
        week_list = []
        for dow in range(7):
            for i in rule_indices:
                if self._schedule_rules[i].week_apply_tuple[dow]:
                    week_list.append(self._schedule_rules[i].schedule_day.name)
                    break
            else:  # no rule applies; use default_day_schedule.
                week_list.append(self.default_day_schedule.name)
        # check rules that apply on holidays
        for i, rule in enumerate(self._schedule_rules):  # see if rules apply
            if rule.apply_holiday:
                week_list.append(self._schedule_rules[i].schedule_day.name)
                break
        else:  # no rule applies; use default_day_schedule.
            week_list.append(self.default_day_schedule.name)
        return week_list

    def _get_extra_week_fields(self):
        """Get schedule names of extra days in Schedule:Week."""
        # add summer and winter design days
        week_fields = [self.summer_designday_schedule.name,
                       self.winter_designday_schedule.name]
        for i in range(2):  # add extra 2 custom days that no one uses
            week_fields.append(self.default_day_schedule.name)
        return week_fields

    def _idf_week_schedule_from_rule_indices(self, rule_indices, week_index):
        """Create an IDF string of a week schedule from a list of rules indices."""
        week_sch_name = '{}_Week {}'.format(self.name, week_index)
        week_fields = [week_sch_name]
        # check rules that apply for the days of the week
        week_fields.extend(self._get_week_list(rule_indices))
        # add extra daus (including summer and winter design days)
        week_fields.extend(self._get_extra_week_fields())
        week_schedule = generate_idf_string(
            'Schedule:Week:Daily', week_fields, self._schedule_week_comments)
        return week_schedule, week_sch_name

    def _idf_week_schedule_from_week_list(self, week_list, week_index):
        """Create an IDF string of a week schedule from a list ScheduleDay names."""
        week_sch_name = '{}_Week {}'.format(self.name, week_index)
        week_fields = [week_sch_name]
        week_fields.extend(week_list)
        week_fields.extend(self._get_extra_week_fields())
        week_schedule = generate_idf_string(
            'Schedule:Week:Daily', week_fields, self._schedule_week_comments)
        return week_schedule, week_sch_name

    def _check_schedule_parent(self, schedule, sch_type='child'):
        """Check that a ScheduleDay has only one parent."""
        # if schedule._parent is not None:
        #     raise ValueError(
        #         'ScheduleDay objects can be assigned to a ScheduleRuleset only once.\n'
        #         'ScheduleDay "{}" cannot be the {} of ScheduleRuleset "{}" since it is '
        #         'already assigned to "{}".\nTry duplicating the ScheduleDay, changing '
        #         'its name, and then assigning it to this ScheduleRuleset.'.format(
        #             schedule.name, sch_type, self.name, schedule._parent.name))
        # schedule._parent = self
        pass
    def _check_schedule_rules(self, rules):
        """Check schedule_rules whenever they come through the setter."""
        if rules is None:
            return []
        if not isinstance(rules, list):
            try:
                rules = list(rules)
            except (ValueError, TypeError):
                raise TypeError('ScheduleRuleset schedule_rules must be iterable.')
        for rule in rules:
            self._check_rule(rule)
            self._check_schedule_parent(rule.schedule_day, 'schedule_rule')
        return rules

    @staticmethod
    def _check_rule(rule):
        """Check that an individual rule is a ScheduleRule."""
        assert isinstance(rule, ScheduleRule), \
            'Expected ScheduleRule for ScheduleRuleset. Got {}.'.format(type(rule))

    @staticmethod
    def _apply_designdays_with_check(sched, summer_dd_sch, winter_dd_sch):
        """Apply summer + winter design day schedules with a check for duplicates."""
        try:
            sched.summer_designday_schedule = summer_dd_sch
        except ValueError:  # summer design day schedule is not unique
            summer_dd_sch = summer_dd_sch.duplicate()
            summer_dd_sch.name = '{}_SmrDsn'.format(summer_dd_sch.name)
            sched.summer_designday_schedule = summer_dd_sch
        try:
            sched.winter_designday_schedule = winter_dd_sch
        except ValueError:  # winter design day schedule is not unique
            winter_dd_sch = winter_dd_sch.duplicate()
            winter_dd_sch.name = '{}_WntrDsn'.format(winter_dd_sch.name)
            sched.winter_designday_schedule = winter_dd_sch

    @staticmethod
    def _idf_day_schedule_dictionary(day_idf_strings):
        """Get a dictionary of DaySchedule objects from an IDF string list."""
        day_schedule_dict = {}
        for sch_str in day_idf_strings:
            sch_str = sch_str.strip()
            sch_obj = ScheduleDay.from_idf(sch_str)
            day_schedule_dict[sch_obj.name] = sch_obj
        return day_schedule_dict

    @staticmethod
    def _idf_week_schedule_dictionary(week_idf_strings, day_sch_dict):
        """Get a dictionary of ScheduleRule objects from Schedule:Week strings."""
        week_schedule_dict = {}
        week_designday_dict = {}
        for sch_str in week_idf_strings:
            sch_str = sch_str.strip()
            rules = ScheduleRule.extract_all_from_schedule_week(sch_str, day_sch_dict)
            if sch_str.startswith('Schedule:Week:Daily,'):
                ep_strs = parse_idf_string(sch_str)
                summer_dd = day_sch_dict[ep_strs[9]]
                winter_dd = day_sch_dict[ep_strs[10]]
            else:
                ep_strs = parse_idf_string(sch_str, 'Schedule:Week:Compact,')
                summer_dd = winter_dd = rules[-1].schedule_day
                for i in range(1, len(ep_strs), 2):
                    day_type, day_sch_name = ep_strs[i].lower(), ep_strs[i + 1]
                    if 'summerdesignday' in day_type:
                        summer_dd = day_sch_dict[day_sch_name]
                    elif 'winterdesignday' in day_type:
                        winter_dd = day_sch_dict[day_sch_name]
            sch_week_name = ep_strs[0]
            week_schedule_dict[sch_week_name] = rules
            week_designday_dict[sch_week_name] = [summer_dd, winter_dd]
        return week_schedule_dict, week_designday_dict

    @staticmethod
    def _idf_schedule_type_dictionary(type_idf_strings):
        """Get a dictionary of ScheduleTypeLimit objects from ScheduleTypeLimits strings.
        """
        sch_type_dict = {}
        for type_str in type_idf_strings:
            type_str = type_str.strip()
            type_obj = ScheduleTypeLimit.from_idf(type_str)
            sch_type_dict[type_obj.name] = type_obj
        return sch_type_dict

    @staticmethod
    def _get_avg_week(name, schedules, weights, timestep_resolution, rule_indices):
        """Get an average week schedule across several schedules and rule_indices."""
        # get matrix with each ruleset schedule in rows and each day of week in cols
        val_mtx = []
        for s_i, sched in enumerate(schedules):
            week_list = []
            for dow in range(7):
                for i in rule_indices[s_i]:  # see if rules apply
                    if sched[i].week_apply_tuple[dow]:
                        week_list.append(sched[i].schedule_day)
                        break
                else:  # no rule applies; use default_day_schedule.
                    week_list.append(sched.default_day_schedule)
            # check rules that apply on holidays
            for i in rule_indices[s_i]:  # see if rules apply
                if sched[i].apply_holiday:
                    week_list.append(sched[i].schedule_day)
                    break
            else:  # no rule applies; use default_day_schedule.
                week_list.append(sched.default_day_schedule)
            # check the rules applied for summer and winter design days
            summer = sched.default_day_schedule if sched._summer_designday_schedule \
                is None else sched._summer_designday_schedule
            week_list.append(summer)
            winter = sched.default_day_schedule if sched._winter_designday_schedule \
                is None else sched._winter_designday_schedule
            week_list.append(winter)
            # add all values to the matrix
            val_mtx.append([day_sch.values_at_timestep(timestep_resolution)
                            for day_sch in week_list])
        # transpose the matrix and compute weighted average values for each dow
        avg_mtx = []
        for dow_list in zip(*val_mtx):
            sch_vals = [sum([val * weights[i] for i, val in enumerate(values)])
                        for values in zip(*dow_list)]
            avg_mtx.append(sch_vals)
        # create the final ScheduleRuleset from the values
        return ScheduleRuleset.from_week_daily_values(
            name, avg_mtx[0], avg_mtx[1], avg_mtx[2], avg_mtx[3], avg_mtx[4],
            avg_mtx[5], avg_mtx[6], avg_mtx[7], timestep_resolution,
            schedules[0].schedule_type_limit, avg_mtx[8], avg_mtx[9])

    def __len__(self):
        return len(self._schedule_rules)

    def __getitem__(self, key):
        return self._schedule_rules[key]

    def __iter__(self):
        return iter(self._schedule_rules)

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.name, hash(self.default_day_schedule),
                hash(self.summer_designday_schedule),
                hash(self.winter_designday_schedule), hash(self.schedule_type_limit)) + \
            tuple(hash(rule) for rule in self.schedule_rules)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, ScheduleRuleset) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __copy__(self):
        summer = self._summer_designday_schedule.duplicate() if \
            self._summer_designday_schedule is not None else None
        winter = self._winter_designday_schedule.duplicate() if \
            self._winter_designday_schedule is not None else None
        return ScheduleRuleset(
            self.name, self.default_day_schedule.duplicate(),
            [rule.duplicate() for rule in self._schedule_rules],
            self._schedule_type_limit, summer, winter)

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        return 'ScheduleRuleset:\n name: {}\n default_day: {}\n' \
            ' schedule_rules:\n  {}'.format(
                self.name, self.default_day_schedule.name,
                '\n  '.join([rule.schedule_day.name for rule in self._schedule_rules]))
