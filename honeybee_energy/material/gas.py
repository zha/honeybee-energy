# coding=utf-8
"""Gas materials representing gaps within window constructions.

They can only exist within window constructions bounded by glazing materials
(they cannot be in the interior or exterior layer).
"""
from __future__ import division

from ._base import _EnergyMaterialWindowBase
from ..reader import parse_idf_string
from ..writer import generate_idf_string

from honeybee._lockable import lockable
from honeybee.typing import float_positive, float_in_range, tuple_with_length

import math


@lockable
class _EnergyWindowMaterialGasBase(_EnergyMaterialWindowBase):
    """Base for gas gap layer."""
    GASES = ('Air', 'Argon', 'Krypton', 'Xenon')
    CONDUCTIVITYCURVES = {'Air': (0.002873, 0.0000776, 0.0),
                          'Argon': (0.002285, 0.00005149, 0.0),
                          'Krypton': (0.0009443, 0.00002826, 0.0),
                          'Xenon': (0.0004538, 0.00001723, 0.0)}
    VISCOSITYCURVES = {'Air': (0.00000372, 0.00000005, 0.0),
                       'Argon': (0.00000338, 0.00000006, 0.0),
                       'Krypton': (0.00000221, 0.00000008, 0.0),
                       'Xenon': (0.00000107, 0.00000007, 0.0)}
    SPECIFICHEATCURVES = {'Air': (1002.73699951, 0.012324, 0.0),
                          'Argon': (521.92852783, 0.0, 0.0),
                          'Krypton': (248.09069824, 0.0, 0.0),
                          'Xenon': (158.33970642, 0.0, 0.0)}
    MOLECULARWEIGHTS = {'Air': 28.97, 'Argon': 39.948,
                        'Krypton': 83.8, 'Xenon': 131.3}
    __slots__ = ('_thickness',)

    def __init__(self, name, thickness=0.0125):
        """Initialize gas base material."""
        _EnergyMaterialWindowBase.__init__(self, name)
        self.thickness = thickness

    @property
    def is_gas_material(self):
        """Boolean to note whether the material is a gas gap layer."""
        return True

    @property
    def thickness(self):
        """Get or set the thickess of the gas layer [m]."""
        return self._thickness

    @property
    def molecular_weight(self):
        """Default placeholder gas molecular weight."""
        return self.MOLECULARWEIGHTS['Air']

    @thickness.setter
    def thickness(self, thick):
        self._thickness = float_positive(thick, 'gas gap thickness')

    @property
    def conductivity(self):
        """Conductivity of the gas in the absence of convection at 0C [W/m-K]."""
        return self.conductivity_at_temperature(273.15)

    @property
    def viscosity(self):
        """Viscosity of the gas at 0C [kg/m-s]."""
        return self.viscosity_at_temperature(273.15)

    @property
    def specific_heat(self):
        """Specific heat of the gas at 0C [J/kg-K]."""
        return self.specific_heat_at_temperature(273.15)

    @property
    def density(self):
        """Density of the gas at 0C and sea-level pressure [J/kg-K]."""
        return self.density_at_temperature(273.15)

    @property
    def prandtl(self):
        """Prandtl number of the gas at 0C."""
        return self.prandtl_at_temperature(273.15)

    def density_at_temperature(self, t_kelvin, pressure=101325):
        """Get the density of the gas [kg/m3] at a given temperature and pressure.

        This method uses the ideal gas law to estimate the density.

        Args:
            t_kelvin: The average temperature of the gas cavity in Kelvin.
            pressure: The average pressure of the gas cavity in Pa.
                Default is 101325 Pa for standard pressure at sea level.
        """
        return (pressure * self.molecular_weight * 0.001) / (8.314 * t_kelvin)

    def prandtl_at_temperature(self, t_kelvin):
        """Get the Prandtl number of the gas at a given Kelvin temperature."""
        return self.viscosity_at_temperature(t_kelvin) * \
            self.specific_heat_at_temperature(t_kelvin) / \
            self.conductivity_at_temperature(t_kelvin)

    def grashof(self, delta_t=15, t_kelvin=273.15, pressure=101325):
        """Get Grashof number given the temperature difference across the cavity.

        Args:
            delta_t: The temperature diference across the gas cavity [C]. Default is
                15C, which is consistent with the NFRC standard for double glazed units.
            t_kelvin: The average temperature of the gas cavity in Kelvin.
                Default: 273.15 K (0C).
            pressure: The average pressure of the gas cavity in Pa.
                Default is 101325 Pa for standard pressure at sea level.
        """
        return (9.81 * (self.thickness ** 3) * delta_t *
                self.density_at_temperature(t_kelvin, pressure) ** 2) / \
            (t_kelvin * (self.viscosity_at_temperature(t_kelvin) ** 2))

    def rayleigh(self, delta_t=15, t_kelvin=273.15, pressure=101325):
        """Get Rayleigh number given the temperature difference across the cavity.

        Args:
            delta_t: The temperature diference across the gas cavity [C]. Default is
                15C, which is consistent with the NFRC standard for double glazed units.
            t_kelvin: The average temperature of the gas cavity in Kelvin.
                Default: 273.15 K (0C).
            pressure: The average pressure of the gas cavity in Pa.
                Default is 101325 Pa for standard pressure at sea level.
        """
        _numerator = (self.density_at_temperature(t_kelvin, pressure) ** 2) * \
            (self.thickness ** 3) * 9.81 * self.specific_heat_at_temperature(t_kelvin) \
            * delta_t
        _denominator = t_kelvin * self.viscosity_at_temperature(t_kelvin) * \
            self.conductivity_at_temperature(t_kelvin)
        return _numerator / _denominator

    def nusselt(self, delta_t=15, height=1.0, t_kelvin=273.15, pressure=101325):
        """Get Nusselt number for a vertical cavity given the temp difference and height.

        Args:
            delta_t: The temperature diference across the gas cavity [C]. Default is
                15C, which is consistent with the NFRC standard for double glazed units.
            height: An optional height for the cavity in meters. Default is 1.0,
                which is consistent with NFRC standards.
            t_kelvin: The average temperature of the gas cavity in Kelvin.
                Default: 273.15 K (0C).
            pressure: The average pressure of the gas cavity in Pa.
                Default is 101325 Pa for standard pressure at sea level.
        """
        rayleigh = self.rayleigh(delta_t, t_kelvin, pressure)
        if rayleigh > 50000:
            n_u1 = 0.0673838 * (rayleigh ** (1 / 3))
        elif rayleigh > 10000:
            n_u1 = 0.028154 * (rayleigh ** 0.4134)
        else:
            n_u1 = 1 + 1.7596678e-10 * (rayleigh ** 2.2984755)
        n_u2 = 0.242 * ((rayleigh * (self.thickness / height)) ** 0.272)
        return max(n_u1, n_u2)

    def nusselt_at_angle(self, delta_t=15, height=1.0, angle=90,
                         t_kelvin=273.15, pressure=101325):
        """Get Nusselt number for a cavity at a given angle, temp difference and height.

        Args:
            delta_t: The temperature diference across the gas cavity [C]. Default is
                15C, which is consistent with the NFRC standard for double glazed units.
            height: An optional height for the cavity in meters. Default is 1.0,
                which is consistent with NFRC standards.
            angle: An angle in degrees between 0 and 180.
                0 = A horizontal cavity with downward heat flow through the layer.
                90 = A vertical cavity
                180 = A horizontal cavity with upward heat flow through the layer.
            t_kelvin: The average temperature of the gas cavity in Kelvin.
                Default: 273.15 K (0C).
            pressure: The average pressure of the gas cavity in Pa.
                Default is 101325 Pa for standard pressure at sea level.
        """
        def dot_x(x):
            return (x + abs(x)) / 2

        rayleigh = self.rayleigh(delta_t, t_kelvin, pressure)
        if angle < 60:
            cos_a = math.cos(math.radians(angle))
            sin_a_18 = math.sin(1.8 * math.radians(angle))
            term_1 = dot_x(1 - (1708 / (rayleigh * cos_a)))
            term_2 = 1 - ((1708 * (sin_a_18 ** 1.6)) / (rayleigh * cos_a))
            term_3 = dot_x(((rayleigh * cos_a) / 5830) ** (1 / 3) - 1)
            return 1 + (1.44 * term_1 * term_2) + term_3
        elif angle < 90:
            g = 0.5 / ((1 + ((rayleigh / 3160) ** 20.6)) ** 0.1)
            n_u1 = (1 + (((0.0936 * (rayleigh ** 0.314)) / (1 + g)) ** 7)) ** (1 / 7)
            n_u2 = (0.104 + (0.175 / (self.thickness / height))) * (rayleigh ** 0.283)
            n_u_60 = max(n_u1, n_u2)
            n_u_90 = self.nusselt(delta_t, height, t_kelvin, pressure)
            return (n_u_60 + n_u_90) / 2
        elif angle == 90:
            return self.nusselt(delta_t, height, t_kelvin, pressure)
        else:
            n_u_90 = self.nusselt(delta_t, height, t_kelvin, pressure)
            return 1 + ((n_u_90 - 1) * math.sin(math.radians(angle)))

    def convective_conductance(self, delta_t=15, height=1.0,
                               t_kelvin=273.15, pressure=101325):
        """Get convective conductance of the cavity in a vertical position.

        Args:
            delta_t: The temperature diference across the gas cavity [C]. Default is
                15C, which is consistent with the NFRC standard for double glazed units.
            height: An optional height for the cavity in meters. Default is 1.0,
                which is consistent with NFRC standards.
            t_kelvin: The average temperature of the gas cavity in Kelvin.
                Default: 273.15 K (0C).
            pressure: The average pressure of the gas cavity in Pa.
                Default is 101325 Pa for standard pressure at sea level.
        """
        return self.nusselt(delta_t, height, t_kelvin, pressure) * \
            (self.conductivity_at_temperature(t_kelvin) / self.thickness)

    def convective_conductance_at_angle(self, delta_t=15, height=1.0, angle=90,
                                        t_kelvin=273.15, pressure=101325):
        """Get convective conductance of the cavity in an angle.

        Args:
            delta_t: The temperature diference across the gas cavity [C]. Default is
                15C, which is consistent with the NFRC standard for double glazed units.
            height: An optional height for the cavity in meters. Default is 1.0,
                which is consistent with NFRC standards.
            angle: An angle in degrees between 0 and 180.
                0 = A horizontal cavity with downward heat flow through the layer.
                90 = A vertical cavity
                180 = A horizontal cavity with upward heat flow through the layer.
            t_kelvin: The average temperature of the gas cavity in Kelvin.
                Default: 273.15 K (0C).
            pressure: The average pressure of the gas cavity in Pa.
                Default is 101325 Pa for standard pressure at sea level.
        """
        return self.nusselt_at_angle(delta_t, height, angle, t_kelvin, pressure) * \
            (self.conductivity_at_temperature(t_kelvin) / self.thickness)

    def radiative_conductance(self, emissivity_1=0.84, emissivity_2=0.84,
                              t_kelvin=273.15):
        """Get the radiative conductance of the cavity given emissivities on both sides.

        Args:
            emissivity_1: The emissivity of the surface on one side of the cavity.
                Default is 0.84, which is tyical of clear, uncoated glass.
            emissivity_2: The emissivity of the surface on the other side of the cavity.
                Default is 0.84, which is tyical of clear, uncoated glass.
            t_kelvin: The average temperature of the gas cavity in Kelvin.
                Default: 273.15 K (0C).
        """
        return (4 * 5.6697e-8) * (((1 / emissivity_1) + (1 / emissivity_2) - 1) ** -1) \
            * (t_kelvin ** 3)

    def u_value(self, delta_t=15, emissivity_1=0.84, emissivity_2=0.84, height=1.0,
                t_kelvin=273.15, pressure=101325):
        """Get the U-value of a vertical gas cavity given temp difference and emissivity.

        Args:
            delta_t: The temperature diference across the gas cavity [C]. This
                influences how strong the convection is within the gas gap. Default is
                15C, which is consistent with the NFRC standard for double glazed units.
            emissivity_1: The emissivity of the surface on one side of the cavity.
                Default is 0.84, which is tyical of clear, uncoated glass.
            emissivity_2: The emissivity of the surface on the other side of the cavity.
                Default is 0.84, which is tyical of clear, uncoated glass.
            height: An optional height for the cavity in meters. Default is 1.0,
                which is consistent with NFRC standards.
            t_kelvin: The average temperature of the gas cavity in Kelvin.
                Default: 273.15 K (0C).
            pressure: The average pressure of the gas cavity in Pa.
                Default is 101325 Pa for standard pressure at sea level.
        """
        return self.convective_conductance(delta_t, height, t_kelvin, pressure) + \
            self.radiative_conductance(emissivity_1, emissivity_2, t_kelvin)

    def u_value_at_angle(self, delta_t=15, emissivity_1=0.84, emissivity_2=0.84,
                         height=1.0, angle=90, t_kelvin=273.15, pressure=101325):
        """Get the U-value of a vertical gas cavity given temp difference and emissivity.

        Args:
            delta_t: The temperature diference across the gas cavity [C]. This
                influences how strong the convection is within the gas gap. Default is
                15C, which is consistent with the NFRC standard for double glazed units.
            emissivity_1: The emissivity of the surface on one side of the cavity.
                Default is 0.84, which is tyical of clear, uncoated glass.
            emissivity_2: The emissivity of the surface on the other side of the cavity.
                Default is 0.84, which is tyical of clear, uncoated glass.
            height: An optional height for the cavity in meters. Default is 1.0,
                which is consistent with NFRC standards.
            angle: An angle in degrees between 0 and 180.
                0 = A horizontal cavity with downward heat flow through the layer.
                90 = A vertical cavity
                180 = A horizontal cavity with upward heat flow through the layer.
            t_kelvin: The average temperature of the gas cavity in Kelvin.
                Default: 273.15 K (0C).
            pressure: The average pressure of the gas cavity in Pa.
                Default is 101325 Pa for standard pressure at sea level.
        """
        return self.convective_conductance_at_angle(
            delta_t, height, angle, t_kelvin, pressure) + \
            self.radiative_conductance(emissivity_1, emissivity_2, t_kelvin)


