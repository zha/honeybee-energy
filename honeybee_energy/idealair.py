# coding=utf-8
"""Simple ideal air system object used to condition zones."""
from __future__ import division

from .reader import parse_idf_string
from .writer import generate_idf_string

from honeybee.typing import valid_string, float_positive, float_in_range
from .schedule.ruleset import ScheduleRuleset
from .schedule.fixedinterval import ScheduleFixedInterval

from .schedule.csvschedule import CSVSchedule

class IdealAirSystem(object):
    """Simple ideal air system object used to condition zones.

    Note that this is the only HVAC system supported by honeybee_energy and, to
    access more advanced HVAC systems, a honeybee_energy extension should be
    installed.

    Properties:
        * heating_limit
        * cooling_limit
        * economizer_type
        * demand_controlled_ventilation
        * sensible_heat_recovery
        * latent_heat_recovery
    """
    __slots__ = ('_heating_limit', '_cooling_limit', '_economizer_type',
                 '_cooling_supply_air_limit', '_heating_supply_air_limit',
                 '_demand_controlled_ventilation', '_sensible_heat_recovery',
                 '_latent_heat_recovery', '_heating_availability_schedule',
                 '_cooling_availability_schedule', '_parent')
    ECONOMIZER_TYPES = ('NoEconomizer', 'DifferentialDryBulb', 'DifferentialEnthalpy')

    def __init__(self, heating_limit='autosize', cooling_limit='autosize',
                 cooling_supply_air_limit = 'autosize',
                 heating_supply_air_limit = 'autosize',
                 economizer_type='DifferentialDryBulb',
                 demand_controlled_ventilation=False,
                 sensible_heat_recovery=0, latent_heat_recovery=0, heating_availability_schedule = None,
                 cooling_availability_schedule= None):
        """Initialize IdealAirSystem.

        Args:
            heating_limit: A number for the maximum heating capacity in Watts. This
                can also be the text 'autosize' to indicate that the capacity should
                be determined during the sizing calculation that happens before
                EnergyPlus runs the simulation over the run period. If None, no limit
                on heating capacity will be applied. Default: 'autosize'.
            cooling_limit: A number for the maximum cooling capacity in Watts. This
                can also be the text 'autosize' to indicate that the capacity should
                be determined during the sizing calculation that happens before
                EnergyPlus runs the simulation over the run period. If None, no limit
                on cooling capacity will be applied. Default: 'autosize'.
            economizer_type: Text to indicate the type of air-side economizer used on
                the ideal air system. Economizers will mix in a greater amount of
                outdoor air to cool the zone (rather than running the cooling system)
                when the zone needs cooling and the outdoor air is cooler than the zone.
                Choose from the options below. Default: DifferentialDryBulb.
                    * NoEconomizer
                    * DifferentialDryBulb
                    * DifferentialEnthalpy
            demand_controlled_ventilation: Boolean to note whether demand controlled
                ventilation should be used on the system, which will vary the amount
                of ventilation air according to the occupancy schedule of the zone.
                Default: False.
            sensible_heat_recovery: A number between 0 and 1 for the effectiveness
                of sensible heat recovery within the system. Default: 0.
            latent_heat_recovery: A number between 0 and 1 for the effectiveness
                of latent heat recovery within the system. Default: 0.
        """
        self._parent = None
        self.heating_limit = heating_limit
        self.cooling_limit = cooling_limit

        self._cooling_supply_air_limit = cooling_supply_air_limit
        self._heating_supply_air_limit = heating_supply_air_limit

        self.economizer_type = economizer_type
        self.demand_controlled_ventilation = demand_controlled_ventilation
        self.sensible_heat_recovery = sensible_heat_recovery
        self.latent_heat_recovery = latent_heat_recovery
        self.heating_availability_schedule = heating_availability_schedule
        self.cooling_availability_schedule = cooling_availability_schedule

    @property
    def heating_limit(self):
        """Get or set a number for the maximum heating capacity in Watts."""
        return self._heating_limit

    @heating_limit.setter
    def heating_limit(self, value):
        if value is None:
            self._heating_limit = None
        elif isinstance(value, str) and value.lower() == 'autosize':
            self._heating_limit = 'autosize'
        else:
            self._heating_limit = float_positive(value, 'ideal air heating limit')

    @property
    def cooling_limit(self):
        """Get or set a number for the maximum cooling capacity in Watts."""
        return self._cooling_limit

    @cooling_limit.setter
    def cooling_limit(self, value):
        if value is None:
            # assert self.economizer_type == 'NoEconomizer', 'Ideal air system ' \
            #     'economizer_type must be "NoEconomizer" to have no cooling limit.'
            self._cooling_limit = None
        elif isinstance(value, str) and value.lower() == 'autosize':
            self._cooling_limit = 'autosize'
        else:
            self._cooling_limit = float_positive(value, 'ideal air cooling limit')

    @property
    def economizer_type(self):
        """Get or set text to indicate the type of air-side economizer.

        Choose from the options below:
            * NoEconomizer
            * DifferentialDryBulb
            * DifferentialEnthalpy
        """
        return self._economizer_type

    @economizer_type.setter
    def economizer_type(self, value):
        clean_input = valid_string(value).lower()
        for key in self.ECONOMIZER_TYPES:
            if key.lower() == clean_input:
                value = key
                break
        else:
            raise ValueError(
                'economizer_type {} is not recognized.\nChoose from the '
                'following:\n{}'.format(value, self.ECONOMIZER_TYPES))
        self._economizer_type = value

    @property
    def demand_controlled_ventilation(self):
        """Get or set a boolean for whether demand controlled ventilation is present."""
        return self._demand_controlled_ventilation

    @demand_controlled_ventilation.setter
    def demand_controlled_ventilation(self, value):
        self._demand_controlled_ventilation = bool(value)

    @property
    def sensible_heat_recovery(self):
        """Get or set a number for the effectiveness of sensible heat recovery."""
        return self._sensible_heat_recovery

    @sensible_heat_recovery.setter
    def sensible_heat_recovery(self, value):
        self._sensible_heat_recovery = float_in_range(
            value, 0.0, 1.0, 'ideal air sensible heat recovery')

    @property
    def latent_heat_recovery(self):
        """Get or set a number for the effectiveness of latent heat recovery."""
        return self._latent_heat_recovery

    @latent_heat_recovery.setter
    def latent_heat_recovery(self, value):
        self._latent_heat_recovery = float_in_range(
            value, 0.0, 1.0, 'ideal air latent heat recovery')

    @property
    def heating_availability_schedule(self):
        """Get or set a ScheduleRuleset or ScheduleFixedInterval for the occupancy."""
        return self._heating_availability_schedule

    @heating_availability_schedule.setter
    def heating_availability_schedule(self, value):
        assert isinstance(value, (ScheduleRuleset, ScheduleFixedInterval, CSVSchedule)), \
            'Expected ScheduleRuleset or ScheduleFixedInterval. ' \
            ' Got {}.'.format(type(value))
        value.lock()   # lock editing in case schedule has multiple references
        self._heating_availability_schedule = value

    @property
    def cooling_availability_schedule(self):
        """Get or set a ScheduleRuleset or ScheduleFixedInterval for the occupancy."""
        return self._cooling_availability_schedule

    @cooling_availability_schedule.setter
    def cooling_availability_schedule(self, value):
        assert isinstance(value, (ScheduleRuleset, ScheduleFixedInterval, CSVSchedule)), \
            'Expected ScheduleRuleset or ScheduleFixedInterval. ' \
            ' Got {}.'.format(type(value))
        value.lock()  # lock editing in case schedule has multiple references
        self._cooling_availability_schedule = value

    @classmethod
    def from_idf(cls, idf_string):
        """Create an IdealAirSystem object from an EnergyPlus IDF text string.

        Args:
            idf_string: A text string fully describing an EnergyPlus
                HVACTemplate:Zone:IdealLoadsAirSystem definition.

        Returns:
            ideal_air_system: An IdealAirSystem object loaded from the idf_string.
            zone_name: The name of the zone to which the IdealAirSystem object should
                be assigned.
        """
        # check the inputs
        ep_strs = parse_idf_string(idf_string, 'HVACTemplate:Zone:IdealLoadsAirSystem,')

        # extract the properties from the string
        heat_limit = 'autosize'
        cool_limit = 'autosize'
        econ = 'DifferentialDryBulb'
        dcv = False
        sensible = 0
        latent = 0
        try:
            if ep_strs[7].lower() == 'limitcapacity' or \
                    ep_strs[7].lower() == 'limitflowrateandcapacity':
                heat_limit = ep_strs[9] if ep_strs[9] != '' else 'autosize'
            else:
                heat_limit = None
            if ep_strs[10].lower() == 'limitcapacity' or \
                    ep_strs[10].lower() == 'limitflowrateandcapacity':
                heat_limit = ep_strs[12] if ep_strs[12] != '' else 'autosize'
            else:
                heat_limit = None
            if ep_strs[25].lower() == 'occupancyschedule':
                dcv = True
            if ep_strs[26].lower() != 'differentialdrybulb':
                econ = ep_strs[26]
            if ep_strs[27].lower() == 'sensible':
                sensible = ep_strs[28] if ep_strs[28] != '' else 0.7
            elif ep_strs[27].lower() == 'enthalpy':
                sensible = ep_strs[28] if ep_strs[28] != '' else 0.7
                latent = ep_strs[29] if ep_strs[29] != '' else 0.65
        except IndexError:
            pass  # shorter Ideal air loads definition

        # return the object and the zone name for the object
        ideal_air_system = cls(heat_limit, cool_limit, econ, dcv, sensible, latent)
        zone_name = ep_strs[0]
        return ideal_air_system, zone_name

    @classmethod
    def from_dict(cls, data):
        """Create a IdealAirSystem object from a dictionary.

        Args:
            data: A IdealAirSystem dictionary in following the format below.

        .. code-block:: json

            {
            "type": "IdealAirSystem",
            "heating_limit": 'autosize',  // Max size of the heating system in Watts
            "cooling_limit": 'autosize',  // Max size of the cooling system in Watts
            "economizer_type": 'DifferentialDryBulb',  // Economizer type
            "demand_controlled_ventilation": True,  // Demand controlled ventilation
            "sensible_heat_recovery": 0.75,  // Sensible heat recovery effectiveness
            "latent_heat_recovery": 0.7  // Latent heat recovery effectiveness
            }
        """
        assert data['type'] == 'IdealAirSystem', \
            'Expected IdealAirSystem dictionary. Got {}.'.format(data['type'])
        heat_limit = data['heating_limit'] if 'heating_limit' in data else 'autosize'
        cool_limit = data['cooling_limit'] if 'cooling_limit' in data else 'autosize'
        econ = data['economizer_type'] if 'economizer_type' in data and \
            data['economizer_type'] is not None else 'DifferentialDryBulb'
        dcv = data['demand_controlled_ventilation'] if \
            'demand_controlled_ventilation' in data else False
        sensible = data['sensible_heat_recovery'] if \
            'sensible_heat_recovery' in data else 0
        latent = data['latent_heat_recovery'] if \
            'latent_heat_recovery' in data else 0
        return cls(heat_limit, cool_limit, econ, dcv, sensible, latent)

    def to_idf(self):
        """IDF string representation of IdealAirSystem object.

        Note that this ideal air system should be assigned to a honeybee Room that
        has a Setpoint object for this method to work correctly since all setpoints
        and ventilation requirements are pulled from this assigned Room.
        """
        # check that a setpoint object is assigned
        assert self._parent is not None and \
            self._parent.properties.energy.setpoint is not None, \
            'IdealAirSystem must be assigned to a Room ' \
            'with a setpoint object to use IdealAirSystem.to_idf.'

        # extract all of the fields from this object and its parent
        if self.heating_limit is not None:
            h_lim_type = 'LimitFlowRateAndCapacity' # Modified to limit both flowrate and capacity
            heat_limit = self.heating_limit
        else:
            h_lim_type = 'NoLimit'
            heat_limit = ''
        if self.cooling_limit is not None:
            c_lim_type = 'LimitFlowRateAndCapacity'
            air_limit = self._cooling_supply_air_limit
            cool_limit = self.cooling_limit
        else:
            c_lim_type = 'NoLimit'
            air_limit = cool_limit = ''

        # if self._parent.properties.energy.setpoint.humidifying_setpoint == 'none':
        #     humid_type = 'None'
        #     humid_setpt = ''
        if self._parent.properties.energy.setpoint.humidifying_setpoint is not None:
            humid_type = 'Humidistat'
            humid_setpt = self._parent.properties.energy.setpoint.humidifying_setpoint
        else:
            humid_type = 'None'
            humid_setpt = ''

            # humid_type = 'Humidistat'
            # humid_setpt = '30'
        if self._parent.properties.energy.setpoint.dehumidifying_setpoint is not None:
            dehumid_type = 'Humidistat'
            dehumid_setpt = self._parent.properties.energy.setpoint.dehumidifying_setpoint
        else:
            dehumid_type = 'None'
            dehumid_setpt = ''
        if self._parent.properties.energy.ventilation is not None:
            oa_method = 'DetailedSpecification'
            oa_name = '{}..{}'.format(self._parent.properties.energy.ventilation.name,
                                      self._parent.name)
        else:
            oa_method = 'None'
            oa_name = ''
        dcv = 'OccupancySchedule' if self.demand_controlled_ventilation else 'None'
        if self.sensible_heat_recovery == 0 and self.latent_heat_recovery == 0:
            heat_recovery = 'None'
        elif self.latent_heat_recovery != 0:
            heat_recovery = 'Enthalpy'
        else:
            heat_recovery = 'Sensible'

        if self.heating_availability_schedule is not None:
            heating_avail_sch = self.heating_availability_schedule.name
        if self.cooling_availability_schedule is not None:
            cooling_avail_sch = self.cooling_availability_schedule.name


        # return a full IDF string
        thermostat = '{}..{}'.format(self._parent.properties.energy.setpoint.name,
                                     self._parent.name)
        # values = (self._parent.name, thermostat,
        #           '', 40, 13, '', '', h_lim_type, air_limit, heat_limit, c_lim_type,
        #           air_limit, cool_limit, heating_avail_sch, cooling_avail_sch,
        #           dehumid_type, 0.7, dehumid_setpt, humid_type, humid_setpt, oa_method,
        #           '', '', '', oa_name, dcv,   self.economizer_type, heat_recovery,
        #           self.sensible_heat_recovery, self.latent_heat_recovery)
        # comments = (
        #     'zone name', 'template thermostat name', 'availability schedule',
        #     'heating supply air temp {C}', 'cooling supply air temp {C}',
        #     'max heating supply air hr {kg-H2O/kg-air}',
        #     'min cooling supply air hr {kg-H2O/kg-air}',
        #     'heating limit', 'max heating fow rate {m3/s}', 'max sensible heat capacity',
        #     'cooling limit', 'max cooling fow rate {m3/s}', 'max total cooling capacity',
        #     'heating availability schedule', 'cooling availability schedule',
        #     'dehumidification type', 'cooling shr', 'dehumidification setpoint',
        #     'humidification type', 'humidification setpoint', 'outdoor air method',
        #     'oa per person', 'oa per area', 'oa per zone', 'outdoor air object name',
        #     'demand controlled vent type', 'economizer type', 'heat recovery type',
        #     'sensible heat recovery effectiveness', 'latent heat recovery effectiveness')
        values = ('zone ideal air load', "",
                  'supply air node', '',
                  '',
                  40, 13,
                  0.0156, 0.0077,
                  h_lim_type, air_limit, heat_limit,
                  c_lim_type, air_limit, cool_limit,
                  heating_avail_sch, cooling_avail_sch,
                  dehumid_type, 0.7, humid_setpt,
                  oa_name, 'Outdoor Air Inlet',
                  dcv, self.economizer_type,
                  heat_recovery,
                  self.sensible_heat_recovery, self.latent_heat_recovery
        )

        comments = ('name', 'availability schedule',
                    'supply air node name', 'Exhaust Air Node Name',
                    'system inlet air node',
                    'heating supply air temp {C}', 'cooling supply air temp {C}',
                    'max heating supply air hr {kg-H2O/kg-air}',
                    'min cooling supply air hr {kg-H2O/kg-air}',
                    'Heating limit', 'max heating fow rate {m3/s}', 'max sensible heat capacity',
                    'cooling limit', 'max cooling fow rate {m3/s}', 'max total cooling capacity',
                    'heating availability schedule', 'cooling availability schedule',
                    'dehumidification type', 'cooling shr', 'humidification type',
                    'outdoor air object name', 'outdoor air inlet name',
                    'demand controlled vent type', 'economizer type',
                    'heat recovery type',
                    'sensible heat recovery effectiveness', 'latent heat recovery effectiveness'
                    )

        connection_value = (self._parent.name, 'eqp list',
                            'supply air node',
                            '',
                            'zone air node',
                            'return air node'
                            )

        connection_comments = ('Zone Name', 'Zone Conditioning Equipment List Name',
                               'Zone Air Inlet Node or NodeList Name',
                               'Zone Air Exhaust Node or NodeList Name',
                               'Zone Air Node Name',
                               'Zone Return Air Node Name')

        eqplist_value = ('eqp list', 'SequentialLoad',
                         'ZoneHVAC:IdealLoadsAirSystem',
                         'zone ideal air load', 1, 1
                         )

        eqplist_comment = ('name', 'Load Distribution Scheme',
                           'Zone Equipment Object Type',
                           'Zone Equipment Name',
                           'Zone Equipment Cooling Sequence',
                           'Zone Equipment Heating or No-Load Sequence')


        return "\n\n".join((generate_idf_string(
                           'ZoneHVAC:IdealLoadsAirSystem', values, comments),
                           generate_idf_string('ZoneHVAC:EquipmentConnections', connection_value, connection_comments),
                          generate_idf_string('ZoneHVAC:EquipmentList', eqplist_value, eqplist_comment),
        ))

    def to_dict(self):
        """IdealAirSystem dictionary representation."""
        base = {'type': 'IdealAirSystem'}
        if self.heating_limit != 'autosize':
            base['heating_limit'] = self.heating_limit
        if self.cooling_limit != 'autosize':
            base['cooling_limit'] = self.cooling_limit
        if self.economizer_type != 'DifferentialDryBulb':
            base['economizer_type'] = self.economizer_type
        if self.demand_controlled_ventilation:
            base['demand_controlled_ventilation'] = True
        if self.sensible_heat_recovery != 0:
            base['sensible_heat_recovery'] = self.sensible_heat_recovery
        if self.latent_heat_recovery != 0:
            base['latent_heat_recovery'] = self.latent_heat_recovery
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __copy__(self):
        return IdealAirSystem(
            self.heating_limit, self.cooling_limit, self.economizer_type,
            self.demand_controlled_ventilation, self.sensible_heat_recovery,
            self.latent_heat_recovery)

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.heating_limit, self.cooling_limit, self.economizer_type,
                self.demand_controlled_ventilation, self.sensible_heat_recovery,
                self.latent_heat_recovery)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, IdealAirSystem) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return 'IdealAirSystem:\n heat limit: {}\n cool limit: {}' \
            '\n economizer: {}\n dcv: {}\n sensible hr: {}\n latent hr: {}'.format(
                self.heating_limit, self.cooling_limit, self.economizer_type,
                self.demand_controlled_ventilation, self.sensible_heat_recovery,
                self.latent_heat_recovery)
