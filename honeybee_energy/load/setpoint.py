# coding=utf-8
"""Temperature (thermostat) and humidity (humidistat) setpoints for a thermal zone."""
from __future__ import division

from ._base import _LoadBase
from ..schedule.ruleset import ScheduleRuleset
from ..schedule.fixedinterval import ScheduleFixedInterval

from ..schedule.csvschedule import CSVSchedule
from ..schedule.necb import NECB

from ..reader import parse_idf_string
from ..writer import generate_idf_string

import honeybee_energy.lib.scheduletypelimits as _type_lib

from honeybee._lockable import lockable
from honeybee.typing import float_in_range


@lockable
class Setpoint(_LoadBase):
    """Temperature (thermostat) and humidity (humidistat) setpoints for a thermal zone.

    Properties:
        * name
        * heating_schedule
        * cooling_schedule
        * humidifying_schedule
        * dehumidifying_schedule
        * heating_setpoint
        * cooling_setpoint
        * humidifying_setpoint
        * dehumidifying_setpoint
        * heating_setback
        * cooling_setback
        * humidifying_setback
        * dehumidifying_setback
    """
    __slots__ = ('_heating_schedule', '_cooling_schedule', '_humidifying_schedule',
                 '_dehumidifying_schedule')
    _humidifying_schedule_no_limit = ScheduleRuleset.from_constant_value(
        'HumidNoLimit', 0, _type_lib.humidity)
    _dehumidifying_schedule_no_limit = ScheduleRuleset.from_constant_value(
        'DeHumidNoLimit', 100, _type_lib.humidity)

    def __init__(self, name, heating_schedule, cooling_schedule,
                 humidifying_schedule=None, dehumidifying_schedule=None):
        """Initialize Setpoint.

        Args:
            name: Text string for the Setpoint object. Must be <= 100 characters.
                Can include spaces but special characters will be stripped out.
            heating_schedule: A ScheduleRuleset or ScheduleFixedInterval for the
                heating setpoint.
            cooling_schedule: A ScheduleRuleset or ScheduleFixedInterval for the
                cooling setpoint.
            humidifying_schedule: A ScheduleRuleset or ScheduleFixedInterval for
                the humidification setpoint. If None, no additional humidification
                will be applied by the HVAC system. Default: None.
            dehumidifying_schedule: A ScheduleRuleset or ScheduleFixedInterval for
                the dehumidification setpoint. If None, no additional dehumidification
                will be performed by the HVAC system. Default: None.
        """
        _LoadBase.__init__(self, name)
        # defaults that might be overwritten
        self._dehumidifying_schedule = None

        self.heating_schedule = heating_schedule
        self.cooling_schedule = cooling_schedule
        self.humidifying_schedule = humidifying_schedule
        self.dehumidifying_schedule = dehumidifying_schedule

    @property
    def heating_schedule(self):
        """Get or set a ScheduleRuleset or ScheduleFixedInterval for the heating setpoint.
        """
        return self._heating_schedule

    @heating_schedule.setter
    def heating_schedule(self, value):
        self._check_temperature_schedule_type(value, 'Heating Setpoint')
        value.lock()   # lock editing in case schedule has multiple references
        self._heating_schedule = value

    @property
    def cooling_schedule(self):
        """Get or set a ScheduleRuleset or ScheduleFixedInterval for the cooling setpoint.
        """
        return self._cooling_schedule

    @cooling_schedule.setter
    def cooling_schedule(self, value):
        self._check_temperature_schedule_type(value, 'Cooling Setpoint')
        value.lock()   # lock editing in case schedule has multiple references
        self._cooling_schedule = value

    @property
    def humidifying_schedule(self):
        """Get or set a ScheduleRuleset or ScheduleFixedInterval for humidification.
        """
        return self._humidifying_schedule

    @humidifying_schedule.setter
    def humidifying_schedule(self, value):
        if value is not None:
            self._check_humidity_schedule_type(value, 'Humidifying Setpoint')
            value.lock()   # lock editing in case schedule has multiple references
            self._humidifying_schedule = value
            # if self._dehumidifying_schedule is None:
            #     self._dehumidifying_schedule = self._dehumidifying_schedule_no_limit
        else:
            self._humidifying_schedule = None if self._dehumidifying_schedule is None \
                else self._humidifying_schedule_no_limit

    @property
    def dehumidifying_schedule(self):
        """Get or set a ScheduleRuleset or ScheduleFixedInterval for dehumidification.
        """
        return self._dehumidifying_schedule

    @dehumidifying_schedule.setter
    def dehumidifying_schedule(self, value):
        if value is not None:
            self._check_humidity_schedule_type(value, 'Dehumidifying Setpoint')
            value.lock()   # lock editing in case schedule has multiple references
            self._dehumidifying_schedule = value
            if self._humidifying_schedule is None:
                self._humidifying_schedule = self._humidifying_schedule_no_limit
        else:
            self._dehumidifying_schedule = None if self._humidifying_schedule is None \
                else self._dehumidifying_schedule_no_limit

    @property
    def heating_setpoint(self):
        """Get or set a single constant temperature for the heating setpoint [C].

        Note that, if a varying heating_schedule has been assigned to this object, this
        property will be the highest temperature within the heating_schedule.
        """
        return self._max_schedule_value(self._heating_schedule)

    @heating_setpoint.setter
    def heating_setpoint(self, value):
        value = float_in_range(value, -273.15, input_name='heating setpoint')
        schedule = ScheduleRuleset.from_constant_value(
            '{}_HtgSetp'.format(self.name), value, _type_lib.temperature)
        self.heating_schedule = schedule

    @property
    def cooling_setpoint(self):
        """Get or set a single constant temperature for the cooling setpoint [C].

        Note that, if a varying cooling_schedule has been assigned to this object, this
        property will be the lowest temperature within the cooling_schedule.
        """
        return self._min_schedule_value(self._cooling_schedule)

    @cooling_setpoint.setter
    def cooling_setpoint(self, value):
        value = float_in_range(value, -273.15, input_name='cooling setpoint')
        schedule = ScheduleRuleset.from_constant_value(
            '{}_ClgSetp'.format(self.name), value, _type_lib.temperature)
        self.cooling_schedule = schedule

    @property
    def humidifying_setpoint(self):
        """Get or set a single constant value for the humidifying setpoint [%].

        Note that, if a varying humidifying_schedule has been assigned to this object,
        this property will be the lowest value within the humidifying_schedule.
        """
        return self._max_schedule_value(self._humidifying_schedule) if \
            self._humidifying_schedule is not None else None

    @humidifying_setpoint.setter
    def humidifying_setpoint(self, value):
        if value is not None:
            value = float_in_range(value, 0, 100, 'humidifying setpoint')
            schedule = ScheduleRuleset.from_constant_value(
                '{}_DeHumidSetp'.format(self.name), value, _type_lib.humidity)
            self.humidifying_schedule = schedule
        else:
            self.humidifying_schedule = None

    @property
    def dehumidifying_setpoint(self):
        """Get or set a single constant value for the dehumidifying setpoint [%].

        Note that, if a varying dehumidifying_schedule has been assigned to this object,
        this property will be the lowest value within the dehumidifying_schedule.
        """
        return self._min_schedule_value(self._dehumidifying_schedule) if \
            self._dehumidifying_schedule is not None else None

    @dehumidifying_setpoint.setter
    def dehumidifying_setpoint(self, value):
        if value is not None:
            value = float_in_range(value, 0, 100, 'dehumidifying setpoint')
            schedule = ScheduleRuleset.from_constant_value(
                '{}_DeHumidSetp'.format(self.name), value, _type_lib.humidity)
            self.dehumidifying_schedule = schedule
        else:
            self.dehumidifying_schedule = None

    @property
    def heating_setback(self):
        """Get the lowest temperature in the heating setpoint schedule [C].

        Note that, if a constant heating_setpoint has been assigned to this object,
        this property will the same as the heating_setpoint.
        """
        return self._min_schedule_value(self._heating_schedule)

    @property
    def cooling_setback(self):
        """Get the highest temperature in the cooling setpoint schedule [C].

        Note that, if a constant cooling_setpoint has been assigned to this object,
        this property will the same as the cooling_setpoint.
        """
        return self._max_schedule_value(self._cooling_schedule)

    @property
    def humidifying_setback(self):
        """Get the lowest humidity in the humidifying setpoint schedule [%].

        Note that, if a constant humidifying_setpoint has been assigned to this object,
        this property will the same as the humidifying_setpoint.
        """
        return self._min_schedule_value(self._humidifying_schedule) if \
            self._humidifying_schedule is not None else None

    @property
    def dehumidifying_setback(self):
        """Get the highest humidity in the dehumidifying setpoint schedule [%].

        Note that, if a constant dehumidifying_setpoint has been assigned to this object,
        this property will the same as the dehumidifying_setpoint.
        """
        return self._max_schedule_value(self._dehumidifying_schedule) if \
            self._dehumidifying_schedule is not None else None

    def remove_humidity_setpoints(self):
        """Remove all humidity setpoints from this object."""
        self._humidifying_schedule = None
        self._dehumidifying_schedule = None

    def add_humidity_from_idf(self, idf_string, schedule_dict):
        """Add humidity setpoints to this object from an EnergyPlus IDF text string.

        Args:
            idf_string: A text string fully describing an EnergyPlus
                ZoneControl:Humidistat definition.
            schedule_dict: A dictionary with schedule names as keys and honeybee
                schedule objects as values (either ScheduleRuleset or
                ScheduleFixedInterval). These will be used to assign the schedules to
                the Setpoint object.
        """
        # check the inputs
        ep_strs = parse_idf_string(idf_string, 'ZoneControl:Humidistat,')

        # extract the schedules from the string
        try:
            try:
                humid_sched = schedule_dict[ep_strs[2]] if ep_strs[2] != '' else None
                dehumid_sched = schedule_dict[ep_strs[3]] if ep_strs[3] != '' else None
            except KeyError as e:
                raise ValueError('Failed to find {} in the schedule_dict.'.format(e))
        except IndexError:
            pass  # shorter humidistat definition lacking values

        # assign the properties to this object
        self.humidifying_schedule = humid_sched
        self.dehumidifying_schedule = dehumid_sched

    @classmethod
    def from_idf(cls, idf_string, schedule_dict):
        """Create an Setpoint object from an EnergyPlus IDF text string.

        Note that this method only loads the heating and cooling setpoints from an
        IDF and, to also load humidity setpoints, the add_humidity_from_idf method
        should be used.

        Args:
            idf_string: A text string fully describing an EnergyPlus
                HVACTemplate:Thermostat definition.
            schedule_dict: A dictionary with schedule names as keys and honeybee
                schedule objects as values (either ScheduleRuleset or
                ScheduleFixedInterval). These will be used to assign the schedules to
                the Setpoint object.

        Returns:
            setpoint: A Setpoint object loaded from the idf_string.
        """
        # check the inputs
        ep_strs = parse_idf_string(idf_string, 'HVACTemplate:Thermostat,')

        # remove the zone name from the thermostat
        setp_obj_name = ep_strs[0].split('..')[0]

        # extract the schedules from the string
        try:
            heat_sched = schedule_dict[ep_strs[1]] if ep_strs[1] != '' else None
            cool_sched = schedule_dict[ep_strs[3]] if ep_strs[3] != '' else None
        except KeyError as e:
            raise ValueError('Failed to find {} in the schedule_dict.'.format(e))

        # return the object and the zone name for the object
        setpoint = cls(setp_obj_name, heat_sched, cool_sched)
        return setpoint

    @classmethod
    def from_dict(cls, data):
        """Create a Setpoint object from a dictionary.

        Note that the dictionary must be a non-abridged version for this classmethod
        to work.

        Args:
            data: A Setpoint dictionary in following the format below.

        .. code-block:: json

            {
            "type": 'Setpoint',
            "name": 'Hospital Patient Room Setpoint',
            "heating_schedule": {}, // ScheduleRuleset/ScheduleFixedInterval dictionary
            "cooling_schedule": {}, // ScheduleRuleset/ScheduleFixedInterval dictionary
            "humidifying_schedule": {}, // ScheduleRuleset/ScheduleFixedInterval dictionary
            "dehumidifying_schedule": {} // ScheduleRuleset/ScheduleFixedInterval dictionary
            }
        """
        assert data['type'] == 'Setpoint', \
            'Expected Setpoint dictionary. Got {}.'.format(data['type'])
        heat_sched = cls._get_schedule_from_dict(data['heating_schedule'])
        cool_sched = cls._get_schedule_from_dict(data['cooling_schedule'])
        humid_sched = cls._get_schedule_from_dict(data['humidifying_schedule']) if \
            'humidifying_schedule' in data and \
            data['humidifying_schedule'] is not None else None
        dehumid_sched = cls._get_schedule_from_dict(data['dehumidifying_schedule']) if \
            'dehumidifying_schedule' in data and \
            data['dehumidifying_schedule'] is not None else None
        return cls(data['name'], heat_sched, cool_sched, humid_sched, dehumid_sched)

    @classmethod
    def from_dict_abridged(cls, data, schedule_dict):
        """Create a Setpoint object from an abridged dictionary.

        Args:
            data: A SetpointAbridged dictionary in following the format below.
            schedule_dict: A dictionary with schedule names as keys and honeybee schedule
                objects as values (either ScheduleRuleset or ScheduleFixedInterval).
                These will be used to assign the schedules to the Setpoint object.

        .. code-block:: json

            {
            "type": 'SetpointAbridged',
            "name": 'Hospital Patient Room Setpoint',
            "heating_schedule": "Hospital Pat Room Heating", // Schedule name
            "cooling_schedule": "Hospital Pat Room Cooling", // Schedule name
            "humidifying_schedule": "Hospital Pat Room Humidify", // Schedule name
            "dehumidifying_schedule": "Hospital Pat Room Dehumidify" // Schedule name
            }
        """
        assert data['type'] == 'SetpointAbridged', \
            'Expected SetpointAbridged dictionary. Got {}.'.format(data['type'])
        try:
            heat_sched = schedule_dict[data['heating_schedule']]
            cool_sched = schedule_dict[data['cooling_schedule']]
        except KeyError as e:
            raise ValueError('Failed to find {} in the schedule_dict.'.format(e))

        humid_sched = None
        dehumid_sched = None
        if 'humidifying_schedule' in data and data['humidifying_schedule'] is not None:
            try:
                humid_sched = schedule_dict[data['humidifying_schedule']]
            except KeyError as e:
                raise ValueError('Failed to find {} in the schedule_dict.'.format(e))
        if 'dehumidifying_schedule' in data and data['dehumidifying_schedule'] is not None:
            try:
                dehumid_sched = schedule_dict[data['dehumidifying_schedule']]
            except KeyError as e:
                raise ValueError('Failed to find {} in the schedule_dict.'.format(e))
        return cls(data['name'], heat_sched, cool_sched, humid_sched, dehumid_sched)

    def to_idf(self, zone_name):
        """IDF string representation of Setpoint object's thermostat.

        Note that this method only outputs a string for the HVACTemplate:Thermostat
        object and, to write everything needed to describe the object into an IDF,
        this object's schedules must also be written. If the humidifying or
        dehumidifying schedules are not None, the to_idf_humidistat method should also
        be used to write the humidistat.

        Args:
            zone_name: Text for the zone name that the Setpoint object is assigned to.
        """
        # values = ('{}..{}'.format(self.name, zone_name), self.heating_schedule.name, '',
        #           self.cooling_schedule.name, '')
        # comments = ('name', 'heating setpoint schedule', 'heating setpoint {C}',
        #             'cooling setpoint schedule', 'cooling setpoint {C}')

        schedule_string ="""ScheduleTypeLimits,
          HVACTemplate Any Number;                                 !- Name
        
        Schedule:Compact,
          HVACTemplate-Always 4,                                   !- Name
          HVACTemplate Any Number,                                 !- Schedule Type Limits Name
          Through: 12/31,                                          !- Field 1
          For: AllDays,                                            !- Field 2
          Until: 24:00,                                            !- Field 3
          4;                                                       !- Field 4
        """

        values = ('{}..{}'.format(self.name, zone_name), zone_name,
                    'HVACTemplate-Always 4', 'ThermostatSetpoint:DualSetpoint', 'dual_setp_ctrl')
        comments = ('name', 'Zone or ZoneList Name',
                    'Control Type Schedule Name', 'Control Object Type', 'Control Name')

        values_setpoint = ('dual_setp_ctrl', self.heating_schedule.name, self.cooling_schedule.name )
        comments_setpoint = ('name', 'Heating Setpoint Temperature Schedule Name',
                              'Cooling Setpoint Temperature Schedule Name')


        return "\n\n".join((generate_idf_string('ZoneControl:Thermostat', values, comments),
                           schedule_string,
                           generate_idf_string('ThermostatSetpoint:DualSetpoint', values_setpoint, comments_setpoint)))

    def to_idf_humidistat(self, zone_name):
        """IDF string representation of Setpoint object's humidistat.

        Note that this method only outputs strings for the ZoneControl:Humidistat
        and, to write everything needed to describe the object into an IDF, this
        object's schedules must also be written.

        Also note that this method will return None if no humidity setpoint schedules
        have been assigned.

        Args:
            zone_name: Text for the zone name that the Setpoint object is assigned to.
        """
        if self.humidifying_schedule is not None:
            values = ('{}_{}'.format(self.name, zone_name), zone_name,
                      self.humidifying_schedule.name, self.dehumidifying_schedule.name)
            comments = ('name', 'zone name', 'humidifying setpoint schedule',
                        'dehumidifying setpoint schedule')
            return generate_idf_string('ZoneControl:Humidistat', values, comments)
        return None

    def to_dict(self, abridged=False):
        """Setpoint dictionary representation.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True),
                which only specifies the names of schedules. Default: False.
        """
        base = {'type': 'Setpoint'} if not abridged else {'type': 'SetpointAbridged'}
        base['name'] = self.name
        if not abridged:
            base['heating_schedule'] = self.heating_schedule.to_dict()
            base['cooling_schedule'] = self.cooling_schedule.to_dict()
            if self.humidifying_schedule is not None:
                base['humidifying_schedule'] = self.humidifying_schedule.to_dict()
                base['dehumidifying_schedule'] = self.dehumidifying_schedule.to_dict()
        else:
            base['heating_schedule'] = self.heating_schedule.name
            base['cooling_schedule'] = self.cooling_schedule.name
            if self.humidifying_schedule is not None:
                base['humidifying_schedule'] = self.humidifying_schedule.name
                base['dehumidifying_schedule'] = self.dehumidifying_schedule.name
        return base

    @staticmethod
    def average(name, setpoints, weights=None, timestep_resolution=1):
        """Get an Setpoint object that's an average between other Setpoints.

        Args:
            name: A name for the new averaged Setpoint object.
            setpoints: A list of Setpoint objects that will be averaged
                together to make a new Setpoint.
            weights: An optional list of fractional numbers with the same length
                as the input setpoints. These will be used to weight each of the
                Setpoint objects in the resulting average. Note that, if the sum of
                the weights is less than 1, the unaccounted fraction will be assumed
                to be at the weighted average setpoints of the other objects.
                If None, the objects will be weighted equally. Default: None.
            timestep_resolution: An optional integer for the timestep resolution
                at which the schedules will be averaged. Any schedule details
                smaller than this timestep will be lost in the averaging process.
                Default: 1.
        """
        weights, u_weights = Setpoint._check_avg_weights(setpoints, weights, 'Setpoint')

        # calculate the average thermostat schedules
        heat_sched = Setpoint._average_schedule(
            '{}_HtgSetp Schedule'.format(name),
            [setp.heating_schedule for setp in setpoints], u_weights, timestep_resolution)
        cool_sched = Setpoint._average_schedule(
            '{}_ClgSetp Schedule'.format(name),
            [setp.cooling_schedule for setp in setpoints], u_weights, timestep_resolution)

        # calculate the average humidistat schedules
        humid_scheds = [vent.humidifying_schedule for vent in setpoints]
        if all(val is None for val in humid_scheds):
            humid_sched = None
            dehumid_sched = None
        else:
            dehumid_scheds = [vent.dehumidifying_schedule for vent in setpoints]
            humid_sch_name = '{}_Humid Schedule'.format(name)
            dehumid_sch_name = '{}_Deumid Schedule'.format(name)
            for i, sch in enumerate(humid_scheds):
                if sch is None:
                    humid_scheds[i] = Setpoint._humidifying_schedule_no_limit
                    dehumid_scheds[i] = Setpoint._dehumidifying_schedule_no_limit
            humid_sched = Setpoint._average_schedule(
                humid_sch_name, humid_scheds, u_weights, timestep_resolution)
            dehumid_sched = Setpoint._average_schedule(
                dehumid_sch_name, dehumid_scheds, u_weights, timestep_resolution)

        # return the averaged object
        return Setpoint(name, heat_sched, cool_sched, humid_sched, dehumid_sched)

    def _check_temperature_schedule_type(self, schedule, obj_name=''):
        """Check that the type limit of an input schedule is temperature."""
        assert isinstance(schedule, (ScheduleRuleset, ScheduleFixedInterval, CSVSchedule, NECB)), \
            'Expected ScheduleRuleset or ScheduleFixedInterval or CSVSchedule for {} ' \
            'schedule. Got {}.'.format(obj_name, type(schedule))
        if schedule.schedule_type_limit is not None:
            assert schedule.schedule_type_limit.unit == 'C', '{} schedule ' \
                'should be in Temperature units. Got a schedule of unit_type ' \
                '{}.'.format(obj_name, schedule.schedule_type_limit.unit_type)

    def _check_humidity_schedule_type(self, schedule, obj_name=''):
        """Check that the type limit of an input schedule is percent."""
        assert isinstance(schedule, (ScheduleRuleset, ScheduleFixedInterval, CSVSchedule)), \
            'Expected ScheduleRuleset or ScheduleFixedInterval or CSVSchedule for {} ' \
            'schedule. Got {}.'.format(obj_name, type(schedule))
        if schedule.schedule_type_limit is not None:
            assert schedule.schedule_type_limit.unit == '%', '{} schedule ' \
                'should be in Percent units. Got a schedule of unit_type ' \
                '{}.'.format(obj_name, schedule.schedule_type_limit.unit_type)

    def _min_schedule_value(self, schedule):
        """Extract the minimum value from a schedule."""
        try:  # ScheduleRuleset
            vals = []
            for sch in schedule.day_schedules:
                vals.extend(sch.values)
            return min(vals)
        except AttributeError:  # ScheduleFixedInterval
            return min(schedule.values)

    def _max_schedule_value(self, schedule):
        """Extract the maximum value from a schedule."""
        try:  # ScheduleRuleset
            vals = []
            for sch in schedule.day_schedules:
                vals.extend(sch.values)
            return max(vals)
        except AttributeError:  # ScheduleFixedInterval
            return max(schedule.values)

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.name, hash(self.heating_schedule), hash(self.cooling_schedule),
                hash(self.humidifying_schedule), hash(self.dehumidifying_schedule))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, Setpoint) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __copy__(self):
        return Setpoint(
            self.name, self.heating_schedule, self.cooling_schedule,
            self.humidifying_schedule, self.dehumidifying_schedule)

    def __repr__(self):
        return 'Setpoint:\n name: {}\n heating: {}\n cooling: ' \
            '{}\n humidifying: {}\n dehumidifying: {}'.format(
                self.name, self.heating_setpoint, self.cooling_setpoint,
                self.humidifying_schedule, self.humidifying_schedule)