@lockable
class EnergyWindowMaterialGas(_EnergyWindowMaterialGasBase):
    """Gas gap layer.

    Properties:
        name
        thickness
        gas_type
        conductivity
        viscosity
        specific_heat
        density
        prandtl
    """
    __slots__ = ('_gas_type',)

    def __init__(self, name, thickness=0.0125, gas_type='Air'):
        """Initialize gas energy material.

        Args:
            name: Text string for material name. Must be <= 100 characters.
                Can include spaces but special characters will be stripped out.
            thickness: Number for the thickness of the air gap layer [m].
                Default: 0.0125
            gas_type: Text describing the type of gas in the gap.
                Must be one of the following: 'Air', 'Argon', 'Krypton', 'Xenon'.
                Default: 'Air'
        """
        _EnergyWindowMaterialGasBase.__init__(self, name, thickness)
        self.gas_type = gas_type

    @property
    def gas_type(self):
        """Get or set the text describing the gas in the gas gap layer."""
        return self._gas_type

    @gas_type.setter
    def gas_type(self, gas):
        assert gas.title() in self.GASES, 'Invalid input "{}" for gas type.' \
            '\nGas type must be one of the following:{}'.format(gas, self.GASES)
        self._gas_type = gas.title()

    @property
    def molecular_weight(self):
        """Get the gas molecular weight."""
        return self.MOLECULARWEIGHTS[self._gas_type]

    def conductivity_at_temperature(self, t_kelvin):
        """Get the conductivity of the gas [W/m-K] at a given Kelvin temperature."""
        return self._coeff_property(self.CONDUCTIVITYCURVES, t_kelvin)

    def viscosity_at_temperature(self, t_kelvin):
        """Get the viscosity of the gas [kg/m-s] at a given Kelvin temperature."""
        return self._coeff_property(self.VISCOSITYCURVES, t_kelvin)

    def specific_heat_at_temperature(self, t_kelvin):
        """Get the specific heat of the gas [J/kg-K] at a given Kelvin temperature."""
        return self._coeff_property(self.SPECIFICHEATCURVES, t_kelvin)

    @classmethod
    def from_idf(cls, idf_string):
        """Create EnergyWindowMaterialGas from an EnergyPlus text string.

        Args:
            idf_string: A text string fully describing an EnergyPlus material.
        """
        ep_strs = parse_idf_string(idf_string, 'WindowMaterial:Gas,')
        return cls(ep_strs[0], ep_strs[2], ep_strs[1])

    @classmethod
    def from_dict(cls, data):
        """Create a EnergyWindowMaterialGas from a dictionary.

        Args:
            data: {
                "type": 'EnergyWindowMaterialGas',
                "name": 'Argon Gap',
                "thickness": 0.01,
                "gas_type": 'Argon'}
        """
        assert data['type'] == 'EnergyWindowMaterialGas', \
            'Expected EnergyWindowMaterialGas. Got {}.'.format(data['type'])
        if 'thickness' not in data:
            data['thickness'] = 0.0125
        if 'gas_type' not in data:
            data['gas_type'] = 'Air'
        return cls(data['name'], data['thickness'], data['gas_type'])

    def to_idf(self):
        """Get an EnergyPlus string representation of the material."""
        values = (self.name, self.gas_type, self.thickness)
        comments = ('name', 'gas type', 'thickness {m}')
        return generate_idf_string('WindowMaterial:Gas', values, comments)

    def to_dict(self):
        """Energy Material Gas dictionary representation."""
        return {
            'type': 'EnergyWindowMaterialGas',
            'name': self.name,
            'thickness': self.thickness,
            'gas_type': self.gas_type
        }

    def _coeff_property(self, dictionary, t_kelvin):
        """Get a property given a dictionary of coefficients and kelvin temperature."""
        return dictionary[self._gas_type][0] + \
            dictionary[self._gas_type][1] * t_kelvin + \
            dictionary[self._gas_type][2] * t_kelvin ** 2

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.name, self.thickness, self.gas_type)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, EnergyWindowMaterialGas) and \
            self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return self.to_idf()

    def __copy__(self):
        return EnergyWindowMaterialGas(self.name, self.thickness, self.gas_type)


