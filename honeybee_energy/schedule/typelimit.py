# coding=utf-8
"""Schedule type definition."""
from __future__ import division

from ..reader import parse_idf_string
from ..writer import generate_idf_string

from honeybee.typing import valid_ep_string, valid_string, float_in_range
from ladybug.datatype import fraction, temperature, temperaturedelta, power, \
    angle, speed, distance, uvalue

import os
import re


class ScheduleTypeLimit(object):
    """Energy schedule type definition.

    Schedule types exist for the sole purpose of validating schedule values against
    upper/lower limits and assigning a data type and units to the schedule values.

    Properties:
        name
        lower_limit
        upper_limit
        numeric_type
        unit_type
        data_type
        unit
    """
    _default_lb_unit_type = {
        'Dimensionless': (fraction.Fraction(), 'fraction'),
        'Temperature': (temperature.Temperature(), 'C'),
        'DeltaTemperature': (temperaturedelta.TemperatureDelta(), 'C'),
        'PrecipitationRate': [distance.Distance(), 'm'],
        'Angle': [angle.Angle(), 'degrees'],
        'ConvectionCoefficient': [uvalue.ConvectionCoefficient(), 'W/m2-K'],
        'ActivityLevel': [power.ActivityLevel(), 'W'],
        'Velocity': [speed.Speed(), 'm/s'],
        'Capacity': [power.Power(), 'W'],
        'Power': [power.Power(), 'W'],
        'Availability': [fraction.Fraction(), 'fraction'],
        'Percent': [fraction.Fraction(), '%'],
        'Control': [fraction.Fraction(), 'fraction'],
        'Mode': [fraction.Fraction(), 'fraction']}

    UNIT_TYPES = tuple(_default_lb_unit_type.keys())
    NUMERIC_TYPES = ('Continuous', 'Discrete')

    def __init__(self, name, lower_limit=None, upper_limit=None,
                 numeric_type='Continuous', unit_type='Dimensionless'):
        """Initialize ScheduleTypeLimit.

        Args:
            name: Text string for schedule type name. Must be <= 100 characters.
                Can include spaces but special characters will be stripped out.
            lower_limit: An optional number for the lower limit for values in the
                schedule. If None, there will be no lower limit.
            upper_limit: An optional number for the upper limit for values in the
                schedule. If None, there will be no upper limit.
            numeric_type: Either one of two strings: 'Continuous' or 'Discrete'.
                The latter means that only integers are accepted as schedule values.
                Default: 'Continuous'.
            unit_type: Text for an EnergyPlus unit type, which will be used
                to assign units to the values in the schedule.  Note that this field
                is not used in the actual calculations of EnergyPlus.
                Default: 'Dimensionless'. Choose from the following options:
                'Dimensionless', 'Temperature', 'DeltaTemperature', 'PrecipitationRate',
                'Angle', 'ConvectionCoefficient', 'ActivityLevel', 'Velocity',
                'Capacity', 'Power', 'Availability', 'Percent', 'Control', 'Mode'
        """
        # process the name and limits
        self._name = valid_ep_string(name, 'schedule type name')
        self._lower_limit = float_in_range(lower_limit) if lower_limit is not \
            None else None
        self._upper_limit = float_in_range(upper_limit) if upper_limit is not \
            None else None
        if self._lower_limit is not None and self._upper_limit is not None:
            assert self._lower_limit <= self._upper_limit, 'ScheduleTypeLimit ' \
                'lower_limit must be less than upper_limit. {} > {}.'.format(
                    self._lower_limit, self._upper_limit)

        # process the numeric type
        self._numeric_type = numeric_type.capitalize() or 'Continuous'
        assert self._numeric_type in self.NUMERIC_TYPES, '"{}" is not an acceptable ' \
            'numeric type.  Choose from the following:\n{}'.format(
                numeric_type, self.NUMERIC_TYPES)

        # process the unit type and assign the ladybug data type and unit
        if unit_type is None:
            self._data_type, self._unit = self._default_lb_unit_type['Dimensionless']
            self._unit_type = 'Dimensionless'
        else:
            clean_input = valid_string(unit_type).lower()
            for key in self.UNIT_TYPES:
                if key.lower() == clean_input:
                    unit_type = key
                    break
            else:
                raise ValueError(
                    'unit_type {} is not recognized.\nChoose from the '
                    'following:\n{}'.format(unit_type, self.UNIT_TYPES))
            self._data_type, self._unit = self._default_lb_unit_type[unit_type]
            self._unit_type = unit_type

    @property
    def name(self):
        """Get the text string for schedule type name."""
        return self._name

    @property
    def lower_limit(self):
        """Get the lower limit of the schedule type."""
        return self._lower_limit

    @property
    def upper_limit(self):
        """Get the upper limit of the schedule type."""
        return self._upper_limit

    @property
    def numeric_type(self):
        """Text noting whether schedule values are 'Continuous' or 'Discrete'."""
        return self._numeric_type

    @property
    def unit_type(self):
        """Get the text string describing the energyplus unit type."""
        return self._unit_type

    @property
    def data_type(self):
        """Get the Ladybug DataType object corresponding to the energyplus unit type.

        This object can be used for creating Ladybug DataCollections, performing unit
        conversions of schedule values, etc.
        """
        return self._data_type

    @property
    def unit(self):
        """Get the string describing the units of the schedule values (ie. 'C', 'W')."""
        return self._unit

    @classmethod
    def from_idf(cls, idf_string):
        """Create a ScheduleTypeLimit from an IDF string of ScheduleTypeLimits.

        Args:
            idf_string: A text string describing EnergyPlus ScheduleTypeLimits.
        """
        ep_strs = parse_idf_string(idf_string, 'ScheduleTypeLimits,')
        ep_fields = [prop if prop != '' else None for prop in ep_strs]
        return cls(*ep_fields)

    @classmethod
    def from_dict(cls, data):
        """Create a ScheduleTypeLimit from a dictionary.

        Args:
            data: ScheduleTypeLimit dictionary following the format below.

        .. code-block:: json

            {
            "type": 'ScheduleTypeLimit',
            "name": 'Fractional',
            "lower_limit": 0,
            "upper_limit": 1,
            "numeric_type": False,
            "unit_type": "Dimensionless"
            }
        """
        assert data['type'] == 'ScheduleTypeLimit', \
            'Expected ScheduleTypeLimit dictionary. Got {}.'.format(data['type'])
        lower_limit = data['lower_limit'] if 'lower_limit' in data else None
        upper_limit = data['upper_limit'] if 'upper_limit' in data else None
        numeric_type = data['numeric_type'] if 'numeric_type' in data else 'Continuous'
        unit_type = data['unit_type'] if 'unit_type' in data else 'Dimensionless'
        return cls(data['name'], lower_limit, upper_limit, numeric_type, unit_type)

    def to_idf(self):
        """IDF string for the ScheduleTypeLimits of this object."""
        values = [self.name, self.lower_limit, self.upper_limit,
                  self.numeric_type, self.unit_type]
        if values[1] is None:
            values[1] = ''
        if values[2] is None:
            values[2] = ''
        comments = ('name', 'lower limit value', 'upper limit value',
                    'numeric type', 'unit type')
        return generate_idf_string('ScheduleTypeLimits', values, comments)

    def to_dict(self):
        """Shade construction dictionary representation."""
        base = {'type': 'ScheduleTypeLimit'}
        base['name'] = self.name
        base['lower_limit'] = self.lower_limit
        base['upper_limit'] = self.upper_limit
        base['numeric_type'] = self.numeric_type
        base['unit_type'] = self.unit_type
        return base

    @staticmethod
    def extract_all_from_idf_file(idf_file):
        """Extract all ScheduleTypeLimit objects from an EnergyPlus IDF file.

        Args:
            idf_file: A path to an IDF file containing objects for ScheduleTypeLimits.

        Returns:
            schedule_type_limits: A list of all ScheduleTypeLimits objects in the
                IDF file as honeybee_energy ScheduleTypeLimit objects.
        """
        # check the file
        assert os.path.isfile(idf_file), 'Cannot find an idf file at {}'.format(idf_file)
        with open(idf_file, 'r') as ep_file:
            file_contents = ep_file.read()
        # extract all of the ScheduleTypeLimit objects
        type_pattern = re.compile(r"(?i)(ScheduleTypeLimits,[\s\S]*?;)")
        type_idf_strings = type_pattern.findall(file_contents)
        schedule_type_limits = []
        for type_str in type_idf_strings:
            type_str = type_str.strip()
            schedule_type_limits.append(ScheduleTypeLimit.from_idf(type_str))
        return schedule_type_limits

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def __copy__(self):
        return ScheduleTypeLimit(self.name, self._lower_limit, self._upper_limit,
                                 self._numeric_type, self._unit_type)

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.name, self._lower_limit, self._upper_limit,
                self._numeric_type, self._unit_type)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, ScheduleTypeLimit) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        return self.to_idf()
