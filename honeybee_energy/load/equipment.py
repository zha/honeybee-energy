# coding=utf-8
"""Complete definition of equipment in a simulation, including schedule and load."""
from __future__ import division

from ._base import _LoadBase
from ..schedule.ruleset import ScheduleRuleset
from ..schedule.csvschedule import CSVSchedule
from ..schedule.necb import NECB

from ..schedule.fixedinterval import ScheduleFixedInterval
from ..reader import parse_idf_string
from ..writer import generate_idf_string

from honeybee._lockable import lockable
from honeybee.typing import float_in_range, float_positive


@lockable
class _EquipmentBase(_LoadBase):
    """A complete definition of equipment, including schedules and load.

    Properties:
        * name
        * watts_per_area
        * schedule
        * radiant_fraction
        * latent_fraction
        * lost_fraction
        * convected_fraction
    """
    __slots__ = ('_watts_per_area', '_schedule', '_radiant_fraction',
                 '_latent_fraction', '_lost_fraction')
    _idf_comments = ('name', 'zone name', 'schedule name', 'equipment level method',
                     'equipment power level {W}', 'equipment per floor area {W/m2}',
                     'equipment per person {W/ppl}', 'latent fraction',
                     'radiant fration', 'lost fraction')

    def __init__(self, name, watts_per_area, schedule, radiant_fraction=0,
                 latent_fraction=0, lost_fraction=0):
        """Initialize Equipment.

        Args:
            name: Text string for the equipment definition name. Must be <= 100 characters.
                Can include spaces but special characters will be stripped out.
            watts_per_area: A numerical value for the equipment power density in
                Watts per square meter of floor area.
            schedule: A ScheduleRuleset or ScheduleFixedInterval for the use of equipment
                over the course of the year. The type of this schedule should be
                Fractional and the fractional values will get multiplied by the
                watts_per_area to yield a complete equipment profile.
            radiant_fraction: A number between 0 and 1 for the fraction of the total
                equipment load given off as long wave radiant heat. Default: 0.
            latent_fraction: A number between 0 and 1 for the fraction of the total
                equipment load that is latent (as opposed to sensible). Default: 0.
            lost_fraction: A number between 0 and 1 for the fraction of the total
                equipment load that is lost outside of the zone and the HVAC system.
                Typically, this is used to represent heat that is exhausted directly
                out of a zone (as you would for a stove). Default: 0.
        """
        _LoadBase.__init__(self, name)
        self._latent_fraction = 0  # starting value so that check runs correctly
        self._lost_fraction = 0  # starting value so that check runs correctly

        self.watts_per_area = watts_per_area
        self.schedule = schedule
        self.radiant_fraction = radiant_fraction
        self.latent_fraction = latent_fraction
        self.lost_fraction = lost_fraction

    @property
    def watts_per_area(self):
        """Get or set the equipment power density in Watts/square meter of floor area."""
        return self._watts_per_area

    @watts_per_area.setter
    def watts_per_area(self, value):
        self._watts_per_area = float_positive(value, 'equipment watts per area')

    @property
    def schedule(self):
        """Get or set a ScheduleRuleset or ScheduleFixedInterval for equipment usage."""
        return self._schedule

    @schedule.setter
    def schedule(self, value):
        assert isinstance(value, (ScheduleRuleset, ScheduleFixedInterval, CSVSchedule, NECB)), \
            'Expected ScheduleRuleset or ScheduleFixedInterval for equipment ' \
            'schedule. Got {}.'.format(type(value))
        self._check_fractional_schedule_type(value, 'Equipment')
        value.lock()   # lock editing in case schedule has multiple references
        self._schedule = value

    @property
    def radiant_fraction(self):
        """Get or set the fraction of equipment heat given off as long wave radiation."""
        return self._radiant_fraction

    @radiant_fraction.setter
    def radiant_fraction(self, value):
        self._radiant_fraction = float_in_range(
            value, 0.0, 1.0, 'equipment radiant fraction')
        self._check_fractions()

    @property
    def latent_fraction(self):
        """Get or set the fraction of equipment heat that is latent."""
        return self._latent_fraction

    @latent_fraction.setter
    def latent_fraction(self, value):
        self._latent_fraction = float_in_range(
            value, 0.0, 1.0, 'equipment latent fraction')
        self._check_fractions()

    @property
    def lost_fraction(self):
        """Get or set the fraction of equipment heat that is lost out of the zone."""
        return self._lost_fraction

    @lost_fraction.setter
    def lost_fraction(self, value):
        self._lost_fraction = float_in_range(
            value, 0.0, 1.0, 'equipment lost fraction')
        self._check_fractions()

    @property
    def convected_fraction(self):
        """Get the fraction of equipment heat that convects to the zone air."""
        return 1 - sum((self._radiant_fraction, self._latent_fraction,
                        self._lost_fraction))

    def _check_fractions(self):
        tot = (self._radiant_fraction, self._latent_fraction, self._lost_fraction)
        assert sum(tot) <= 1, 'Sum of equipment radiant_fraction, latent_fraction' \
            ' and lost_fraction ({}) is greater than 1.'.format(sum(tot))

    def _get_idf_values(self, zone_name):
        """Get the properties of this object ordered as they are in an IDF."""
        return ('{}..{}'.format(self.name, zone_name), zone_name, self.schedule.name,
                'Watts/Area', '', self.watts_per_area, '', self.latent_fraction,
                self.radiant_fraction, self.lost_fraction)

    def _add_dict_keys(self, base, abridged):
        """Add keys to a base dictionary."""
        base['name'] = self.name
        base['watts_per_area'] = self.watts_per_area
        base['radiant_fraction'] = self.radiant_fraction
        base['latent_fraction'] = self.latent_fraction
        base['lost_fraction'] = self.lost_fraction
        base['schedule'] = self.schedule.to_dict() if not \
            abridged else self.schedule.name
        return base

    @staticmethod
    def _extract_ep_properties(ep_strs, schedule_dict):
        """Extract relevant EnergyPlus properties from a list of strings."""
        # check the inputs
        assert ep_strs[3].lower() == 'watts/area', 'Equipment must use ' \
            'Watts/Area method to be loaded from IDF to honeybee.'
        # extract the properties from the string
        rad_fract = 0
        lat_fract = 0
        lost_fract = 0
        try:
            rad_fract = ep_strs[8] if ep_strs[8] != '' else 0
            lat_fract = ep_strs[7] if ep_strs[7] != '' else 0
            lost_fract = ep_strs[9] if ep_strs[9] != '' else 0
        except IndexError:
            pass  # shorter equipment definitipn lacking fractions
        # extract the schedules from the string
        try:
            sched = schedule_dict[ep_strs[2]]
        except KeyError as e:
            raise ValueError('Failed to find {} in the schedule_dict.'.format(e))
        return sched, rad_fract, lat_fract, lost_fract

    @staticmethod
    def _extract_dict_props(data, expected_type):
        """Extract relevant properties from an equipment dictionary."""
        assert data['type'] == expected_type, \
            'Expected {} dictionary. Got {}.'.format(expected_type, data['type'])
        sched = _EquipmentBase._get_schedule_from_dict(data['schedule'])
        rad_fract, lat_fract, lost_fract = _EquipmentBase._optional_dict_keys(data)
        return sched, rad_fract, lat_fract, lost_fract

    @staticmethod
    def _extract_abridged_dict_props(data, expected_type, schedule_dict):
        """Extract relevant properties from an equipment dictionary."""
        assert data['type'] == expected_type, \
            'Expected {} dictionary. Got {}.'.format(expected_type, data['type'])
        try:
            sched = schedule_dict[data['schedule']]
        except KeyError as e:
            raise ValueError('Failed to find {} in the schedule_dict.'.format(e))
        rad_fract, lat_fract, lost_fract = _EquipmentBase._optional_dict_keys(data)
        return sched, rad_fract, lat_fract, lost_fract

    @staticmethod
    def _optional_dict_keys(data):
        """Get the optional keys from an Equipment dictionary."""
        rad_fract = data['radiant_fraction'] if 'radiant_fraction' in data else 0
        lat_fract = data['latent_fraction'] if 'latent_fraction' in data else 0
        lost_fract = data['lost_fraction'] if 'lost_fraction' in data else 0
        return rad_fract, lat_fract, lost_fract

    @staticmethod
    def _average_properties(name, equipments, weights, timestep_resolution):
        """Get average properties across several equipment objects."""
        weights, u_weights = \
            _EquipmentBase._check_avg_weights(equipments, weights, 'Equipment')

        # calculate the average values
        pd = sum([eq.watts_per_area * w for eq, w in zip(equipments, weights)])
        rad_fract = sum([eq.radiant_fraction * w for eq, w in zip(equipments, u_weights)])
        lat_fract = sum([eq.latent_fraction * w for eq, w in zip(equipments, u_weights)])
        lost_fract = sum([eq.lost_fraction * w for eq, w in zip(equipments, u_weights)])

        # calculate the average schedules
        sched = _EquipmentBase._average_schedule(
            '{} Schedule'.format(name), [eq.schedule for eq in equipments],
            u_weights, timestep_resolution)

        return pd, sched, rad_fract, lat_fract, lost_fract

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.name, self.watts_per_area, hash(self.schedule),
                self.radiant_fraction, self.latent_fraction, self.lost_fraction)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, _EquipmentBase) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __copy__(self):
        return _EquipmentBase(
            self.name, self.watts_per_area, self.schedule,
            self.radiant_fraction, self.latent_fraction, self.lost_fraction)

    def __repr__(self):
        return 'Equipment:\n name: {}\n watts per area: {}\n schedule: ' \
            '{}'.format(self.name, self.watts_per_area, self.schedule.name)