@lockable
class EnergyWindowMaterialGasMixture(_EnergyWindowMaterialGasBase):
    """Gas gap layer with a mixture of gasses.

    Properties:
        name
        thickness
        gas_types
        gas_fractions
        gas_count
        conductivity
        viscosity
        specific_heat
        density
        prandtl
    """
    __slots__ = ('_gas_count', '_gas_types', '_gas_fractions')

    def __init__(self, name, thickness=0.0125,
                 gas_types=('Argon', 'Air'), gas_fractions=(0.9, 0.1)):
        """Initialize gas mixture energy material.

        Args:
            name: Text string for material name. Must be <= 100 characters.
                Can include spaces but special characters will be stripped out.
            thickness: Number for the thickness of the air gap layer [m].
                Default: 0.0125
            gas_types: A list of text describing the types of gas in the gap.
                Text must be one of the following: 'Air', 'Argon', 'Krypton', 'Xenon'.
                Default: ('Argon', 'Air')
            gas_fractions: A list of text describing the volumetric fractions of gas
                types in the mixture.  This list must align with the gas_types
                input list. Default: (0.9, 0.1)
        """
        _EnergyWindowMaterialGasBase.__init__(self, name, thickness)
        try:  # check the number of gases
            self._gas_count = len(gas_types)
        except (TypeError, ValueError):
            raise TypeError(
                'Expected list for gas_types. Got {}.'.format(type(gas_types)))
        assert 2 <= self._gas_count <= 4, 'Number of gases in gas mixture must be ' \
            'between 2 anf 4. Got {}.'.format(self._gas_count)
        self.gas_types = gas_types
        self.gas_fractions = gas_fractions

    @property
    def gas_types(self):
        """Get or set a tuple of text describing the gases in the gas gap layer."""
        return self._gas_types

    @gas_types.setter
    def gas_types(self, g_types):
        self._gas_types = tuple_with_length(
            g_types, self._gas_count, str, 'gas mixture gas_types')
        self._gas_types = tuple(gas.title() for gas in self._gas_types)
        for gas in self._gas_types:
            assert gas in self.GASES, 'Invalid input "{}" for gas type.' \
                '\nGas type must be one of the following:{}'.format(gas, self.GASES)

    @property
    def gas_fractions(self):
        """Get or set a tuple of numbers the fractions of gases in the gas gap layer."""
        return self._gas_fractions

    @gas_fractions.setter
    def gas_fractions(self, g_fracs):
        self._gas_fractions = tuple_with_length(
            g_fracs, self._gas_count, float, 'gas mixture gas_fractions')
        assert sum(self._gas_fractions) == 1, 'Gas fractions must sum to 1. ' \
            'Got {}.'.format(sum(self._gas_fractions))

    @property
    def molecular_weight(self):
        """Get the gas molecular weight."""
        return sum(tuple(self.MOLECULARWEIGHTS[gas] * frac for gas, frac
                         in zip(self._gas_types, self._gas_fractions)))

    @property
    def gas_count(self):
        """An integer indicating the number of gasses in the mixture."""
        return self._gas_count

    def conductivity_at_temperature(self, t_kelvin):
        """Get the conductivity of the gas [W/m-K] at a given Kelvin temperature."""
        return self._weighted_avg_coeff_property(self.CONDUCTIVITYCURVES, t_kelvin)

    def viscosity_at_temperature(self, t_kelvin):
        """Get the viscosity of the gas [kg/m-s] at a given Kelvin temperature."""
        return self._weighted_avg_coeff_property(self.VISCOSITYCURVES, t_kelvin)

    def specific_heat_at_temperature(self, t_kelvin):
        """Get the specific heat of the gas [J/kg-K] at a given Kelvin temperature."""
        return self._weighted_avg_coeff_property(self.SPECIFICHEATCURVES, t_kelvin)

    @classmethod
    def from_idf(cls, idf_string):
        """Create EnergyWindowMaterialGas from an EnergyPlus text string.

        Args:
            idf_string: A text string fully describing an EnergyPlus material.
        """
        prop_types = (str, float, int, str, float, str, float, str, float, str, float)
        ep_strs = parse_idf_string(idf_string, 'WindowMaterial:GasMixture,')
        ep_s = [typ(prop) for typ, prop in zip(prop_types, ep_strs)]
        gas_types = [ep_s[i] for i in range(3, 3 + ep_s[2] * 2, 2)]
        gas_fracs = [ep_s[i] for i in range(4, 4 + ep_s[2] * 2, 2)]
        return cls(ep_s[0], ep_s[1], gas_types, gas_fracs)

    @classmethod
    def from_dict(cls, data):
        """Create a EnergyWindowMaterialGasMixture from a dictionary.

        Args:
            data: {
                "type": 'EnergyWindowMaterialGasMixture',
                "name": 'Argon Mixture Gap',
                "thickness": 0.01,
                'gas_type_fraction': ({'gas_type': 'Air', 'gas_fraction': 0.95},
                                      {'gas_type': 'Argon', 'gas_fraction': 0.05})}
        """
        assert data['type'] == 'EnergyWindowMaterialGasMixture', \
            'Expected EnergyWindowMaterialGasMixture. Got {}.'.format(data['type'])
        optional_keys = ('thickness', 'gas_type_fraction')
        optional_vals = (0.0125, ({'gas_type': 'Air', 'gas_fraction': 0.9},
                                  {'gas_type': 'Argon', 'gas_fraction': 0.1}))
        for key, val in zip(optional_keys, optional_vals):
            if key not in data:
                data[key] = val
        gas_types = tuple(gas['gas_type'] for gas in data['gas_type_fraction'])
        gas_fractions = tuple(gas['gas_fraction'] for gas in data['gas_type_fraction'])
        return cls(data['name'], data['thickness'], gas_types, gas_fractions)

    def to_idf(self):
        """Get an EnergyPlus string representation of the material."""
        values = [self.name, self.thickness, len(self.gas_types)]
        comments = ['name', 'thickness {m}', 'number of gases']
        for i in range(len(self.gas_types)):
            values.append(self.gas_types[i])
            values.append(self.gas_fractions[i])
            comments.append('gas {} type'.format(i))
            comments.append('gas {} fraction'.format(i))
        return generate_idf_string('WindowMaterial:GasMixture', values, comments)

    def to_dict(self):
        """Energy Material Gas Mixture dictionary representation."""
        gas_array = tuple({'gas_type': gas, 'gas_fraction': frac}
                          for gas, frac in zip(self.gas_types, self.gas_fractions))
        return {
            'type': 'EnergyWindowMaterialGasMixture',
            'name': self.name,
            'thickness': self.thickness,
            'gas_type_fraction': gas_array
        }

    def _weighted_avg_coeff_property(self, dictionary, t_kelvin):
        """Get a weighted average property given a dictionary of coefficients."""
        property = []
        for gas in self._gas_types:
            property.append(dictionary[gas][0] + dictionary[gas][1] * t_kelvin +
                            dictionary[gas][2] * t_kelvin ** 2)
        return sum(tuple(pr * frac for pr, frac in zip(property, self._gas_fractions)))

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.name, self.thickness, self.gas_types, self.gas_fractions)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, EnergyWindowMaterialGasMixture) and \
            self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return self.to_idf()

    def __copy__(self):
        return EnergyWindowMaterialGasMixture(
            self.name, self.thickness, self.gas_types, self.gas_fractions)


