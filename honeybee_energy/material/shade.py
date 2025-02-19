# coding=utf-8
"""Shade materials representing shades, blinds, or screens in a window construction.

They can exist in only one of three possible locations in a window construction:
1) On the innermost material layer.
2) On the outermost material layer.
3) In between two glazing materials. In the case of window constructions with
    multiple glazing surfaces, the shade mateerial must be between the two
    inner glass layers.

Note that shade materials should never be bounded by gas gap layers in honeybee-energy.
"""
from __future__ import division

from ._base import _EnergyMaterialWindowBase
from .gas import EnergyWindowMaterialGas
from ..reader import parse_idf_string
from ..writer import generate_idf_string

from honeybee._lockable import lockable
from honeybee.typing import float_in_range, float_positive


@lockable
class _EnergyWindowMaterialShadeBase(_EnergyMaterialWindowBase):
    """Base for all shade material layers."""
    __slots__ = ('_infrared_transmittance', '_emissivity', '_distance_to_glass',
                 '_top_opening_multiplier', '_bottom_opening_multiplier',
                 '_left_opening_multiplier', '_right_opening_multiplier')

    def __init__(self, name, infrared_transmittance=0, emissivity=0.9,
                 distance_to_glass=0.05, opening_multiplier=0.5):
        """Initialize base shade energy material."""
        _EnergyMaterialWindowBase.__init__(self, name)
        self.infrared_transmittance = infrared_transmittance
        self.emissivity = emissivity
        self.distance_to_glass = distance_to_glass
        self.set_all_opening_multipliers(opening_multiplier)

    @property
    def is_shade_material(self):
        """Boolean to note whether the material is a shade layer."""
        return True

    @property
    def infrared_transmittance(self):
        """Get or set the infrared transmittance of the shade."""
        return self._infrared_transmittance

    @infrared_transmittance.setter
    def infrared_transmittance(self, ir_tr):
        self._infrared_transmittance = float_in_range(
            ir_tr, 0.0, 1.0, 'shade material infrared transmittance')

    @property
    def emissivity(self):
        """Get or set the hemispherical emissivity of the shade."""
        return self._emissivity

    @emissivity.setter
    def emissivity(self, ir_e):
        ir_e = float_in_range(ir_e, 0.0, 1.0, 'shade material emissivity')
        self._emissivity = ir_e

    @property
    def distance_to_glass(self):
        """Get or set the shade distance to the glass [m]."""
        return self._distance_to_glass

    @distance_to_glass.setter
    def distance_to_glass(self, dist):
        self._distance_to_glass = float_in_range(
            dist, 0.001, 1.0, 'shade material distance to glass')

    @property
    def top_opening_multiplier(self):
        """Get or set the top opening multiplier."""
        return self._top_opening_multiplier

    @top_opening_multiplier.setter
    def top_opening_multiplier(self, multiplier):
        self._top_opening_multiplier = float_in_range(
            multiplier, 0.0, 1.0, 'shade material opening multiplier')

    @property
    def bottom_opening_multiplier(self):
        """Get or set the bottom opening multiplier."""
        return self._bottom_opening_multiplier

    @bottom_opening_multiplier.setter
    def bottom_opening_multiplier(self, multiplier):
        self._bottom_opening_multiplier = float_in_range(
            multiplier, 0.0, 1.0, 'shade material opening multiplier')

    @property
    def left_opening_multiplier(self):
        """Get or set the left opening multiplier."""
        return self._left_opening_multiplier

    @left_opening_multiplier.setter
    def left_opening_multiplier(self, multiplier):
        self._left_opening_multiplier = float_in_range(
            multiplier, 0.0, 1.0, 'shade material opening multiplier')

    @property
    def right_opening_multiplier(self):
        """Get or set the right opening multiplier."""
        return self._right_opening_multiplier

    @right_opening_multiplier.setter
    def right_opening_multiplier(self, multiplier):
        self._right_opening_multiplier = float_in_range(
            multiplier, 0.0, 1.0, 'shade material opening multiplier')

    def set_all_opening_multipliers(self, multiplier):
        """Set all opening multipliers to the same value at once."""
        self.top_opening_multiplier = multiplier
        self.bottom_opening_multiplier = multiplier
        self.left_opening_multiplier = multiplier
        self.right_opening_multiplier = multiplier

    def r_value_exterior(self, delta_t=7.5, emissivity=0.84, height=1.0, angle=90,
                         t_kelvin=273.15, pressure=101325):
        """Get an estimate of the R-value of the shade + air gap when it is exterior.

        Args:
            delta_t: The temperature diference across the air gap [C]. This
                influences how strong the convection is within the air gap. Default is
                7.5C, which is consistent with the NFRC standard for double glazed units.
            emissivity: The emissivity of the glazing surface adjacent to the shade.
                Default is 0.84, which is tyical of clear, uncoated glass.
            height: An optional height for the cavity between the shade and the
                glass in meters. Default is 1.0.
            angle: An angle in degrees between 0 and 180.
                0 = A horizontal surface with downward heat flow through the layer.
                90 = A vertical surface
                180 = A horizontal surface with upward heat flow through the layer.
            t_kelvin: The average temperature of the gas cavity in Kelvin.
                Default: 273.15 K (0C).
            pressure: The average air pressure in Pa. Default is 101325 Pa for sea level.
        """
        # TODO: Account for air permeability and side openings in gap u-value.
        # https://bigladdersoftware.com/epx/docs/9-0/engineering-reference/
        # window-heat-balance-calculation.html#solving-for-gap-airflow-and-temperature
        _gap = EnergyWindowMaterialGas(
            name='Generic Shade Gap', thickness=self.distance_to_glass, gas_type='Air')
        try:
            _shade_e = self.emissivity_back
        except AttributeError:
            _shade_e = self.emissivity
        _r_gap = 1 / _gap.u_value_at_angle(delta_t, _shade_e, emissivity,
                                           height, angle, t_kelvin, pressure)
        return self.r_value + _r_gap

    def r_value_interior(self, delta_t=7.5, emissivity=0.84, height=1.0, angle=90,
                         t_kelvin=273.15, pressure=101325):
        """Get an estimate of the R-value of the shade + air gap when it is interior.

        Args:
            delta_t: The temperature diference across the air gap [C]. This
                influences how strong the convection is within the air gap. Default is
                7.5C, which is consistent with the NFRC standard for double glazed units.
            emissivity: The emissivity of the glazing surface adjacent to the shade.
                Default is 0.84, which is tyical of clear, uncoated glass.
            height: An optional height for the cavity between the shade and the
                glass in meters. Default is 1.0.
            angle: An angle in degrees between 0 and 180.
                0 = A horizontal surface with downward heat flow through the layer.
                90 = A vertical surface
                180 = A horizontal surface with upward heat flow through the layer.
            t_kelvin: The average temperature of the gas cavity in Kelvin.
                Default: 273.15 K (0C).
            pressure: The average air pressure in Pa. Default is 101325 Pa for sea level.
        """
        # TODO: Account for air permeability and side openings in gap u-value.
        # https://bigladdersoftware.com/epx/docs/9-0/engineering-reference/
        # window-heat-balance-calculation.html#solving-for-gap-airflow-and-temperature
        _gap = EnergyWindowMaterialGas(
            name='Generic Shade Gap', thickness=self.distance_to_glass, gas_type='Air')
        _shade_e = self.emissivity
        _r_gap = 1 / _gap.u_value_at_angle(delta_t, _shade_e, emissivity,
                                           height, angle, t_kelvin, pressure)
        return self.r_value + _r_gap

    def r_value_between(self, delta_t=7.5, emissivity_1=0.84, emissivity_2=0.84,
                        height=1.0, angle=90, t_kelvin=273.15, pressure=101325):
        """Get an estimate of the R-value of the shade + air gap when it is interior.

        Args:
            delta_t: The temperature diference across the air gap [C]. This
                influences how strong the convection is within the air gap. Default is
                7.5C, which is consistent with the NFRC standard for double glazed units.
            emissivity_1: The emissivity of the glazing surface on one side of the shade.
                Default is 0.84, which is tyical of clear, uncoated glass.
            emissivity_2: The emissivity of the glazing surface on the other side of
                the shade. Default is 0.84, which is tyical of clear, uncoated glass.
            height: An optional height for the cavity between the shade and the
                glass in meters. Default is 1.0.
            angle: An angle in degrees between 0 and 180.
                0 = A horizontal surface with downward heat flow through the layer.
                90 = A vertical surface
                180 = A horizontal surface with upward heat flow through the layer.
            t_kelvin: The average temperature of the gas cavity in Kelvin.
                Default: 273.15 K (0C).
            pressure: The average air pressure in Pa. Default is 101325 Pa for sea level.
        """
        _gap = EnergyWindowMaterialGas(
            name='Generic Shade Gap', thickness=self.distance_to_glass, gas_type='Air')
        _shade_e = self.emissivity
        _r_gap_1 = 1 / _gap.u_value_at_angle(delta_t, _shade_e, emissivity_1,
                                             height, angle, t_kelvin, pressure)
        _r_gap_2 = 1 / _gap.u_value_at_angle(delta_t, _shade_e, emissivity_2,
                                             height, angle, t_kelvin, pressure)
        return self.r_value + _r_gap_1 + _r_gap_2