@lockable
class ElectricEquipment(_EquipmentBase):
    """A complete definition of electric equipment, including schedules and load.

    Properties:
        * name
        * watts_per_area
        * schedule
        * radiant_fraction
        * latent_fraction
        * lost_fraction
        * convected_fraction
    """
    __slots__ = ()

    def __init__(self, name, watts_per_area, schedule, radiant_fraction=0,
                 latent_fraction=0, lost_fraction=0):
        """Initialize Electric Equipment.

        Args:
            name: Text string for the equipment definition name. Must be <= 100 characters.
                Can include spaces but special characters will be stripped out.
            watts_per_area: A numerical value for the equipment power density in
                Watts per square meter of floor area.
            schedule: A ScheduleRuleset or ScheduleFixedInterval for the use of equipment
                over the course of the year. The type of this schedule should be
                Fractional and the fractional values will get multiplied by the
                watts_per_area to yield a complete equipment profile.
            radiant_fraction: A number between 0 and 1 for the fraction of the total
                equipment load given off as long wave radiant heat. Default: 0.
            latent_fraction: A number between 0 and 1 for the fraction of the total
                equipment load that is latent (as opposed to sensible). Default: 0.
            lost_fraction: A number between 0 and 1 for the fraction of the total
                equipment load that is lost outside of the zone and the HVAC system.
                Typically, this is used to represent heat that is exhausted directly
                out of a zone (as you would for a stove). Default: 0.
        """
        _EquipmentBase.__init__(self, name, watts_per_area, schedule,
                                radiant_fraction, latent_fraction, lost_fraction)

    @classmethod
    def from_idf(cls, idf_string, schedule_dict):
        """Create an ElectricEquipment object from an EnergyPlus IDF text string.

        Note that the ElectricEquipment idf_string must use the 'watts per zone floor
        area' method in order to be successfully imported.

        Args:
            idf_string: A text string fully describing an EnergyPlus
                ElectricEquipment definition.
            schedule_dict: A dictionary with schedule names as keys and honeybee
                schedule objects as values (either ScheduleRuleset or
                ScheduleFixedInterval). These will be used to assign the schedules to
                the ElectricEquipment object.

        Returns:
            equipment: An ElectricEquipment object loaded from the idf_string.
            zone_name: The name of the zone to which the ElectricEquipment object
                should be assigned.
        """
        # check the inputs
        ep_strs = parse_idf_string(idf_string, 'ElectricEquipment,')
        # get the relevant properties
        sched, rad_f, lat_f, lost_f = cls._extract_ep_properties(ep_strs, schedule_dict)
        # return the equipment object and the zone name for the equip object
        obj_name = ep_strs[0].split('..')[0]
        zone_name = ep_strs[1]
        equipment = cls(obj_name, ep_strs[5], sched, rad_f, lat_f, lost_f)
        return equipment, zone_name

    @classmethod
    def from_dict(cls, data):
        """Create a ElectricEquipment object from a dictionary.

        Note that the dictionary must be a non-abridged version for this classmethod
        to work.

        Args:
            data: A ElectricEquipment dictionary in following the format below.

        .. code-block:: json

            {
            "type": 'ElectricEquipment',
            "name": 'Open Office Equipment',
            "watts_per_area": 5, // equipment watts per square meter of floor area
            "schedule": {}, // ScheduleRuleset/ScheduleFixedInterval dictionary
            "radiant_fraction": 0.3, // fraction of heat that is long wave radiant
            "latent_fraction": 0, // fraction of heat that is latent
            "lost_fraction": 0 // fraction of heat that is lost
            }
        """
        sched, rad_f, lat_f, lost_f = cls._extract_dict_props(data, 'ElectricEquipment')
        return cls(data['name'], data['watts_per_area'], sched, rad_f, lat_f, lost_f)

    @classmethod
    def from_dict_abridged(cls, data, schedule_dict):
        """Create a ElectricEquipment object from an abridged dictionary.

        Args:
            data: A ElectricEquipmentAbridged dictionary in following the format below.
            schedule_dict: A dictionary with schedule names as keys and honeybee schedule
                objects as values (either ScheduleRuleset or ScheduleFixedInterval).
                These will be used to assign the schedules to the equipment object.

        .. code-block:: json

            {
            "type": 'ElectricEquipmentAbridged',
            "name": 'Open Office Equipment',
            "watts_per_area": 5, // equipment watts per square meter of floor area
            "schedule": "Office Equipment Schedule", // Schedule name
            "radiant_fraction": 0.3, // fraction of heat that is long wave radiant
            "latent_fraction": 0, // fraction of heat that is latent
            "lost_fraction": 0 // fraction of heat that is lost
            }
        """
        sched, rad_f, lat_f, lost_f = cls._extract_abridged_dict_props(
            data, 'ElectricEquipmentAbridged', schedule_dict)
        return cls(data['name'], data['watts_per_area'], sched, rad_f, lat_f, lost_f)

    def to_idf(self, zone_name):
        """IDF string representation of ElectricEquipment object.

        Note that this method only outputs a single string for the ElectricEquipment
        object and, to write everything needed to describe the object into an IDF,
        this object's schedule must also be written.

        Args:
            zone_name: Text for the zone name that the ElectricEquipment object
                is assigned to.
        """
        return generate_idf_string('ElectricEquipment', self._get_idf_values(zone_name),
                                   self._idf_comments)

    def to_dict(self, abridged=False):
        """ElectricEquipment dictionary representation.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True),
                which only specifies the names of schedules. Default: False.
        """
        base = {'type': 'ElectricEquipment'} if not abridged else \
            {'type': 'ElectricEquipmentAbridged'}
        return self._add_dict_keys(base, abridged)

    @staticmethod
    def average(name, equipments, weights=None, timestep_resolution=1):
        """Get an ElectricEquipment object that's an average between other objects.

        Args:
            name: A name for the new averaged ElectricEquipment object.
            equipments: A list of ElectricEquipment objects that will be averaged
                together to make a new ElectricEquipment.
            weights: An optional list of fractional numbers with the same length
                as the input equipments. These will be used to weight each of the
                equipment objects in the resulting average. Note that these weights
                can sum to less than 1 in which case the average watts_per_area will
                assume 0 for the unaccounted fraction of the weights.
                If None, the objects will be weighted equally. Default: None.
            timestep_resolution: An optional integer for the timestep resolution
                at which the schedules will be averaged. Any schedule details
                smaller than this timestep will be lost in the averaging process.
                Default: 1.
        """
        pd, sched, rad_f, lat_f, lost_f = ElectricEquipment._average_properties(
            name, equipments, weights, timestep_resolution)
        return ElectricEquipment(name, pd, sched, rad_f, lat_f, lost_f)

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.name, self.watts_per_area, hash(self.schedule),
                self.radiant_fraction, self.latent_fraction, self.lost_fraction)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, ElectricEquipment) and self.__key() == other.__key()

    def __copy__(self):
        return ElectricEquipment(
            self.name, self.watts_per_area, self.schedule,
            self.radiant_fraction, self.latent_fraction, self.lost_fraction)

    def __repr__(self):
        return 'ElectricEquipment:\n name: {}\n watts per area: {}\n schedule: ' \
            '{}'.format(self.name, self.watts_per_area, self.schedule.name)