@lockable
class EnergyWindowMaterialGasCustom(_EnergyWindowMaterialGasBase):
    """Custom gas gap layer.

    Properties:
        name
        thickness
        conductivity_coeff_a
        viscosity_coeff_a
        specific_heat_coeff_a
        conductivity_coeff_b
        viscosity_coeff_b
        specific_heat_coeff_b
        conductivity_coeff_c
        viscosity_coeff_c
        specific_heat_coeff_c
        specific_heat_ratio
        molecular_weight
        conductivity
        viscosity
        specific_heat
        density
        prandtl

    Usage:
        co2_gap = EnergyWindowMaterialGasCustom('CO2', 0.0125, 0.0146, 0.000014, 827.73)
        co2_gap.specific_heat_ratio = 1.4
        co2_gap.molecular_weight = 44
        print(co2_gap)
    """
    __slots__ = ('_conductivity_coeff_a', '_viscosity_coeff_a', '_specific_heat_coeff_a',
                 '_conductivity_coeff_b', '_viscosity_coeff_b', '_specific_heat_coeff_b',
                 '_conductivity_coeff_c', '_viscosity_coeff_c', '_specific_heat_coeff_c',
                 '_specific_heat_ratio', '_molecular_weight')

    def __init__(self, name, thickness,
                 conductivity_coeff_a, viscosity_coeff_a, specific_heat_coeff_a,
                 conductivity_coeff_b=0, viscosity_coeff_b=0, specific_heat_coeff_b=0,
                 conductivity_coeff_c=0, viscosity_coeff_c=0, specific_heat_coeff_c=0,
                 specific_heat_ratio=1.0, molecular_weight=20.0):
        """Initialize custom gas energy material.

        This object allows you to specify specific values for conductivity,
        viscosity and specific heat through the following formula:

            property = A + (B * T) + (C * T ** 2)

            where:
                A, B, and C = regression coefficients for the gas
                T = temperature [K]

        Note that setting properties B and C to 0 will mean the property will be
        equal to the A coefficeint.

        Args:
            name: Text string for material name. Must be <= 100 characters.
                Can include spaces but special characters will be stripped out.
            thickness: Number for the thickness of the air gap layer [m].
                Default: 0.0125
            conductivity_coeff_a: First conductivity coefficient.
                Or condictivity in [W/m-K] if b and c coefficients are 0.
            viscosity_coeff_a: First viscosity coefficient.
                Or viscosity in [kg/m-s] if b and c coefficients are 0.
            specific_heat_coeff_a: First specific heat coefficient.
                Or specific heat in [J/kg-K] if b and c coefficients are 0.
            conductivity_coeff_b: Second conductivity coefficient. Default = 0.
            viscosity_coeff_b: Second viscosity coefficient. Default = 0.
            specific_heat_coeff_b: Second specific heat coefficient. Default = 0.
            conductivity_coeff_c: Thrid conductivity coefficient. Default = 0.
            viscosity_coeff_c: Thrid viscosity coefficient. Default = 0.
            specific_heat_coeff_c: Thrid specific heat coefficient. Default = 0.
            specific_heat_ratio: A number for the the ratio of the specific heat at
                contant pressure, to the specific heat at constant volume.
                Default is 1.0 for Air.
            molecular_weight: Number between 20 and 200 for the mass of 1 mol of
                the substance in grams. Default is 20.0.
        """
        _EnergyWindowMaterialGasBase.__init__(self, name, thickness)
        self.conductivity_coeff_a = conductivity_coeff_a
        self.viscosity_coeff_a = viscosity_coeff_a
        self.specific_heat_coeff_a = specific_heat_coeff_a
        self.conductivity_coeff_b = conductivity_coeff_b
        self.viscosity_coeff_b = viscosity_coeff_b
        self.specific_heat_coeff_b = specific_heat_coeff_b
        self.conductivity_coeff_c = conductivity_coeff_c
        self.viscosity_coeff_c = viscosity_coeff_c
        self.specific_heat_coeff_c = specific_heat_coeff_c
        self.specific_heat_ratio = specific_heat_ratio
        self.molecular_weight = molecular_weight

    @property
    def conductivity_coeff_a(self):
        """Get or set the first conductivity coefficient."""
        return self._conductivity_coeff_a

    @conductivity_coeff_a.setter
    def conductivity_coeff_a(self, coeff):
        self._conductivity_coeff_a = float(coeff)

    @property
    def viscosity_coeff_a(self):
        """Get or set the first viscosity coefficient."""
        return self._viscosity_coeff_a

    @viscosity_coeff_a.setter
    def viscosity_coeff_a(self, coeff):
        self._viscosity_coeff_a = float_positive(coeff)

    @property
    def specific_heat_coeff_a(self):
        """Get or set the first specific heat coefficient."""
        return self._specific_heat_coeff_a

    @specific_heat_coeff_a.setter
    def specific_heat_coeff_a(self, coeff):
        self._specific_heat_coeff_a = float_positive(coeff)

    @property
    def conductivity_coeff_b(self):
        """Get or set the second conductivity coefficient."""
        return self._conductivity_coeff_b

    @conductivity_coeff_b.setter
    def conductivity_coeff_b(self, coeff):
        self._conductivity_coeff_b = float(coeff)

    @property
    def viscosity_coeff_b(self):
        """Get or set the second viscosity coefficient."""
        return self._viscosity_coeff_b

    @viscosity_coeff_b.setter
    def viscosity_coeff_b(self, coeff):
        self._viscosity_coeff_b = float(coeff)

    @property
    def specific_heat_coeff_b(self):
        """Get or set the second specific heat coefficient."""
        return self._specific_heat_coeff_b

    @specific_heat_coeff_b.setter
    def specific_heat_coeff_b(self, coeff):
        self._specific_heat_coeff_b = float(coeff)

    @property
    def conductivity_coeff_c(self):
        """Get or set the third conductivity coefficient."""
        return self._conductivity_coeff_c

    @conductivity_coeff_c.setter
    def conductivity_coeff_c(self, coeff):
        self._conductivity_coeff_c = float(coeff)

    @property
    def viscosity_coeff_c(self):
        """Get or set the third viscosity coefficient."""
        return self._viscosity_coeff_c

    @viscosity_coeff_c.setter
    def viscosity_coeff_c(self, coeff):
        self._viscosity_coeff_c = float(coeff)

    @property
    def specific_heat_coeff_c(self):
        """Get or set the third specific heat coefficient."""
        return self._specific_heat_coeff_c

    @specific_heat_coeff_c.setter
    def specific_heat_coeff_c(self, coeff):
        self._specific_heat_coeff_c = float(coeff)

    @property
    def specific_heat_ratio(self):
        """Get or set the specific heat ratio."""
        return self._specific_heat_ratio

    @specific_heat_ratio.setter
    def specific_heat_ratio(self, number):
        number = float(number)
        assert 1 <= number, 'Input specific_heat_ratio ({}) must be > 1.'.format(number)
        self._specific_heat_ratio = number

    @property
    def molecular_weight(self):
        """Get or set the molecular weight."""
        return self._molecular_weight

    @molecular_weight.setter
    def molecular_weight(self, number):
        self._molecular_weight = float_in_range(
            number, 20.0, 200.0, 'gas material molecular weight')

    def conductivity_at_temperature(self, t_kelvin):
        """Get the conductivity of the gas [W/m-K] at a given Kelvin temperature."""
        return self.conductivity_coeff_a + self.conductivity_coeff_b * t_kelvin + \
            self.conductivity_coeff_c * t_kelvin ** 2

    def viscosity_at_temperature(self, t_kelvin):
        """Get the viscosity of the gas [kg/m-s] at a given Kelvin temperature."""
        return self.viscosity_coeff_a + self.viscosity_coeff_b * t_kelvin + \
            self.viscosity_coeff_c * t_kelvin ** 2

    def specific_heat_at_temperature(self, t_kelvin):
        """Get the specific heat of the gas [J/kg-K] at a given Kelvin temperature."""
        return self.specific_heat_coeff_a + self.specific_heat_coeff_b * t_kelvin + \
            self.specific_heat_coeff_c * t_kelvin ** 2

    @classmethod
    def from_idf(cls, idf_string):
        """Create EnergyWindowMaterialGasCustom from an EnergyPlus text string.

        Args:
            idf_string: A text string fully describing an EnergyPlus material.
        """
        ep_s = parse_idf_string(idf_string, 'WindowMaterial:Gas,')
        assert ep_s[1].title() == 'Custom', 'Exected Custom Gas. Got a specific one.'
        ep_s.pop(1)
        return cls(*ep_s)

    @classmethod
    def from_dict(cls, data):
        """Create a EnergyWindowMaterialGasCustom from a dictionary.

        Args:
            data: {
                "type": 'EnergyWindowMaterialGasCustom',
                "name": 'CO2',
                "thickness": 0.01,
                "conductivity_coeff_a": 0.0146,
                "viscosity_coeff_a": 0.000014,
                "specific_heat_coeff_a": 827.73,
                "specific_heat_ratio": 1.4
                "molecular_weight": 44}
        """
        assert data['type'] == 'EnergyWindowMaterialGasCustom', \
            'Expected EnergyWindowMaterialGasCustom. Got {}.'.format(data['type'])
        optional_keys = ('conductivity_coeff_b', 'viscosity_coeff_b',
                         'specific_heat_coeff_b', 'conductivity_coeff_c',
                         'viscosity_coeff_c', 'specific_heat_coeff_c',
                         'specific_heat_ratio', 'molecular_weight')
        optional_vals = (0, 0, 0, 0, 0, 0, 1.0, 20.0)
        for key, val in zip(optional_keys, optional_vals):
            if key not in data:
                data[key] = val
        return cls(data['name'], data['thickness'], data['conductivity_coeff_a'],
                   data['viscosity_coeff_a'], data['specific_heat_coeff_a'],
                   data['conductivity_coeff_b'], data['viscosity_coeff_b'],
                   data['specific_heat_coeff_b'], data['conductivity_coeff_c'],
                   data['viscosity_coeff_c'], data['specific_heat_coeff_c'],
                   data['specific_heat_ratio'], data['molecular_weight'])

    def to_idf(self):
        """Get an EnergyPlus string representation of the material."""
        values = (self.name, 'Custom', self.thickness, self.conductivity_coeff_a,
                  self.conductivity_coeff_b, self.conductivity_coeff_c,
                  self.viscosity_coeff_a, self.viscosity_coeff_b,
                  self.viscosity_coeff_c, self.specific_heat_coeff_a,
                  self.specific_heat_coeff_b, self.specific_heat_coeff_c,
                  self.molecular_weight, self.specific_heat_ratio)
        comments = ('name', 'gas type', 'thickness', 'conductivity coeff a',
                    'conductivity coeff b', 'conductivity coeff c', 'viscosity coeff a',
                    'viscosity coeff b', 'viscosity coeff c', 'specific heat coeff a',
                    'specific heat coeff b', 'specific heat coeff c',
                    'molecular weight', 'specific heat ratio')
        return generate_idf_string('WindowMaterial:Gas', values, comments)

    def to_dict(self):
        """Energy Material Gas Custom dictionary representation."""
        return {
            'type': 'EnergyWindowMaterialGasCustom',
            'name': self.name,
            'thickness': self.thickness,
            'conductivity_coeff_a': self.conductivity_coeff_a,
            'viscosity_coeff_a': self.viscosity_coeff_a,
            'specific_heat_coeff_a': self.specific_heat_coeff_a,
            'conductivity_coeff_b': self.conductivity_coeff_b,
            'viscosity_coeff_b': self.viscosity_coeff_b,
            'specific_heat_coeff_b': self.specific_heat_coeff_b,
            'conductivity_coeff_c': self.conductivity_coeff_c,
            'viscosity_coeff_c': self.viscosity_coeff_c,
            'specific_heat_coeff_c': self.specific_heat_coeff_c,
            'specific_heat_ratio': self.specific_heat_ratio,
            'molecular_weight': self.molecular_weight
        }

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.name, self.thickness, self.conductivity_coeff_a,
                self.viscosity_coeff_a, self.specific_heat_coeff_a,
                self.conductivity_coeff_b, self.viscosity_coeff_b,
                self.specific_heat_coeff_b, self.conductivity_coeff_c,
                self.viscosity_coeff_c, self.specific_heat_coeff_c,
                self.specific_heat_ratio, self.molecular_weight)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, EnergyWindowMaterialGasCustom) and \
            self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return self.to_idf()

    def __copy__(self):
        return EnergyWindowMaterialGasCustom(
            self.name, self.thickness, self.conductivity_coeff_a,
            self.viscosity_coeff_a, self.specific_heat_coeff_a,
            self.conductivity_coeff_b, self.viscosity_coeff_b,
            self.specific_heat_coeff_b, self.conductivity_coeff_c,
            self.viscosity_coeff_c, self.specific_heat_coeff_c,
            self.specific_heat_ratio, self.molecular_weight)