@lockable
class EnergyWindowMaterialShade(_EnergyWindowMaterialShadeBase):
    """A material for a shade layer in a window construction.

    Reflectance and emissivity properties are assumed to be the same on both sides of
    the shade. Shades are considered to be perfect diffusers.

    Properties:
        name
        thickness
        solar_transmittance
        solar_reflectance
        visible_transmittance
        visible_reflectance
        infrared_transmittance
        emissivity
        conductivity
        distance_to_glass
        top_opening_multiplier
        bottom_opening_multiplier
        left_opening_multiplier
        right_opening_multiplier
        airflow_permeability
        resistivity
        u_value
        r_value
    """
    __slots__ = ('_thickness', '_solar_transmittance', '_solar_reflectance',
                 '_visible_transmittance', '_visible_reflectance',
                 '_conductivity', '_airflow_permeability')

    def __init__(self, name, thickness=0.005, solar_transmittance=0.4,
                 solar_reflectance=0.5,
                 visible_transmittance=0.4, visible_reflectance=0.4,
                 infrared_transmittance=0, emissivity=0.9,
                 conductivity=0.9, distance_to_glass=0.05,
                 opening_multiplier=0.5, airflow_permeability=0.0):
        """Initialize energy window material shade.

        Args:
            name: Text string for material name. Must be <= 100 characters.
                Can include spaces but special characters will be stripped out.
            thickness: Number for the thickness of the shade layer [m].
                Default is 0.005 meters (5 mm).
            solar_transmittance: Number between 0 and 1 for the transmittance
                of solar radiation through the shade.
                Default is 0.4, which is typical of a white diffusing shade.
            solar_reflectance: Number between 0 and 1 for the reflectance of solar
                radiation off of the shade, averaged over the solar spectrum.
                Default value is 0.5, which is typical of a white diffusing shade.
            visible_transmittance: Number between 0 and 1 for the transmittance
                of visible light through the shade.
                Default is 0.4, which is typical of a white diffusing shade.
            visible_reflectance: Number between 0 and 1 for the reflectance of
                visible light off of the shade.
                Default value is 0.4, which is typical of a white diffusing shade.
            infrared_transmittance: Long-wave hemisperical transmittance of the shade.
                Default value is 0, which is typical of diffusing shades.
            emissivity: Number between 0 and 1 for the infrared hemispherical
                emissivity of the front side of the shade.  Default is 0.9, which
                is typical of most diffusing shade materials.
            conductivity: Number for the thermal conductivity of the shade [W/m-K].
            distance_to_glass: A number between 0.001 and 1.0 for the distance
                between the shade and neighboring glass layers [m].
                Default is 0.05 (50 mm).
            opening_multiplier: Factor between 0 and 1 that is multiplied by the
                area at the top, bottom and sides of the shade for air flow
                calculations. Default: 0.5.
            airflow_permeability: The fraction of the shade surface that is open to
                air flow. Must be between 0 and 0.8. Default is 0 for no permeability.
        """
        _EnergyWindowMaterialShadeBase.__init__(
            self, name, infrared_transmittance, emissivity,
            distance_to_glass, opening_multiplier)

        # default for checking transmittance + reflectance < 1
        self._solar_reflectance = 0
        self._visible_reflectance = 0

        self.thickness = thickness
        self.solar_transmittance = solar_transmittance
        self.solar_reflectance = solar_reflectance
        self.visible_transmittance = visible_transmittance
        self.visible_reflectance = visible_reflectance
        self.infrared_transmittance = infrared_transmittance
        self.conductivity = conductivity
        self.airflow_permeability = airflow_permeability

    @property
    def thickness(self):
        """Get or set the thickess of the shade material layer [m]."""
        return self._thickness

    @thickness.setter
    def thickness(self, thick):
        self._thickness = float_positive(thick, 'shade material thickness')

    @property
    def solar_transmittance(self):
        """Get or set the solar transmittance of the shade."""
        return self._solar_transmittance

    @solar_transmittance.setter
    def solar_transmittance(self, s_tr):
        s_tr = float_in_range(s_tr, 0.0, 1.0, 'shade material solar transmittance')
        assert s_tr + self._solar_reflectance <= 1, 'Sum of shade transmittance and ' \
            'reflectance ({}) is greater than 1.'.format(s_tr + self._solar_reflectance)
        self._solar_transmittance = s_tr

    @property
    def solar_reflectance(self):
        """Get or set the front solar reflectance of the shade."""
        return self._solar_reflectance

    @solar_reflectance.setter
    def solar_reflectance(self, s_ref):
        s_ref = float_in_range(s_ref, 0.0, 1.0, 'shade material solar reflectance')
        assert s_ref + self._solar_transmittance <= 1, 'Sum of shade transmittance ' \
            'and reflectance ({}) is greater than 1.'.format(
                s_ref + self._solar_transmittance)
        self._solar_reflectance = s_ref

    @property
    def visible_transmittance(self):
        """Get or set the visible transmittance of the shade."""
        return self._visible_transmittance

    @visible_transmittance.setter
    def visible_transmittance(self, v_tr):
        v_tr = float_in_range(v_tr, 0.0, 1.0, 'shade material visible transmittance')
        assert v_tr + self._visible_reflectance <= 1, 'Sum of shade transmittance ' \
            'and reflectance ({}) is greater than 1.'.format(
                v_tr + self._visible_reflectance)
        self._visible_transmittance = v_tr

    @property
    def visible_reflectance(self):
        """Get or set the front visible reflectance of the shade."""
        return self._visible_reflectance

    @visible_reflectance.setter
    def visible_reflectance(self, v_ref):
        v_ref = float_in_range(v_ref, 0.0, 1.0, 'shade material visible reflectance')
        assert v_ref + self._visible_transmittance <= 1, 'Sum of shade transmittance ' \
            'and reflectance ({}) is greater than 1.'.format(
                v_ref + self._visible_transmittance)
        self._visible_reflectance = v_ref

    @property
    def visible_reflectance_back(self):
        """Get or set the back visible reflectance of the glass at normal incidence."""
        return self._visible_reflectance_back if self._visible_reflectance_back \
            is not None else self._visible_reflectance

    @visible_reflectance_back.setter
    def visible_reflectance_back(self, v_ref):
        if v_ref is not None:
            v_ref = float_in_range(v_ref, 0.0, 1.0, 'shade material visible reflectance')
            assert v_ref + self._visible_transmittance <= 1, 'Sum of window ' \
                'transmittance and reflectance ({}) is greater than 1.'.format(
                    v_ref + self._visible_transmittance)
        self._visible_reflectance_back = v_ref

    @property
    def conductivity(self):
        """Get or set the conductivity of the shade layer [W/m-K]."""
        return self._conductivity

    @conductivity.setter
    def conductivity(self, cond):
        self._conductivity = float_positive(cond, 'shade material conductivity')

    @property
    def airflow_permeability(self):
        """Get or set the fraction of the shade surface open to air flow."""
        return self._airflow_permeability

    @airflow_permeability.setter
    def airflow_permeability(self, perm):
        self._airflow_permeability = float_in_range(
            perm, 0.0, 0.8, 'shade material permeability')

    @property
    def resistivity(self):
        """Get or set the resistivity of the shade layer [m-K/W]."""
        return 1 / self._conductivity

    @resistivity.setter
    def resistivity(self, resis):
        self._conductivity = 1 / float_positive(resis, 'shade material resistivity')

    @property
    def u_value(self):
        """U-value of the material layer [W/m2-K] (excluding air film resistance)."""
        return self.conductivity / self.thickness

    @u_value.setter
    def u_value(self, u_val):
        self.r_value = 1 / float_positive(u_val, 'shade material u-value')

    @property
    def r_value(self):
        """R-value of the material layer [m2-K/W] (excluding air film resistance)."""
        return self.thickness / self.conductivity

    @r_value.setter
    def r_value(self, r_val):
        self._conductivity = self.thickness / \
            float_positive(r_val, 'shade material r-value')

    @classmethod
    def from_idf(cls, idf_string):
        """Create EnergyWindowMaterialShade from an EnergyPlus text string.

        Args:
            idf_string: A text string fully describing an EnergyPlus material.
        """
        ep_s = parse_idf_string(idf_string, 'WindowMaterial:Shade,')
        new_mat = cls(ep_s[0], ep_s[7], ep_s[1], ep_s[2], ep_s[3], ep_s[4],
                      ep_s[6], ep_s[5], ep_s[8], ep_s[9], ep_s[10], ep_s[14])
        new_mat.bottom_opening_multiplier = ep_s[11]
        new_mat.left_opening_multiplier = ep_s[12]
        new_mat.right_opening_multiplier = ep_s[13]
        return new_mat

    @classmethod
    def from_dict(cls, data):
        """Create a EnergyWindowMaterialShade from a dictionary.

        Args:
            data: {
                "type": 'EnergyWindowMaterialShade',
                "name": 'Dark Insulating Shade',
                "thickness": 0.02,
                "solar_transmittance": 0.05,
                "solar_reflectance": 0.2,
                "visible_transmittance": 0.05,
                "visible_reflectance": 0.15,
                "emissivity": 0.9,
                "infrared_transmittance": 0,
                "conductivity": 0.1}
        """
        assert data['type'] == 'EnergyWindowMaterialShade', \
            'Expected EnergyWindowMaterialShade. Got {}.'.format(data['type'])

        optional_keys = (
            'thickness', 'solar_transmittance', 'solar_reflectance',
            'visible_transmittance', 'visible_reflectance', 'infrared_transmittance',
            'emissivity', 'conductivity', 'distance_to_glass',
            'top_opening_multiplier', 'bottom_opening_multiplier',
            'left_opening_multiplier', 'right_opening_multiplier',
            'airflow_permeability')
        optional_vals = (0.005, 0.4, 0.5, 0.4, 0.4, 0, 0.9, 0.9, 0.05,
                         0.5, 0.5, 0.5, 0.5, 0)
        for key, val in zip(optional_keys, optional_vals):
            if key not in data:
                data[key] = val

        new_mat = cls(data['name'], data['thickness'], data['solar_transmittance'],
                      data['solar_reflectance'],
                      data['visible_transmittance'], data['visible_reflectance'],
                      data['infrared_transmittance'], data['emissivity'],
                      data['conductivity'], data['distance_to_glass'],
                      data['top_opening_multiplier'], data['airflow_permeability'])
        new_mat.bottom_opening_multiplier = data['bottom_opening_multiplier']
        new_mat.left_opening_multiplier = data['left_opening_multiplier']
        new_mat.right_opening_multiplier = data['right_opening_multiplier']
        return new_mat

    def to_idf(self):
        """Get an EnergyPlus string representation of the material."""
        values = (self.name, self.solar_transmittance, self.solar_reflectance,
                  self.visible_transmittance, self.visible_reflectance,
                  self.emissivity, self.infrared_transmittance, self.thickness,
                  self.conductivity, self.top_opening_multiplier,
                  self.bottom_opening_multiplier, self.left_opening_multiplier,
                  self.right_opening_multiplier, self.airflow_permeability)
        comments = ('name', 'solar transmittance', 'solar reflectance',
                    'visible transmittance', 'visible reflectance', 'emissivity',
                    'infrared transmittance', 'thickness {m}', 'conductivity {W/m-K}',
                    'distance to glass {m}', 'top opening multiplier',
                    'bottom opening multiplier', 'left opening multiplier',
                    'right opening multiplier', 'airflow permeability')
        return generate_idf_string('WindowMaterial:Shade', values, comments)

    def to_dict(self):
        """Energy Window Material Shade dictionary representation."""
        return {
            'type': 'EnergyWindowMaterialShade',
            'name': self.name,
            'thickness': self.thickness,
            'solar_transmittance': self.solar_transmittance,
            'solar_reflectance': self.solar_reflectance,
            'visible_transmittance': self.visible_transmittance,
            'visible_reflectance': self.visible_reflectance,
            'infrared_transmittance': self.infrared_transmittance,
            'emissivity': self.emissivity,
            'conductivity': self.conductivity,
            'distance_to_glass': self.distance_to_glass,
            'top_opening_multiplier': self.top_opening_multiplier,
            'bottom_opening_multiplier': self.bottom_opening_multiplier,
            'left_opening_multiplier': self.left_opening_multiplier,
            'right_opening_multiplier': self.right_opening_multiplier,
            'airflow_permeability': self.airflow_permeability
        }

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.name, self.thickness, self.solar_transmittance,
                self.solar_reflectance, self.visible_transmittance,
                self.visible_reflectance, self.infrared_transmittance,
                self.emissivity, self.conductivity, self.distance_to_glass,
                self.top_opening_multiplier, self.bottom_opening_multiplier,
                self.left_opening_multiplier, self.right_opening_multiplier,
                self.airflow_permeability)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, EnergyWindowMaterialShade) and \
            self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return self.to_idf()

    def __copy__(self):
        new_material = EnergyWindowMaterialShade(
            self.name, self.thickness, self.solar_transmittance, self.solar_reflectance,
            self.visible_transmittance, self.visible_reflectance,
            self.infrared_transmittance, self.emissivity,
            self.conductivity, self.distance_to_glass,
            self.top_opening_multiplier, self.airflow_permeability)
        new_material._top_opening_multiplier = self._top_opening_multiplier
        new_material._bottom_opening_multiplier = self._bottom_opening_multiplier
        new_material._left_opening_multiplier = self._left_opening_multiplier
        new_material._right_opening_multiplier = self._right_opening_multiplier
        return new_material