@lockable
class GasEquipment(_EquipmentBase):
    """A complete definition of gas equipment, including schedules and load.

    Properties:
        * name
        * watts_per_area
        * schedule
        * radiant_fraction
        * latent_fraction
        * lost_fraction
        * convected_fraction
    """
    __slots__ = ()

    def __init__(self, name, watts_per_area, schedule, radiant_fraction=0,
                 latent_fraction=0, lost_fraction=0):
        """Initialize Gas Equipment.

        Args:
            name: Text string for the equipment definition name. Must be <= 100 characters.
                Can include spaces but special characters will be stripped out.
            watts_per_area: A numerical value for the equipment power density in
                Watts per square meter of floor area.
            schedule: A ScheduleRuleset or ScheduleFixedInterval for the use of equipment
                over the course of the year. The type of this schedule should be
                Fractional and the fractional values will get multiplied by the
                watts_per_area to yield a complete equipment profile.
            radiant_fraction: A number between 0 and 1 for the fraction of the total
                equipment load given off as long wave radiant heat. Default: 0.
            latent_fraction: A number between 0 and 1 for the fraction of the total
                equipment load that is latent (as opposed to sensible). Default: 0.
            lost_fraction: A number between 0 and 1 for the fraction of the total
                equipment load that is lost outside of the zone and the HVAC system.
                Typically, this is used to represent heat that is exhausted directly
                out of a zone (as you would for a stove). Default: 0.
        """
        _EquipmentBase.__init__(self, name, watts_per_area, schedule,
                                radiant_fraction, latent_fraction, lost_fraction)

    @classmethod
    def from_idf(cls, idf_string, schedule_dict):
        """Create an GasEquipment object from an EnergyPlus IDF text string.

        Note that the GasEquipment idf_string must use the 'watts per zone floor
        area' method in order to be successfully imported.

        Args:
            idf_string: A text string fully describing an EnergyPlus
                GasEquipment definition.
            schedule_dict: A dictionary with schedule names as keys and honeybee
                schedule objects as values (either ScheduleRuleset or
                ScheduleFixedInterval). These will be used to assign the schedules to
                the GasEquipment object.

        Returns:
            equipment: An GasEquipment object loaded from the idf_string.
            zone_name: The name of the zone to which the GasEquipment object
                should be assigned.
        """
        # check the inputs
        ep_strs = parse_idf_string(idf_string, 'GasEquipment,')
        # get the relevant properties
        sched, rad_f, lat_f, lost_f = cls._extract_ep_properties(ep_strs, schedule_dict)
        # return the equipment object and the zone name for the equip object
        obj_name = ep_strs[0].split('..')[0]
        zone_name = ep_strs[1]
        equipment = cls(obj_name, ep_strs[5], sched, rad_f, lat_f, lost_f)
        return equipment, zone_name

    @classmethod
    def from_dict(cls, data):
        """Create a GasEquipment object from a dictionary.

        Note that the dictionary must be a non-abridged version for this classmethod
        to work.

        Args:
            data: A GasEquipment dictionary in following the format below.

        .. code-block:: json

            {
            "type": 'GasEquipment',
            "name": 'Kitchen Equipment',
            "watts_per_area": 20, // equipment watts per square meter of floor area
            "schedule": {}, // ScheduleRuleset/ScheduleFixedInterval dictionary
            "radiant_fraction": 0.3, // fraction of heat that is long wave radiant
            "latent_fraction": 0.2, // fraction of heat that is latent
            "lost_fraction": 0 // fraction of heat that is lost
            }
        """
        sched, rad_f, lat_f, lost_f = cls._extract_dict_props(data, 'GasEquipment')
        return cls(data['name'], data['watts_per_area'], sched, rad_f, lat_f, lost_f)

    @classmethod
    def from_dict_abridged(cls, data, schedule_dict):
        """Create a GasEquipment object from an abridged dictionary.

        Args:
            data: A GasEquipmentAbridged dictionary in following the format below.
            schedule_dict: A dictionary with schedule names as keys and honeybee schedule
                objects as values (either ScheduleRuleset or ScheduleFixedInterval).
                These will be used to assign the schedules to the equipment object.

        .. code-block:: json

            {
            "type": 'GasEquipmentAbridged',
            "name": 'Kitchen Equipment',
            "watts_per_area": 20, // equipment watts per square meter of floor area
            "schedule": "Kitchen Equipment Schedule", // Schedule name
            "radiant_fraction": 0.3, // fraction of heat that is long wave radiant
            "latent_fraction": 0, // fraction of heat that is latent
            "lost_fraction": 0 // fraction of heat that is lost
            }
        """
        sched, rad_f, lat_f, lost_f = cls._extract_abridged_dict_props(
            data, 'GasEquipmentAbridged', schedule_dict)
        return cls(data['name'], data['watts_per_area'], sched, rad_f, lat_f, lost_f)

    def to_idf(self, zone_name):
        """IDF string representation of GasEquipment object.

        Note that this method only outputs a single string for the GasEquipment
        object and, to write everything needed to describe the object into an IDF,
        this object's schedule must also be written.

        Args:
            zone_name: Text for the zone name that the GasEquipment object
                is assigned to.
        """
        return generate_idf_string('GasEquipment', self._get_idf_values(zone_name),
                                   self._idf_comments)

    def to_dict(self, abridged=False):
        """GasEquipment dictionary representation.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True),
                which only specifies the names of schedules. Default: False.
        """
        base = {'type': 'GasEquipment'} if not abridged else \
            {'type': 'GasEquipmentAbridged'}
        return self._add_dict_keys(base, abridged)

    @staticmethod
    def average(name, equipments, weights=None, timestep_resolution=1):
        """Get a GasEquipment object that's an average between other objects.

        Args:
            name: A name for the new averaged GasEquipment object.
            equipments: A list of GasEquipment objects that will be averaged
                together to make a new GasEquipment.
            weights: An optional list of fractional numbers with the same length
                as the input equipments. These will be used to weight each of the
                equipment objects in the resulting average. Note that these weights
                can sum to less than 1 in which case the average watts_per_area will
                assume 0 for the unaccounted fraction of the weights.
                If None, the objects will be weighted equally. Default: None.
            timestep_resolution: An optional integer for the timestep resolution
                at which the schedules will be averaged. Any schedule details
                smaller than this timestep will be lost in the averaging process.
                Default: 1.
        """
        pd, sched, rad_f, lat_f, lost_f = GasEquipment._average_properties(
            name, equipments, weights, timestep_resolution)
        return GasEquipment(name, pd, sched, rad_f, lat_f, lost_f)

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.name, self.watts_per_area, hash(self.schedule),
                self.radiant_fraction, self.latent_fraction, self.lost_fraction)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, GasEquipment) and self.__key() == other.__key()

    def __copy__(self):
        return GasEquipment(
            self.name, self.watts_per_area, self.schedule,
            self.radiant_fraction, self.latent_fraction, self.lost_fraction)

    def __repr__(self):
        return 'GasEquipment:\n name: {}\n watts per area: {}\n schedule: ' \
            '{}'.format(self.name, self.watts_per_area, self.schedule.name)