@lockable
class EnergyWindowMaterialBlind(_EnergyWindowMaterialShadeBase):
    """A material for a blind layer in a window construction.

    Window blind properties consist of flat, equally-spaced slats.

    Properties:
        name
        slat_orientation
        slat_width
        slat_separation
        slat_thickness
        slat_angle
        slat_conductivity
        beam_solar_transmittance
        beam_solar_reflectance
        beam_solar_reflectance_back
        diffuse_solar_transmittance
        diffuse_solar_reflectance
        diffuse_solar_reflectance_back
        beam_visible_transmittance
        beam_visible_reflectance
        beam_visible_reflectance_back
        diffuse_visible_transmittance
        diffuse_visible_reflectance
        diffuse_visible_reflectance_back
        infrared_transmittance
        emissivity
        emissivity_back
        distance_to_glass
        top_opening_multiplier
        bottom_opening_multiplier
        left_opening_multiplier
        right_opening_multiplier
        minimum_slat_angle
        maximum_slat_angle
        slat_resistivity
        u_value
        r_value
    """
    ORIENTATIONS = ('Horizontal', 'Vertical')
    __slots__ = ('_slat_orientation', '_slat_width', '_slat_separation',
                 '_slat_thickness', '_slat_angle', '_slat_conductivity',
                 '_beam_solar_transmittance', '_beam_solar_reflectance',
                 '_beam_solar_reflectance_back', '_diffuse_solar_transmittance',
                 '_diffuse_solar_reflectance', '_diffuse_solar_reflectance_back',
                 '_beam_visible_transmittance', '_beam_visible_reflectance',
                 '_beam_visible_reflectance_back', '_diffuse_visible_transmittance',
                 '_diffuse_visible_reflectance', '_diffuse_visible_reflectance_back',
                 '_emissivity_back', '_minimum_slat_angle', '_maximum_slat_angle')

    def __init__(self, name, slat_orientation='Horizontal', slat_width=0.025,
                 slat_separation=0.01875, slat_thickness=0.001, slat_angle=45,
                 slat_conductivity=221, solar_transmittance=0, solar_reflectance=0.5,
                 visible_transmittance=0, visible_reflectance=0.5,
                 infrared_transmittance=0, emissivity=0.9,
                 distance_to_glass=0.05, opening_multiplier=0.5):
        """Initialize energy windoww material glazing.

        Args:
            name: Text string for material name. Must be <= 100 characters.
                Can include spaces but special characters will be stripped out.
            slat_orientation: Text describing the orientation of the slats.
                Only the following two options are acceptable:
                "Horizontal", "Vertical". Default: "Horizontal"
            slat_width: The width of slat measured from edge to edge [m].
                Default: 0.025 m (25 mm).
            slat_separation: The distance between each of the slats [m].
                Default: 0.01875 m (18.75 mm).
            slat_thickness: A number between 0 and 0.1 for the thickness of the slat [m].
                Default: 0.001 m (1 mm).
            slat_angle: A number between 0 and 180 for the angle between the slats
                and the glazing normal in degrees. 90 signifies slats that are
                perpendicular to the glass. Default: 45.
            slat_conductivity: The thermal conductivity of the blind material [W/m-K].
                Default is 221, which is characteristic of metal blinds.
            solar_transmittance: Number between 0 and 1 for the transmittance
                of solar radiation through the blind material. Default: 0.
            solar_reflectance: Number between 0 and 1 for the front reflectance
                of solar radiation off of the blind, averaged over the solar
                spectrum. Default: 0.5.
            visible_transmittance: Number between 0 and 1 for the transmittance
                of visible light through the blind material. Default : 0.
            visible_reflectance: Number between 0 and 1 for the reflectance of
                visible light off of the blind. Default: 0.5.
            infrared_transmittance: Long-wave hemisperical transmittance of the blind.
                Default vallue is 0.
            emissivity: Number between 0 and 1 for the infrared hemispherical
                emissivity of the blind.  Default is 0.9.
            distance_to_glass: A number between 0.001 and 1.0 for the distance from
                the mid-plane of the blind to the adjacent glass layers [m].
                Default is 0.05 (50 mm).
            opening_multiplier: Factor between 0 and 1 that is multiplied by the
                area at the top, bottom and sides of the shade for air flow
                calculations. Default: 0.5.
        """
        _EnergyWindowMaterialShadeBase.__init__(
            self, name, infrared_transmittance, emissivity,
            distance_to_glass, opening_multiplier)

        # default for checking transmittance + reflectance < 1
        self._beam_solar_reflectance = 0
        self._beam_solar_reflectance_back = None
        self._diffuse_solar_reflectance = 0
        self._diffuse_solar_reflectance_back = None
        self._beam_visible_reflectance = 0
        self._beam_visible_reflectance_back = None
        self._diffuse_visible_reflectance = 0
        self._diffuse_visible_reflectance_back = None

        self.slat_orientation = slat_orientation
        self.slat_width = slat_width
        self.slat_separation = slat_separation
        self.slat_thickness = slat_thickness
        self.slat_angle = slat_angle
        self.slat_conductivity = slat_conductivity
        self.set_all_solar_transmittance(solar_transmittance)
        self.set_all_solar_reflectance(solar_reflectance)
        self.set_all_visible_transmittance(visible_transmittance)
        self.set_all_visible_reflectance(visible_reflectance)
        self.infrared_transmittance = infrared_transmittance
        self.emissivity_back = None
        self._minimum_slat_angle = 0
        self._maximum_slat_angle = 180

    @property
    def slat_orientation(self):
        """Get or set text describing the slat orientation.

        Must be one of the following: ["Horizontal", "Vertical"].
        """
        return self._slat_orientation

    @slat_orientation.setter
    def slat_orientation(self, orient):
        assert orient in self.ORIENTATIONS, 'Invalid input "{}" for slat ' \
            'orientation.\nMust be one of the following:{}'.format(
                orient, self.ORIENTATIONS)
        self._slat_orientation = orient

    @property
    def slat_width(self):
        """Get or set the width of slat measured from edge to edge [m]"""
        return self._slat_width

    @slat_width.setter
    def slat_width(self, width):
        self._slat_width = float_in_range(width, 0.0, 1.0, 'shade material slat width')

    @property
    def slat_separation(self):
        """Get or set the distance between each of the slats [m]"""
        return self._slat_separation

    @slat_separation.setter
    def slat_separation(self, separ):
        self._slat_separation = float_in_range(
            separ, 0.0, 1.0, 'shade material slat separation')

    @property
    def slat_thickness(self):
        """Get or set the thickness of the slat [m]."""
        return self._slat_thickness

    @slat_thickness.setter
    def slat_thickness(self, thick):
        self._slat_thickness = float_in_range(
            thick, 0.0, 0.1, 'shade material slat thickness')

    @property
    def slat_angle(self):
        """Get or set the angle between the slats and the glazing normal."""
        return self._slat_angle

    @slat_angle.setter
    def slat_angle(self, angle):
        self._slat_angle = float_in_range(angle, 0, 180, 'shade material slat angle')

    @property
    def slat_conductivity(self):
        """Get or set the conductivity of the blind material [W/m-K]."""
        return self._slat_conductivity

    @slat_conductivity.setter
    def slat_conductivity(self, cond):
        self._slat_conductivity = float_positive(cond, 'shade material conductivity')

    @property
    def beam_solar_transmittance(self):
        """Get or set the beam solar transmittance of the blind material."""
        return self._beam_solar_transmittance

    @beam_solar_transmittance.setter
    def beam_solar_transmittance(self, s_tr):
        s_tr = float_in_range(s_tr, 0.0, 1.0, 'shade material solar transmittance')
        assert s_tr + self._beam_solar_reflectance <= 1, 'Sum of blind ' \
            'transmittance and reflectance ({}) is greater than 1.'.format(
                s_tr + self._beam_solar_reflectance)
        if self._beam_solar_reflectance_back is not None:
            assert s_tr + self._beam_solar_reflectance_back <= 1, 'Sum of blind ' \
                'transmittance and reflectance ({}) is greater than 1.'.format(
                    s_tr + self._beam_solar_reflectance_back)
        self._beam_solar_transmittance = s_tr

    @property
    def beam_solar_reflectance(self):
        """Get or set the front beam solar reflectance of the blind."""
        return self._beam_solar_reflectance

    @beam_solar_reflectance.setter
    def beam_solar_reflectance(self, s_ref):
        s_ref = float_in_range(s_ref, 0.0, 1.0, 'shade material solar reflectance')
        assert s_ref + self._beam_solar_transmittance <= 1, 'Sum of window ' \
            'transmittance and reflectance ({}) is greater than 1.'.format(
                s_ref + self._beam_solar_transmittance)
        self._beam_solar_reflectance = s_ref

    @property
    def beam_solar_reflectance_back(self):
        """Get or set the back beam solar reflectance of the blind."""
        return self._beam_solar_reflectance_back if \
            self._beam_solar_reflectance_back is not None \
            else self._beam_solar_reflectance

    @beam_solar_reflectance_back.setter
    def beam_solar_reflectance_back(self, s_ref):
        if s_ref is not None:
            s_ref = float_in_range(s_ref, 0.0, 1.0, 'shade material solar reflectance')
            assert s_ref + self._beam_solar_transmittance <= 1, 'Sum of window ' \
                'transmittance and reflectance ({}) is greater than 1.'.format(
                    s_ref + self._beam_solar_transmittance)
        self._beam_solar_reflectance_back = s_ref

    @property
    def diffuse_solar_transmittance(self):
        """Get or set the diffuse solar transmittance of the blind material."""
        return self._diffuse_solar_transmittance

    @diffuse_solar_transmittance.setter
    def diffuse_solar_transmittance(self, s_tr):
        s_tr = float_in_range(s_tr, 0.0, 1.0, 'shade material solar transmittance')
        assert s_tr + self._diffuse_solar_reflectance <= 1, 'Sum of blind ' \
            'transmittance and reflectance ({}) is greater than 1.'.format(
                s_tr + self._diffuse_solar_reflectance)
        if self._diffuse_solar_reflectance_back is not None:
            assert s_tr + self._diffuse_solar_reflectance_back <= 1, 'Sum of blind' \
                ' transmittance and reflectance ({}) is greater than 1.'.format(
                    s_tr + self._diffuse_solar_reflectance_back)
        self._diffuse_solar_transmittance = s_tr

    @property
    def diffuse_solar_reflectance(self):
        """Get or set the front diffuse solar reflectance of the blind."""
        return self._diffuse_solar_reflectance

    @diffuse_solar_reflectance.setter
    def diffuse_solar_reflectance(self, s_ref):
        s_ref = float_in_range(s_ref, 0.0, 1.0, 'shade material solar reflectance')
        assert s_ref + self._diffuse_solar_transmittance <= 1, 'Sum of window ' \
            'transmittance and reflectance ({}) is greater than 1.'.format(
                s_ref + self._diffuse_solar_transmittance)
        self._diffuse_solar_reflectance = s_ref

    @property
    def diffuse_solar_reflectance_back(self):
        """Get or set the back diffuse solar reflectance of the blind."""
        return self._diffuse_solar_reflectance_back if \
            self._diffuse_solar_reflectance_back is not None \
            else self._diffuse_solar_reflectance

    @diffuse_solar_reflectance_back.setter
    def diffuse_solar_reflectance_back(self, s_ref):
        if s_ref is not None:
            s_ref = float_in_range(s_ref, 0.0, 1.0, 'shade material solar reflectance')
            assert s_ref + self._diffuse_solar_transmittance <= 1, 'Sum of window ' \
                'transmittance and reflectance ({}) is greater than 1.'.format(
                    s_ref + self._diffuse_solar_transmittance)
        self._diffuse_solar_reflectance_back = s_ref

    @property
    def beam_visible_transmittance(self):
        """Get or set the beam visible transmittance of the blind material."""
        return self._beam_visible_transmittance

    @beam_visible_transmittance.setter
    def beam_visible_transmittance(self, s_tr):
        s_tr = float_in_range(s_tr, 0.0, 1.0, 'shade material solar transmittance')
        assert s_tr + self._beam_visible_reflectance <= 1, 'Sum of blind ' \
            'transmittance and reflectance ({}) is greater than 1.'.format(
                s_tr + self._beam_visible_reflectance)
        if self._beam_visible_reflectance_back is not None:
            assert s_tr + self._beam_visible_reflectance_back <= 1, 'Sum of blind ' \
                'transmittance and reflectance ({}) is greater than 1.'.format(
                    s_tr + self._beam_visible_reflectance_back)
        self._beam_visible_transmittance = s_tr

    @property
    def beam_visible_reflectance(self):
        """Get or set the front beam visible reflectance of the blind."""
        return self._beam_visible_reflectance

    @beam_visible_reflectance.setter
    def beam_visible_reflectance(self, s_ref):
        s_ref = float_in_range(s_ref, 0.0, 1.0, 'shade material solar reflectance')
        assert s_ref + self._beam_visible_transmittance <= 1, 'Sum of window ' \
            'transmittance and reflectance ({}) is greater than 1.'.format(
                s_ref + self._beam_visible_transmittance)
        self._beam_visible_reflectance = s_ref

    @property
    def beam_visible_reflectance_back(self):
        """Get or set the back beam visible reflectance of the blind."""
        return self._beam_visible_reflectance_back if \
            self._beam_visible_reflectance_back is not None \
            else self._beam_visible_reflectance

    @beam_visible_reflectance_back.setter
    def beam_visible_reflectance_back(self, s_ref):
        if s_ref is not None:
            s_ref = float_in_range(s_ref, 0.0, 1.0, 'shade material solar reflectance')
            assert s_ref + self._beam_visible_transmittance <= 1, 'Sum of window ' \
                'transmittance and reflectance ({}) is greater than 1.'.format(
                    s_ref + self._beam_visible_transmittance)
        self._beam_visible_reflectance_back = s_ref

    @property
    def diffuse_visible_transmittance(self):
        """Get or set the diffuse visible transmittance of the blind material."""
        return self._diffuse_visible_transmittance

    @diffuse_visible_transmittance.setter
    def diffuse_visible_transmittance(self, s_tr):
        s_tr = float_in_range(s_tr, 0.0, 1.0, 'shade material solar transmittance')
        assert s_tr + self._diffuse_visible_reflectance <= 1, 'Sum of blind ' \
            'transmittance and reflectance ({}) is greater than 1.'.format(
                s_tr + self._diffuse_visible_reflectance)
        if self._diffuse_visible_reflectance_back is not None:
            assert s_tr + self._diffuse_visible_reflectance_back <= 1, 'Sum of blind' \
                ' transmittance and reflectance ({}) is greater than 1.'.format(
                    s_tr + self._diffuse_visible_reflectance_back)
        self._diffuse_visible_transmittance = s_tr

    @property
    def diffuse_visible_reflectance(self):
        """Get or set the front diffuse visible reflectance of the blind."""
        return self._diffuse_visible_reflectance

    @diffuse_visible_reflectance.setter
    def diffuse_visible_reflectance(self, s_ref):
        s_ref = float_in_range(s_ref, 0.0, 1.0, 'shade material solar reflectance')
        assert s_ref + self._diffuse_visible_transmittance <= 1, 'Sum of window ' \
            'transmittance and reflectance ({}) is greater than 1.'.format(
                s_ref + self._diffuse_visible_transmittance)
        self._diffuse_visible_reflectance = s_ref

    @property
    def diffuse_visible_reflectance_back(self):
        """Get or set the back diffuse visible reflectance of the blind."""
        return self._diffuse_visible_reflectance_back if \
            self._diffuse_visible_reflectance_back is not None \
            else self._diffuse_visible_reflectance

    @diffuse_visible_reflectance_back.setter
    def diffuse_visible_reflectance_back(self, s_ref):
        if s_ref is not None:
            s_ref = float_in_range(s_ref, 0.0, 1.0, 'shade material solar reflectance')
            assert s_ref + self._diffuse_visible_transmittance <= 1, 'Sum of window ' \
                'transmittance and reflectance ({}) is greater than 1.'.format(
                    s_ref + self._diffuse_visible_transmittance)
        self._diffuse_visible_reflectance_back = s_ref

    @property
    def emissivity_back(self):
        """Get or set the hemispherical emissivity of the back side of the glass."""
        return self._emissivity_back if self._emissivity_back is not None \
            else self._emissivity

    @emissivity_back.setter
    def emissivity_back(self, ir_e):
        if ir_e is not None:
            ir_e = float_in_range(ir_e, 0.0, 1.0, 'shade material emissivity')
        self._emissivity_back = ir_e

    @property
    def minimum_slat_angle(self):
        """Get or set the minimum angle between the slats and the glazing normal."""
        return self._minimum_slat_angle

    @minimum_slat_angle.setter
    def minimum_slat_angle(self, angle):
        _ang = float_in_range(angle, 0, 180, 'shade material slat angle')
        assert _ang < self._maximum_slat_angle, \
            'Minimum slat angle is greater than maximum slat angle.'
        self._minimum_slat_angle = _ang

    @property
    def maximum_slat_angle(self):
        """Get or set the maximum angle between the slats and the glazing normal."""
        return self._maximum_slat_angle

    @maximum_slat_angle.setter
    def maximum_slat_angle(self, angle):
        _ang = float_in_range(angle, 0, 180, 'shade material slat angle')
        assert _ang > self._minimum_slat_angle, \
            'maximum slat angle is less than minimum slat angle.'
        self._maximum_slat_angle = _ang

    @property
    def slat_resistivity(self):
        """Get or set the resistivity of the blind layer [m-K/W]."""
        return 1 / self._slat_conductivity

    @slat_resistivity.setter
    def slat_resistivity(self, resis):
        self._slat_conductivity = 1 / float_positive(resis, 'shade material resistivity')

    @property
    def u_value(self):
        """U-value of the blind slats [W/m2-K] (excluding air film resistance).

        Note that this value assumes that blinds are cmpletely closed (at 0 degrees).
        """
        return self.slat_conductivity / self.slat_thickness

    @u_value.setter
    def u_value(self, u_val):
        self.r_value = 1 / float_positive(u_val, 'shade material u-value')

    @property
    def r_value(self):
        """R-value of the blind slats [m2-K/W] (excluding air film resistance).

        Note that this value assumes that blinds are cmpletely closed (at 0 degrees).
        """
        return self.slat_thickness / self.slat_conductivity

    @r_value.setter
    def r_value(self, r_val):
        self._slat_conductivity = self.slat_thickness / \
            float_positive(r_val, 'shade material r-value')

    def set_all_solar_transmittance(self, transmittance):
        """Set all solar transmittance to the same value at once."""
        self.beam_solar_transmittance = transmittance
        self.diffuse_solar_transmittance = transmittance

    def set_all_solar_reflectance(self, reflectance):
        """Set all solar reflectance to the same value at once."""
        self.beam_solar_reflectance = reflectance
        self.beam_solar_reflectance_back = None
        self.diffuse_solar_reflectance = reflectance
        self.diffuse_solar_reflectance_back = None

    def set_all_visible_transmittance(self, transmittance):
        """Set all solar transmittance to the same value at once."""
        self.beam_visible_transmittance = transmittance
        self.diffuse_visible_transmittance = transmittance

    def set_all_visible_reflectance(self, reflectance):
        """Set all visible reflectance to the same value at once."""
        self.beam_visible_reflectance = reflectance
        self.beam_visible_reflectance_back = None
        self.diffuse_visible_reflectance = reflectance
        self.diffuse_visible_reflectance_back = None

    @classmethod
    def from_idf(cls, idf_string):
        """Create EnergyWindowMaterialBlind from an EnergyPlus text string.

        Args:
            idf_string: A text string fully describing an EnergyPlus material.
        """
        ep_s = parse_idf_string(idf_string, 'WindowMaterial:Blind,')
        new_mat = cls(ep_s[0], ep_s[1], ep_s[2], ep_s[3], ep_s[4], ep_s[5],
                      ep_s[6], ep_s[7], ep_s[8], ep_s[13], ep_s[14], ep_s[19],
                      ep_s[20], ep_s[22], ep_s[23])
        new_mat.beam_solar_reflectance_back = ep_s[9]
        new_mat.diffuse_solar_transmittance = ep_s[10]
        new_mat.diffuse_solar_reflectance = ep_s[11]
        new_mat.diffuse_solar_reflectance_back = ep_s[12]
        new_mat.beam_visible_reflectance_back = ep_s[15]
        new_mat.diffuse_visible_transmittance = ep_s[16]
        new_mat.diffuse_visible_reflectance = ep_s[17]
        new_mat.diffuse_visible_reflectance_back = ep_s[18]
        new_mat.emissivity_back = ep_s[21]
        new_mat.bottom_opening_multiplier = ep_s[24]
        new_mat.left_opening_multiplier = ep_s[25]
        new_mat.right_opening_multiplier = ep_s[26]
        new_mat.minimum_slat_angle = ep_s[27]
        new_mat.maximum_slat_angle = ep_s[28]
        return new_mat

    @classmethod
    def from_dict(cls, data):
        """Create a EnergyWindowMaterialBlind from a dictionary.

        Args:
            data: {
                "type": 'EnergyWindowMaterialBlind',
                "name": 'Plastic Blind',
                "slat_orientation": 'Horizontal',
                "slat_width": 0.04,
                "slat_separation": 0.03,
                "slat_thickness": 0.002,
                "slat_angle": 90,
                "slat_conductivity": 0.2}
        """
        assert data['type'] == 'EnergyWindowMaterialBlind', \
            'Expected EnergyWindowMaterialBlind. Got {}.'.format(data['type'])

        optional_keys = (
            'slat_orientation', 'slat_width', 'slat_separation', 'slat_thickness',
            'slat_angle', 'slat_conductivity', 'beam_solar_transmittance',
            'beam_solar_reflectance', 'beam_solar_reflectance_back',
            'diffuse_solar_transmittance', 'diffuse_solar_reflectance',
            'diffuse_solar_reflectance_back', 'beam_visible_transmittance',
            'beam_visible_reflectance', 'beam_visible_reflectance_back',
            'diffuse_visible_transmittance', 'diffuse_visible_reflectance',
            'diffuse_visible_reflectance_back', 'infrared_transmittance', 'emissivity',
            'emissivity_back', 'distance_to_glass', 'top_opening_multiplier',
            'bottom_opening_multiplier', 'left_opening_multiplier',
            'right_opening_multiplier', 'minimum_slat_angle', 'maximum_slat_angle')
        optional_vals = ('Horizontal', 0.025, 0.01875, 0.001, 45, 221, 0, 0.5, None,
                         0, 0.5, None, 0, 0.5, None, 0, 0.5, None, 0, 0.9, None, 0.05,
                         0.5, 0.5, 0.5, 0.5, 0, 180)
        for key, val in zip(optional_keys, optional_vals):
            if key not in data:
                data[key] = val

        new_mat = cls(
            data['name'], data['slat_orientation'], data['slat_width'],
            data['slat_separation'], data['slat_thickness'],
            data['slat_angle'], data['slat_conductivity'],
            data['beam_solar_transmittance'], data['beam_solar_reflectance'],
            data['beam_visible_transmittance'], data['beam_visible_reflectance'],
            data['infrared_transmittance'], data['emissivity'],
            data['distance_to_glass'], data['top_opening_multiplier'])

        new_mat.beam_solar_reflectance_back = data['beam_solar_reflectance_back']
        new_mat.diffuse_solar_transmittance = data['diffuse_solar_transmittance']
        new_mat.diffuse_solar_reflectance = data['diffuse_solar_reflectance']
        new_mat.diffuse_solar_reflectance_back = data['diffuse_solar_reflectance_back']
        new_mat.beam_visible_reflectance_back = data['beam_visible_reflectance_back']
        new_mat.diffuse_visible_transmittance = data['diffuse_visible_transmittance']
        new_mat.diffuse_visible_reflectance = data['diffuse_visible_reflectance']
        new_mat.diffuse_visible_reflectance_back = \
            data['diffuse_visible_reflectance_back']
        new_mat.emissivity_back = data['emissivity_back']
        new_mat.bottom_opening_multiplier = data['bottom_opening_multiplier']
        new_mat.left_opening_multiplier = data['left_opening_multiplier']
        new_mat.right_opening_multiplier = data['right_opening_multiplier']
        new_mat.minimum_slat_angle = data['minimum_slat_angle']
        new_mat.maximum_slat_angle = data['maximum_slat_angle']
        return new_mat

    def to_idf(self):
        """Get an EnergyPlus string representation of the material."""
        values = (self.name, self.slat_orientation, self.slat_width,
                  self.slat_separation, self.slat_thickness, self.slat_angle,
                  self.slat_conductivity, self.beam_solar_transmittance,
                  self.beam_solar_reflectance, self.beam_solar_reflectance_back,
                  self.diffuse_solar_transmittance, self.diffuse_solar_reflectance,
                  self.diffuse_solar_reflectance_back, self.beam_visible_transmittance,
                  self.beam_visible_reflectance, self.beam_visible_reflectance_back,
                  self.diffuse_visible_transmittance, self.diffuse_visible_reflectance,
                  self.diffuse_visible_reflectance_back, self.infrared_transmittance,
                  self.emissivity, self.emissivity_back, self.distance_to_glass,
                  self.top_opening_multiplier, self.bottom_opening_multiplier,
                  self.left_opening_multiplier, self.right_opening_multiplier,
                  self.minimum_slat_angle, self.maximum_slat_angle)
        comments = (
            'name', 'slat orientation', 'slat width {m}', 'slat separation {m}',
            'slat thickness {m}', 'slat angle {deg}',
            'slat conductivity {W/m-K}', 'beam solar transmittance',
            'beam solar reflectance front', 'beam solar reflectance back',
            'diffuse solar transmittance', 'diffuse solar reflectance front',
            'diffuse solar reflectance back', 'beam visible transmittance',
            'beam visible reflectance front', 'beam visible reflectance back',
            'diffuse visible transmittance', 'diffuse visible reflectance front',
            'diffuse visible reflectance back', 'infrared transmittance',
            'emissivity front', 'emissivity back', 'distance to glass {m}',
            'top opening multiplier', 'bottom opening multiplier',
            'left opening multiplier', 'right opening multiplier',
            'minimum slat angle {deg}', 'maximum slat angle {deg}')
        return generate_idf_string('WindowMaterial:Blind', values, comments)

    def to_dict(self):
        """Energy Window Material Blind dictionary representation."""
        return {
            'type': 'EnergyWindowMaterialBlind',
            'name': self.name,
            'slat_orientation': self.slat_orientation,
            'slat_width': self.slat_width,
            'slat_separation': self.slat_separation,
            'slat_thickness': self.slat_thickness,
            'slat_angle': self.slat_angle,
            'slat_conductivity': self.slat_conductivity,
            'beam_solar_transmittance': self.beam_solar_transmittance,
            'beam_solar_reflectance': self.beam_solar_reflectance,
            'beam_solar_reflectance_back': self.beam_solar_reflectance_back,
            'diffuse_solar_transmittance': self.diffuse_solar_transmittance,
            'diffuse_solar_reflectance': self.diffuse_solar_reflectance,
            'diffuse_solar_reflectance_back': self.diffuse_solar_reflectance_back,
            'beam_visible_transmittance': self.beam_visible_transmittance,
            'beam_visible_reflectance': self.beam_visible_reflectance,
            'beam_visible_reflectance_back': self.beam_visible_reflectance_back,
            'diffuse_visible_transmittance': self.diffuse_visible_transmittance,
            'diffuse_visible_reflectance': self.diffuse_visible_reflectance,
            'diffuse_visible_reflectance_back': self.diffuse_visible_reflectance_back,
            'infrared_transmittance': self.infrared_transmittance,
            'emissivity': self.emissivity,
            'emissivity_back': self.emissivity_back,
            'distance_to_glass': self.distance_to_glass,
            'top_opening_multiplier': self.top_opening_multiplier,
            'bottom_opening_multiplier': self.bottom_opening_multiplier,
            'left_opening_multiplier': self.left_opening_multiplier,
            'right_opening_multiplier': self.right_opening_multiplier,
            'minimum_slat_angle': self.minimum_slat_angle,
            'maximum_slat_angle': self.maximum_slat_angle
        }

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.name, self.slat_orientation, self.slat_width,
                self.slat_separation, self.slat_thickness, self.slat_angle,
                self.slat_conductivity, self.beam_solar_transmittance,
                self.beam_solar_reflectance, self.beam_solar_reflectance_back,
                self.diffuse_solar_transmittance, self.diffuse_solar_reflectance,
                self.diffuse_solar_reflectance_back, self.beam_visible_transmittance,
                self.beam_visible_reflectance, self.beam_visible_reflectance_back,
                self.diffuse_visible_transmittance, self.diffuse_visible_reflectance,
                self.diffuse_visible_reflectance_back, self.infrared_transmittance,
                self.emissivity, self.emissivity_back, self.distance_to_glass,
                self.top_opening_multiplier, self.bottom_opening_multiplier,
                self.left_opening_multiplier, self.right_opening_multiplier,
                self.minimum_slat_angle, self.maximum_slat_angle)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, EnergyWindowMaterialBlind) and \
            self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return self.to_idf()

    def __copy__(self):
        new_m = EnergyWindowMaterialBlind(
            self.name, self.slat_orientation, self.slat_width, self.slat_separation,
            self.slat_thickness, self.slat_angle, self.slat_conductivity,
            self.beam_solar_transmittance, self.beam_solar_reflectance,
            self.beam_visible_transmittance, self.beam_visible_reflectance,
            self.infrared_transmittance, self.emissivity, self.distance_to_glass,
            self.top_opening_multiplier)
        new_m._diffuse_solar_transmittance = self._diffuse_solar_transmittance
        new_m._beam_solar_reflectance_back = self._beam_solar_reflectance_back
        new_m._diffuse_solar_reflectance = self._diffuse_solar_reflectance
        new_m._diffuse_solar_reflectance_back = self._diffuse_solar_reflectance_back
        new_m._diffuse_visible_transmittance = self._diffuse_visible_transmittance
        new_m._beam_visible_reflectance_back = self._beam_visible_reflectance_back
        new_m._diffuse_visible_reflectance = self._diffuse_visible_reflectance
        new_m._diffuse_visible_reflectance_back = self._diffuse_visible_reflectance_back
        new_m._top_opening_multiplier = self._top_opening_multiplier
        new_m._bottom_opening_multiplier = self._bottom_opening_multiplier
        new_m._left_opening_multiplier = self._left_opening_multiplier
        new_m._right_opening_multiplier = self._right_opening_multiplier
        new_m._minimum_slat_angle = self._minimum_slat_angle
        new_m._maximum_slat_angle = self._maximum_slat_angle
        return new_m
