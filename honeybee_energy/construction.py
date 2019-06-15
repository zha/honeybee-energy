# coding=utf-8
"""Energy construction."""
from __future__ import division

from .material._base import _EnergyMaterialOpaqueBase, _EnergyMaterialWindowBase
from .material.opaque import EnergyMaterial, EnergyMaterialNoMass
from .material.glazing import _EnergyWindowMaterialGlazingBase, \
    EnergyWindowMaterialGlazing, EnergyWindowMaterialSimpleGlazSys
from .material.gas import _EnergyWindowMaterialGasBase, EnergyWindowMaterialGas, \
    EnergyWindowMaterialGasMixture, EnergyWindowMaterialGasCustom
from .material.shade import _EnergyWindowMaterialShadeBase, EnergyWindowMaterialShade, \
    EnergyWindowMaterialBlind

from honeybee.typing import valid_ep_string

import math
import re
import os


class _ConstructionBase(object):
    """Energy construction.

    Properties:
        name
        materials
    """
    # generic air material used to compute indoor film coefficients.
    _air = EnergyWindowMaterialGas('generic air', gas_type='Air')

    def __init__(self, name, materials):
        """Initialize energy construction.

        Args:
            name: Text string for construction name. Must be <= 100 characters.
                Can include spaces but special characters will be stripped out.
            materials: List of materials in the construction (from outside to inside).
        """
        self.name = name
        self.materials = list(materials)

    @property
    def name(self):
        """Get or set the text string for construction name."""
        return self._name

    @name.setter
    def name(self, name):
        self._name = valid_ep_string(name, 'construction name')

    @property
    def r_value(self):
        """R-value of the construction [m2-K/W] (excluding air films)."""
        return sum(tuple(mat.r_value for mat in self.materials))

    @property
    def u_value(self):
        """U-value of the construction [W/m2-K] (excluding air films)."""
        return 1 / self.r_value

    @property
    def r_factor(self):
        """Construction R-factor [m2-K/W] (including standard resistances for air films).

        Formulas for film coefficients come from EN673 / ISO10292.
        """
        _ext_r = 1 / self.out_h_simple()  # exterior heat transfer coefficient in m2-K/W
        _int_r = 1 / self.in_h_simple()  # interior film
        return self.r_value + _ext_r + _int_r

    @property
    def u_factor(self):
        """Construction U-factor [W/m2-K] (including standard resistances for air films).

        Formulas for film coefficients come from EN673 / ISO10292.
        """
        return 1 / self.r_factor

    def duplicate(self):
        """Get a copy of this construction."""
        return self.__copy__()

    def out_h_simple(self):
        """Get the simple outdoor heat transfer coefficient according to ISO 10292.

        This is used for all opaque R-factor calculations.
        """
        return 23

    def in_h_simple(self):
        """Get the simple indoor heat transfer coefficient according to ISO 10292.

        This is used for all opaque R-factor calculations.
        """
        return (3.6 + (4.4 * self.inside_emissivity / 0.84))

    def out_h(self, wind_speed=6.7, t_kelvin=273.15):
        """Get the detailed outdoor heat transfer coefficient according to ISO 15099.

        This is used for window U-factor calculations and all of the
        temperature_profile calculations.

        Args:
            wind_speed: The average outdoor wind speed [m/s]. This affects the
                convective heat transfer coefficient. Default is 6.7 m/s.
            t_kelvin: The average between the outdoor temperature and the
                exterior surface temperature. This can affect the radiative heat
                transfer. Default is 273.15K (0C).
        """
        _conv_h = 4 + (4 * wind_speed)
        _rad_h = 4 * 5.6697e-8 * self.outside_emissivity * (t_kelvin ** 3)
        return _conv_h + _rad_h

    def in_h(self, t_kelvin=293.15, delta_t=15, height=1.0, angle=90, pressure=101325):
        """Get the detailed indoor heat transfer coefficient according to ISO 15099.

        This is used for window U-factor calculations and all of the
        temperature_profile calculations.

        Args:
            t_kelvin: The average between the indoor temperature and the
                interior surface temperature. Default is 293.15K (20C).
            delta_t: The temperature diference between the indoor temperature and the
                interior surface temperature [C]. Default is 15C.
            height: An optional height for the surface in meters. Default is 1.0 m,
                which is consistent with NFRC standards.
            angle: An angle in degrees between 0 and 180.
                0 = A horizontal surface with downward heat flow through the layer.
                90 = A vertical surface
                180 = A horizontal surface with upward heat flow through the layer.
            pressure: The average pressure in Pa.
                Default is 101325 Pa for standard pressure at sea level.
        """
        _ray_numerator = (self._air.density_at_temperature(t_kelvin, pressure) ** 2) * \
            (height ** 3) * 9.81 * self._air.specific_heat_at_temperature(t_kelvin) \
            * delta_t
        _ray_denominator = t_kelvin * self._air.viscosity_at_temperature(t_kelvin) * \
            self._air.conductivity_at_temperature(t_kelvin)
        _rayleigh_h = abs(_ray_numerator / _ray_denominator)
        if angle < 15:
            nusselt = 0.13 * (_rayleigh_h ** (1 / 3))
        elif angle <= 90:
            _sin_a = math.sin(math.radians(angle))
            _rayleigh_c = 2.5e5 * ((math.exp(0.72 * angle) / _sin_a) ** (1 / 5))
            if _rayleigh_h < _rayleigh_c:
                nusselt = 0.56 * ((_rayleigh_h * _sin_a) ** (1 / 4))
            else:
                nu_1 = 0.56 * ((_rayleigh_c * _sin_a) ** (1 / 4))
                nu_2 = 0.13 * ((_rayleigh_h ** (1 / 3)) - (_rayleigh_c ** (1 / 3)))
                nusselt = nu_1 + nu_2
        elif angle <= 179:
            _sin_a = math.sin(math.radians(angle))
            nusselt = 0.56 * ((_rayleigh_h * _sin_a) ** (1 / 4))
        else:
            nusselt = 0.58 * (_rayleigh_h ** (1 / 5))
        _conv_h = nusselt * (self._air.conductivity_at_temperature(t_kelvin) / height)
        _rad_h = 4 * 5.6697e-8 * self.inside_emissivity * (t_kelvin ** 3)
        return _conv_h + _rad_h

    def _temperature_profile_from_r_values(
            self, r_values, outside_temperature=-18, inside_temperature=21):
        """Get a list of temperatures at each material boundary between R-values."""
        r_factor = sum(r_values)
        delta_t = inside_temperature - outside_temperature
        temperatures = [outside_temperature]
        for i, r_val in enumerate(r_values):
            temperatures.append(temperatures[i] + (delta_t * (r_val / r_factor)))
        return temperatures

    @staticmethod
    def _parse_ep_string(ep_string):
        """Parse an EnergyPlus material string into a tuple of values."""
        ep_string = ep_string.strip()
        ep_strings = ep_string.split(';')
        assert len(ep_strings) == 2, 'Received more than one object in ep_string.'
        ep_string = re.sub(r'!.*\n', '', ep_strings[0])
        ep_strs = [e_str.strip() for e_str in ep_string.split(',')]
        ep_strs.pop(0)  # remove the EnergyPlus object name
        return ep_strs

    @staticmethod
    def _generate_ep_string(constr_type, name, materials):
        """Get an EnergyPlus string representation from values and comments."""
        values = (name,) + tuple(mat.name for mat in materials)
        comments = ('name',) + tuple('layer %s' % (i + 1) for i in range(len(materials)))
        space_count = tuple((25 - len(str(n))) for n in values)
        spaces = tuple(s_c * ' ' if s_c > 0 else ' ' for s_c in space_count)
        ep_str = 'Construction,              !- ' + constr_type + '\n ' + '\n '.join(
            '{},{}!- {}'.format(val, space, com) for val, space, com in
            zip(values[:-1], spaces[:-1], comments[:-1]))
        return ep_str + '\n {};{}!- {}'.format(values[-1], spaces[-1], comments[-1])

    def __copy__(self):
        return self.__class__(self.name, [mat.duplicate() for mat in self.materials])

    def __len__(self):
        return len(self._materials)

    def __getitem__(self, key):
        return self._materials[key]

    def __iter__(self):
        return iter(self._materials)

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        return 'Construction,\n {},\n {}'.format(
            self.name, '\n '.join(tuple(mat.name for mat in self.materials)))


class OpaqueConstruction(_ConstructionBase):
    """Opaque energy construction.

    Properties:
        name
        materials
        r_value
        u_value
        u_factor
        r_factor
        inside_emissivity
        inside_solar_reflectance
        inside_visible_reflectance
        outside_emissivity
        outside_solar_reflectance
        outside_visible_reflectance
        mass_area_density
        area_heat_capacity
    """

    @property
    def materials(self):
        """Get or set a list of materials in the construction (outside to inside)."""
        return self._materials

    @materials.setter
    def materials(self, mats):
        try:
            if not isinstance(mats, tuple):
                mats = tuple(mats)
        except TypeError:
            raise TypeError('Expected list for construction materials. '
                            'Got {}'.format(type(mats)))
        for mat in mats:
            assert isinstance(mat, _EnergyMaterialOpaqueBase), 'Expected opaque energy' \
                ' material for construction. Got {}.'.format(type(mat))
        assert len(mats) > 0, 'Construction must possess at least one material.'
        assert len(mats) <= 10, 'Opaque Construction cannot have more than 10 materials.'
        self._materials = mats

    @property
    def inside_emissivity(self):
        """"The emissivity of the inside face of the construction."""
        return self.materials[-1].thermal_absorptance

    @property
    def inside_solar_reflectance(self):
        """"The solar reflectance of the inside face of the construction."""
        return 1 - self.materials[-1].solar_absorptance

    @property
    def inside_visible_reflectance(self):
        """"The visible reflectance of the inside face of the construction."""
        return 1 - self.materials[-1].visible_absorptance

    @property
    def outside_emissivity(self):
        """"The emissivity of the outside face of the construction."""
        return self.materials[0].thermal_absorptance

    @property
    def outside_solar_reflectance(self):
        """"The solar reflectance of the outside face of the construction."""
        return 1 - self.materials[0].solar_absorptance

    @property
    def outside_visible_reflectance(self):
        """"The visible reflectance of the outside face of the construction."""
        return 1 - self.materials[0].visible_absorptance

    @property
    def mass_area_density(self):
        """The area density of the construction [kg/m2]."""
        return sum(tuple(mat.mass_area_density for mat in self.materials))

    @property
    def area_heat_capacity(self):
        """The heat capacity per unit area of the construction [kg/K-m2]."""
        return sum(tuple(mat.area_heat_capacity for mat in self.materials))

    @property
    def thickness(self):
        """Thickness of the construction [m]."""
        thickness = 0
        for mat in self.materials:
            if isinstance(mat, EnergyMaterial):
                thickness += mat.thickness
        return thickness

    def temperature_profile(self, outside_temperature=-18, inside_temperature=21,
                            outside_wind_speed=6.7, height=1.0, angle=90.0,
                            pressure=101325):
        """Get a list of temperatures at each material boundary across the construction.

        Args:
            outside_temperature: The temperature on the outside of the construction [C].
                Default is -18, which is consistent with NFRC 100-2010.
            inside_temperature: The temperature on the inside of the construction [C].
                Default is 21, which is consistent with NFRC 100-2010.
            wind_speed: The average outdoor wind speed [m/s]. This affects outdoor
                convective heat transfer coefficient. Default is 6.7 m/s.
            height: An optional height for the surface in meters. Default is 1.0 m.
            angle: An angle in degrees between 0 and 180.
                0 = A horizontal surface with the outside boundary on the bottom.
                90 = A vertical surface
                180 = A horizontal surface with the outside boundary on the top.
            pressure: The average pressure of in Pa.
                Default is 101325 Pa for standard pressure at sea level.

        Returns:
            temperatures: A list of temperature values [C].
                The first value will always be the outside temperature and the
                second will be the exterior surface temperature.
                The last value will always be the inside temperature and the second
                to last will be the interior surface temperature.
            r_values: A list of R-values for each of the material layers [m2-K/W].
                The first value will always be the resistance of the exterior air
                and the last value is the resistance of the interior air.
                The sum of this list is the R-factor for this construction given
                the input parameters.
        """
        if angle != 90 and outside_temperature > inside_temperature:
            angle = abs(180 - angle)
        in_r_init = 1 / self.in_h_simple()
        r_values = [1 / self.out_h(outside_wind_speed, outside_temperature + 273.15)] + \
            [mat.r_value for mat in self.materials] + [in_r_init]
        in_delta_t = (in_r_init / sum(r_values)) * \
            (outside_temperature - inside_temperature)
        r_values[-1] = 1 / self.in_h(inside_temperature - (in_delta_t / 2) + 273.15,
                                     in_delta_t, height, angle, pressure)
        temperatures = self._temperature_profile_from_r_values(
            r_values, outside_temperature, inside_temperature)
        return temperatures, r_values

    @classmethod
    def from_idf(cls, ep_string, ep_mat_strings):
        """Create an OpaqueConstruction from an EnergyPlus IDF text string.

        Args:
            ep_string: A text string fully describing an EnergyPlus construction.
            ep_mat_strings: A list of text strings for each of the materials in
                the construction.
        """
        materials_dict = cls._idf_materials_dictionary(ep_mat_strings)
        ep_strs = cls._parse_ep_string(ep_string)
        materials = [materials_dict[mat] for mat in ep_strs[1:]]
        return cls(ep_strs[0], materials)

    @classmethod
    def from_standards_dict(cls, data, data_materials):
        """Create a OpaqueConstruction from an OpenStudio standards gem dictionary.

        Args:
            data: {
                "name": "Typical Insulated Exterior Mass Wall",
                "intended_surface_type": "ExteriorWall",
                "standards_construction_type": "Mass",
                "insulation_layer": "Typical Insulation",
                "materials": [
                    "1IN Stucco",
                    "8IN CONCRETE HW RefBldg",
                    "Typical Insulation",
                    "1/2IN Gypsum"]
                }
            data_materials: Dictionary representation of all materials in the
                OpenStudio standards gem.
        """
        try:
            materials_dict = tuple(data_materials[mat] for mat in data['materials'])
        except KeyError as e:
            raise ValueError('Failed to find {} in OpenStudio Standards material '
                             'library.'.format(e))
        materials = []
        for mat_dict in materials_dict:
            if mat_dict['material_type'] == 'StandardOpaqueMaterial':
                materials.append(EnergyMaterial.from_standards_dict(mat_dict))
            elif mat_dict['material_type'] in ('MasslessOpaqueMaterial', 'AirGap'):
                materials.append(EnergyMaterialNoMass.from_standards_dict(mat_dict))
            else:
                raise NotImplementedError(
                    'Material {} is not supported.'.format(mat_dict['material_type']))
        return cls(data['name'], materials)

    @classmethod
    def from_dict(cls, data):
        """Create a OpaqueConstruction from a dictionary.

        Args:
            data: {
                "type": 'EnergyConstructionOpaque',
                "name": 'Generic Brick Wall',
                "materials": []  // list of material objects
                }
        """
        assert data['type'] == 'EnergyConstructionOpaque', \
            'Expected EnergyConstructionOpaque. Got {}.'.format(data['type'])
        materials = []
        for mat in data['materials']:
            if mat['type'] == 'EnergyMaterial':
                materials.append(EnergyMaterial.from_dict(mat))
            elif mat['type'] == 'EnergyMaterialNoMass':
                materials.append(EnergyMaterialNoMass.from_dict(mat))
            else:
                raise NotImplementedError(
                    'Material {} is not supported.'.format(mat['type']))
        return cls(data['name'], materials)

    def to_idf(self):
        """IDF string representation of construction object and materials.

        Returns:
            construction_idf: Text string representation of the construction.
            materials_idf: List of text string representations for each of the
                materials in the construction.
        """
        construction_idf = self._generate_ep_string('opaque', self.name, self.materials)
        materials_idf = []
        material_names = []
        for mat in self.materials:
            if mat.name not in material_names:
                material_names.append(mat.name)
                materials_idf.append(mat.to_idf())
        return construction_idf, materials_idf

    def to_radiance_solar_interior(self, specularity=0.0):
        """Honeybee Radiance material with the interior solar reflectance."""
        return self.materials[-1].to_radiance_solar(specularity)

    def to_radiance_visible_interior(self, specularity=0.0):
        """Honeybee Radiance material with the interior visible reflectance."""
        return self.materials[-1].to_radiance_visible(specularity)

    def to_radiance_solar_exterior(self, specularity=0.0):
        """Honeybee Radiance material with the exterior solar reflectance."""
        return self.materials[0].to_radiance_solar(specularity)

    def to_radiance_visible_exterior(self, specularity=0.0):
        """Honeybee Radiance material with the exterior visible reflectance."""
        return self.materials[0].to_radiance_visible(specularity)

    def to_dict(self):
        """Opaque construction dictionary representation."""
        return {
            'type': 'EnergyConstructionOpaque',
            'name': self.name,
            'materials': [m.to_dict() for m in self.materials]
        }

    @staticmethod
    def extract_all_from_idf_file(idf_file):
        """Extract all OpaqueConstruction objects from an EnergyPlus IDF file.

        Args:
            idf_file: A path to an IDF file containing objects for opaque
                constructions and corresponding materials.

        Returns:
            constructions: A list of all OpaqueConstruction objects in the IDF
                file as honeybee_energy OpaqueConstruction objects.
            materials: A list of all opaque materials in the IDF file as
                honeybee_energy EnergyMaterial objects.
        """
        # check the file
        assert os.path.isfile(idf_file), 'Cannot find an idf file at {}'.format(idf_file)
        with open(idf_file, 'r') as ep_file:
            file_contents = ep_file.read()
        # extract all of the opaque material objects
        mat_pattern1 = re.compile(r"(?i)(Material,[\s\S]*?;)")
        mat_pattern2 = re.compile(r"(?i)(Material:NoMass,[\s\S]*?;)")
        mat_pattern3 = re.compile(r"(?i)(Material:AirGap,[\s\S]*?;)")
        material_str = mat_pattern1.findall(file_contents) + \
            mat_pattern2.findall(file_contents) + mat_pattern3.findall(file_contents)
        materials_dict = OpaqueConstruction._idf_materials_dictionary(material_str)
        materials = list(materials_dict.values())
        # extract all of the construction objects
        constr_pattern = re.compile(r"(?i)(Construction,[\s\S]*?;)")
        constr_props = tuple(OpaqueConstruction._parse_ep_string(ep_string) for
                             ep_string in constr_pattern.findall(file_contents))
        constructions = []
        for constr in constr_props:
            try:
                constr_mats = [materials_dict[mat] for mat in constr[1:]]
                constructions.append(OpaqueConstruction(constr[0], constr_mats))
            except KeyError:
                pass  # the construction is a window construction
        return constructions, materials

    @staticmethod
    def _idf_materials_dictionary(ep_mat_strings):
        """Get a dictionary of opaque EnergyMaterial objects from an IDF string list."""
        materials_dict = {}
        for mat_str in ep_mat_strings:
            mat_str = mat_str.strip()
            if mat_str.startswith('Material:NoMass,'):
                mat_obj = EnergyMaterialNoMass.from_idf(mat_str)
                materials_dict[mat_obj.name] = mat_obj
            elif mat_str.startswith('Material,'):
                mat_obj = EnergyMaterial.from_idf(mat_str)
                materials_dict[mat_obj.name] = mat_obj
        return materials_dict

    def __repr__(self):
        """Represent opaque energy construction."""
        return self._generate_ep_string('opaque', self.name, self.materials)


class WindowConstruction(_ConstructionBase):
    """Window energy construction.

    Properties:
        name
        materials
        r_value
        u_value
        u_factor
        r_factor
        inside_emissivity
        outside_emissivity
        unshaded_solar_transmittance
        unshaded_visible_transmittance
        glazing_count
        gap_count
        has_shade
        shade_location
    """

    @property
    def materials(self):
        """Get or set a list of materials in the construction (outside to inside)."""
        return self._materials

    @materials.setter
    def materials(self, mats):
        """For multi-layer window constructions the following rules apply in E+:
            -The first and last layer must be a solid layer (glass or shade/screen/blind)
            -Adjacent glass layers must be separated by one and only one gas layer
            -Adjacent layers must not be of the same type
            -Only one shade/screen/blind layer is allowed
            -An exterior shade/screen/blind must be the first layer
            -An interior shade/blind must be the last layer
            -An interior screen is not allowed
            -For an exterior shade/screen/blind or interior shade/blind, there should
                not be a gas layer between the shade/screen/blind and adjacent glass
                (we take care of this for shade materials)
            -A between-glass screen is not allowed
            -A between-glass shade/blind is allowed only for double and triple glazing
            -A between-glass shade/blind must have adjacent gas layers of the same type
                and width (we take care of this so the user does not specify the gaps)
            -For triple glazing the between-glass shade/blind must be between the two
                inner glass layers. (currently no check)
            -The slat width of a between-glass blind must be less than the sum of the
                widths of the gas layers adjacent to the blind. (currently no check).
        """
        try:
            if not isinstance(mats, tuple):
                mats = tuple(mats)
        except TypeError:
            raise TypeError('Expected list for construction materials. '
                            'Got {}'.format(type(mats)))
        assert len(mats) > 0, 'Construction must possess at least one material.'
        assert len(mats) <= 8, 'Window construction cannot have more than 8 materials.'
        assert not isinstance(mats[0], _EnergyWindowMaterialGasBase), \
            'Window construction cannot have gas gap layers on the outside layer.'
        assert not isinstance(mats[-1], _EnergyWindowMaterialGasBase), \
            'Window construction cannot have gas gap layers on the inside layer.'
        glazing_layer = False
        self._has_shade = False
        for i, mat in enumerate(mats):
            assert isinstance(mat, _EnergyMaterialWindowBase), 'Expected window energy' \
                ' material for construction. Got {}.'.format(type(mat))
            if isinstance(mat, EnergyWindowMaterialSimpleGlazSys):
                assert len(mats) == 1, 'Only one material layer is allowed when using' \
                    ' EnergyWindowMaterialSimpleGlazSys'
            elif isinstance(mat, _EnergyWindowMaterialGasBase):
                assert glazing_layer, 'Gas layer must be adjacent to a glazing layer.'
                glazing_layer = False
            elif isinstance(mat, _EnergyWindowMaterialGlazingBase):
                assert not glazing_layer, 'Two adjacent glazing layers are not allowed.'
                glazing_layer = True
            else:  # must be a shade material
                if i != 0:
                    assert glazing_layer, \
                        'Shade layer must be adjacent to a glazing layer.'
                assert not self._has_shade, 'Constructions can only possess one shade.'
                glazing_layer = False
                self._has_shade = True
        self._materials = mats

    @property
    def r_factor(self):
        """Construction R-factor [m2-K/W] (including standard resistances for air films).

        Formulas for film coefficients come from EN673 / ISO10292.
        """
        gap_count = self.gap_count
        if gap_count == 0:  # single pane or simple glazing system
            return self.materials[0].r_value + (1 / self.out_h_simple()) + \
                (1 / self.in_h_simple())
        r_vals, emissivities = self._layered_r_value_initial(gap_count)
        r_vals = self._solve_r_values(r_vals, emissivities)
        return sum(r_vals)

    @property
    def r_value(self):
        """R-value of the construction [m2-K/W] (excluding air films).

        Note that shade materials are currently considered impermeable to air within
        the U-value calculation.
        """
        gap_count = self.gap_count
        if gap_count == 0:  # single pane or simple glazing system
            return self.materials[0].r_value
        r_vals, emissivities = self._layered_r_value_initial(gap_count)
        r_vals = self._solve_r_values(r_vals, emissivities)
        return sum(r_vals[1:-1])

    @property
    def inside_emissivity(self):
        """"The emissivity of the inside face of the construction."""
        if isinstance(self.materials[0], EnergyWindowMaterialSimpleGlazSys):
            return 0.84
        try:
            return self.materials[-1].emissivity_back
        except AttributeError:
            return self.materials[-1].emissivity

    @property
    def outside_emissivity(self):
        """"The emissivity of the outside face of the construction."""
        if isinstance(self.materials[0], EnergyWindowMaterialSimpleGlazSys):
            return 0.84
        return self.materials[0].emissivity

    @property
    def unshaded_solar_transmittance(self):
        """The unshaded solar transmittance of the window at normal incidence.

        Note that 'unshaded' means that all shade materials in the construction
        are ignored.
        """
        if isinstance(self.materials[0], EnergyWindowMaterialSimpleGlazSys):
            # E+ interprets ~80% of solar heat gain from direct solar transmission
            return self.materials[0].shgc * 0.8
        trans = 1
        for mat in self.materials:
            if isinstance(mat, _EnergyWindowMaterialGlazingBase):
                trans *= mat.solar_transmittance
        return trans

    @property
    def unshaded_visible_transmittance(self):
        """The unshaded visible transmittance of the window at normal incidence.

        Note that 'unshaded' means that all shade materials in the construction
        are ignored.
        """
        if isinstance(self.materials[0], EnergyWindowMaterialSimpleGlazSys):
            return self.materials[0].vt
        trans = 1
        for mat in self.materials:
            if isinstance(mat, _EnergyWindowMaterialGlazingBase):
                trans *= mat.visible_transmittance
        return trans

    @property
    def thickness(self):
        """Thickness of the construction [m]."""
        thickness = 0
        for mat in self.materials:
            if isinstance(mat, (EnergyWindowMaterialGlazing, EnergyWindowMaterialShade,
                                _EnergyWindowMaterialGasBase)):
                thickness += mat.thickness
            elif isinstance(mat, EnergyWindowMaterialBlind):
                thickness += mat.slat_width
        return thickness

    @property
    def glazing_count(self):
        """The number of glazing materials contained within the window construction."""
        count = 0
        for mat in self.materials:
            if isinstance(mat, _EnergyWindowMaterialGlazingBase):
                count += 1
        return count

    @property
    def gap_count(self):
        """The number of gas gaps contained within the window construction.

        Note that this property will count the distance between shades and glass
        as a gap in addition to any gas layers.
        """
        count = 0
        for i, mat in enumerate(self.materials):
            if isinstance(mat, _EnergyWindowMaterialGasBase):
                count += 1
            elif isinstance(mat, _EnergyWindowMaterialShadeBase):
                if i == 0 or count == len(self.materials) - 1:
                    count += 1
                else:
                    count += 2
        return count

    @property
    def has_shade(self):
        """Boolean noting whether there is a shade or blind in the construction."""
        return self._has_shade

    @property
    def shade_location(self):
        """Text noting the location of shade in the construction.

        This will be one of the following: ('Interior', 'Exterior', 'Between', None).
        None indicates that there is no shade within the construction.
        """
        if isinstance(self.materials[0], _EnergyWindowMaterialShadeBase):
            return 'Exterior'
        elif isinstance(self.materials[-1], _EnergyWindowMaterialShadeBase):
            return 'Interior'
        elif self.has_shade:
            return 'Between'
        else:
            return None

    def temperature_profile(self, outside_temperature=-18, inside_temperature=21,
                            wind_speed=6.7, height=1.0, angle=90.0, pressure=101325):
        """Get a list of temperatures at each material boundary across the construction.

        Args:
            outside_temperature: The temperature on the outside of the construction [C].
                Default is -18, which is consistent with NFRC 100-2010.
            inside_temperature: The temperature on the inside of the construction [C].
                Default is 21, which is consistent with NFRC 100-2010.
            wind_speed: The average outdoor wind speed [m/s]. This affects outdoor
                convective heat transfer coefficient. Default is 6.7 m/s.
            height: An optional height for the surface in meters. Default is 1.0 m.
            angle: An angle in degrees between 0 and 180.
                0 = A horizontal surface with the outside boundary on the bottom.
                90 = A vertical surface
                180 = A horizontal surface with the outside boundary on the top.
            pressure: The average pressure of in Pa.
                Default is 101325 Pa for standard pressure at sea level.

        Returns:
            temperatures: A list of temperature values [C].
                The first value will always be the outside temperature and the
                second will be the exterior surface temperature.
                The last value will always be the inside temperature and the second
                to last will be the interior surface temperature.
            r_values: A list of R-values for each of the material layers [m2-K/W].
                The first value will always be the resistance of the exterior air
                and the last value is the resistance of the interior air.
                The sum of this list is the R-factor for this construction given
                the input parameters.
        """
        if angle != 90 and outside_temperature > inside_temperature:
            angle = abs(180 - angle)
        gap_count = self.gap_count
        if gap_count == 0:  # single pane or simple glazing system
            in_r_init = 1 / self.in_h_simple()
            r_values = [1 / self.out_h(wind_speed, outside_temperature + 273.15),
                        self.materials[0].r_value, in_r_init]
            in_delta_t = (in_r_init / sum(r_values)) * \
                (outside_temperature - inside_temperature)
            r_values[-1] = 1 / self.in_h(inside_temperature - (in_delta_t / 2) + 273.15,
                                         in_delta_t, height, angle, pressure)
            temperatures = self._temperature_profile_from_r_values(
                r_values, outside_temperature, inside_temperature)
            return temperatures, r_values
        # multi-layered window construction
        guess = abs(inside_temperature - outside_temperature) / 2
        guess = 1 if guess < 1 else guess  # prevents zero division with gas conductance
        avg_guess = ((inside_temperature + outside_temperature) / 2) + 273.15
        r_values, emissivities = self._layered_r_value_initial(
            gap_count, guess, avg_guess, wind_speed)
        r_last = 0
        r_next = sum(r_values)
        while abs(r_next - r_last) > 0.001:  # 0.001 is the r-value tolerance
            r_last = sum(r_values)
            temperatures = self._temperature_profile_from_r_values(
                r_values, outside_temperature, inside_temperature)
            r_values = self._layered_r_value(
                temperatures, r_values, emissivities, height, angle, pressure)
            r_next = sum(r_values)
        temperatures = self._temperature_profile_from_r_values(
            r_values, outside_temperature, inside_temperature)
        return temperatures, r_values

    @classmethod
    def from_idf(cls, ep_string, ep_mat_strings):
        """Create an WindowConstruction from an EnergyPlus text string.

        Args:
            ep_string: A text string fully describing an EnergyPlus construction.
            ep_mat_strings: A list of text strings for each of the materials in
                the construction.
        """
        materials_dict = cls._idf_materials_dictionary(ep_mat_strings)
        ep_strs = cls._parse_ep_string(ep_string)
        materials = [materials_dict[mat] for mat in ep_strs[1:]]
        return cls(ep_strs[0], materials)

    @classmethod
    def from_standards_dict(cls, data, data_materials):
        """Create a WindowConstruction from an OpenStudio standards gem dictionary.

        Args:
            data: {
                "name": "ASHRAE 189.1-2009 ExtWindow ClimateZone 4-5",
                "intended_surface_type": "ExteriorWindow",
                "materials": ["Theoretical Glass [207]"]
                }
            data_materials: Dictionary representation of all materials in the
                OpenStudio standards gem.
        """
        try:
            materials_dict = tuple(data_materials[mat] for mat in data['materials'])
        except KeyError as e:
            raise ValueError('Failed to find {} in OpenStudio Standards material '
                             'library.'.format(e))
        materials = []
        for mat_dict in materials_dict:
            if mat_dict['material_type'] == 'SimpleGlazing':
                materials.append(
                    EnergyWindowMaterialSimpleGlazSys.from_standards_dict(mat_dict))
            elif mat_dict['material_type'] == 'StandardGlazing':
                materials.append(
                    EnergyWindowMaterialGlazing.from_standards_dict(mat_dict))
            elif mat_dict['material_type'] == 'Gas':
                materials.append(EnergyWindowMaterialGas.from_standards_dict(mat_dict))
            else:
                raise NotImplementedError(
                    'Material {} is not supported.'.format(mat_dict['material_type']))
        return cls(data['name'], materials)

    @classmethod
    def from_dict(cls, data):
        """Create a WindowConstruction from a dictionary.

        Args:
            data: {
                "type": 'EnergyConstructionWindow',
                "name": 'Generic Double Pane Window',
                "materials": []  // list of material objects
                }
        """
        assert data['type'] == 'EnergyConstructionWindow', \
            'Expected EnergyConstructionWindow. Got {}.'.format(data['type'])
        materials = []
        for mat in data['materials']:
            if mat['type'] == 'EnergyWindowMaterialSimpleGlazSys':
                materials.append(EnergyWindowMaterialSimpleGlazSys.from_dict(mat))
            elif mat['type'] == 'EnergyWindowMaterialGlazing':
                materials.append(EnergyWindowMaterialGlazing.from_dict(mat))
            elif mat['type'] == 'EnergyWindowMaterialGas':
                materials.append(EnergyWindowMaterialGas.from_dict(mat))
            elif mat['type'] == 'EnergyWindowMaterialGasMixture':
                materials.append(EnergyWindowMaterialGasMixture.from_dict(mat))
            elif mat['type'] == 'EnergyWindowMaterialGasCustom':
                materials.append(EnergyWindowMaterialGasCustom.from_dict(mat))
            elif mat['type'] == 'EnergyWindowMaterialShade':
                materials.append(EnergyWindowMaterialShade.from_dict(mat))
            elif mat['type'] == 'EnergyWindowMaterialBlind':
                materials.append(EnergyWindowMaterialBlind.from_dict(mat))
            else:
                raise NotImplementedError(
                    'Material {} is not supported.'.format(mat['type']))
        return cls(data['name'], materials)

    def to_idf(self):
        """IDF string representation of construction object and materials.

        Returns:
            construction_idf: Text string representation of the construction.
            materials_idf: Tuple of text string representations for each of the
                materials in the construction.
        """
        construction_idf = self._generate_ep_string('window', self.name, self.materials)
        materials_idf = []
        material_names = []
        for mat in self.materials:
            if mat.name not in material_names:
                material_names.append(mat.name)
                materials_idf.append(mat.to_idf())
        return construction_idf, materials_idf

    def to_radiance_solar(self):
        """Honeybee Radiance material with the solar transmittance."""
        try:
            from honeybee_radiance.primitive.material.glass import Glass
            from honeybee_radiance.primitive.material.trans import Trans
        except ImportError as e:
            raise ImportError('honeybee_radiance library must be installed to use '
                              'to_radiance_solar() method. {}'.format(e))
        diffusing = False
        trans = 1
        for mat in self.materials:
            if isinstance(mat, EnergyWindowMaterialSimpleGlazSys):
                trans *= mat.shgc * 0.8
            elif isinstance(mat, EnergyWindowMaterialGlazing):
                trans *= mat.solar_transmittance
                diffusing = True if mat.solar_diffusing is True else False
            elif isinstance(mat, EnergyWindowMaterialShade):
                trans *= mat.solar_transmittance
                diffusing = True
            elif isinstance(mat, EnergyWindowMaterialBlind):
                raise NotImplementedError('to_radiance_solar() is not supported for '
                                          'window constructions with blind materials.')
        if diffusing is False:
            return Glass.from_single_transmittance(self.name, trans)
        else:
            try:
                ref = self.materials[-1].solar_reflectance_back
            except AttributeError:
                ref = self.materials[-1].solar_reflectance
            return Trans.from_single_reflectance(self.name, rgb_reflectance=ref,
                                                 transmitted_diff=trans,
                                                 transmitted_spec=0)

    def to_radiance_visible(self, specularity=0.0):
        """Honeybee Radiance material with the visible transmittance."""
        try:
            from honeybee_radiance.primitive.material.glass import Glass
            from honeybee_radiance.primitive.material.trans import Trans
        except ImportError as e:
            raise ImportError('honeybee_radiance library must be installed to use '
                              'to_radiance_visible() method. {}'.format(e))
        diffusing = False
        trans = 1
        for mat in self.materials:
            if isinstance(mat, EnergyWindowMaterialSimpleGlazSys):
                trans *= mat.vt
            elif isinstance(mat, EnergyWindowMaterialGlazing):
                trans *= mat.visible_transmittance
                diffusing = True if mat.solar_diffusing is True else False
            elif isinstance(mat, EnergyWindowMaterialShade):
                trans *= mat.visible_transmittance
                diffusing = True
            elif isinstance(mat, EnergyWindowMaterialBlind):
                raise NotImplementedError('to_radiance_visible() is not supported for '
                                          'window constructions with blind materials.')
        if diffusing is False:
            return Glass.from_single_transmittance(self.name, trans)
        else:
            try:
                ref = self.materials[-1].solar_reflectance_back
            except AttributeError:
                ref = self.materials[-1].solar_reflectance
            return Trans.from_single_reflectance(self.name, rgb_reflectance=ref,
                                                 transmitted_diff=trans,
                                                 transmitted_spec=0)

    def to_dict(self):
        """Window construction dictionary representation."""
        return {
            'type': 'EnergyConstructionWindow',
            'name': self.name,
            'materials': [m.to_dict() for m in self.materials]
        }

    @staticmethod
    def extract_all_from_idf_file(idf_file):
        """Get all WindowConstruction objects in an EnergyPlus IDF file.

        Args:
            idf_file: A path to an IDF file containing objects for window
                constructions and corresponding materials. For example, the
                IDF Report output by LBNL WINDOW.
        """
        # check the file
        assert os.path.isfile(idf_file), 'Cannot find an idf file at {}'.format(idf_file)
        with open(idf_file, 'r') as ep_file:
            file_contents = ep_file.read()
        # extract all material objects
        mat_pattern = re.compile(r"(?i)(WindowMaterial:[\s\S]*?;)")
        material_str = mat_pattern.findall(file_contents)
        materials_dict = WindowConstruction._idf_materials_dictionary(material_str)
        materials = list(materials_dict.values())
        # extract all of the construction objects
        constr_pattern = re.compile(r"(?i)(Construction,[\s\S]*?;)")
        constr_props = tuple(WindowConstruction._parse_ep_string(ep_string) for
                             ep_string in constr_pattern.findall(file_contents))
        constructions = []
        for constr in constr_props:
            try:
                constr_mats = [materials_dict[mat] for mat in constr[1:]]
                constructions.append(WindowConstruction(constr[0], constr_mats))
            except KeyError:
                pass  # the construction is an opaque construction
        return constructions, materials

    @staticmethod
    def _idf_materials_dictionary(ep_mat_strings):
        """Get a dictionary of window EnergyMaterial objects from an IDF string list."""
        materials_dict = {}
        for mat_str in ep_mat_strings:
            mat_str = mat_str.strip()
            mat_obj = None
            if mat_str.startswith('WindowMaterial:SimpleGlazingSystem,'):
                mat_obj = EnergyWindowMaterialSimpleGlazSys.from_idf(mat_str)
            elif mat_str.startswith('WindowMaterial:Glazing,'):
                mat_obj = EnergyWindowMaterialGlazing.from_idf(mat_str)
            elif mat_str.startswith('WindowMaterial:Gas,'):
                mat_obj = EnergyWindowMaterialGas.from_idf(mat_str)
            elif mat_str.startswith('WindowMaterial:GasMixture,'):
                mat_obj = EnergyWindowMaterialGasMixture.from_idf(mat_str)
            elif mat_str.startswith('WindowMaterial:Shade,'):
                mat_obj = EnergyWindowMaterialShade.from_idf(mat_str)
            elif mat_str.startswith('WindowMaterial:Blind,'):
                mat_obj = EnergyWindowMaterialBlind.from_idf(mat_str)
            if mat_obj is not None:
                materials_dict[mat_obj.name] = mat_obj
        return materials_dict

    def _solve_r_values(self, r_vals, emissivities):
        """Iteratively solve for R-values."""
        r_last = 0
        r_next = sum(r_vals)
        while abs(r_next - r_last) > 0.001:  # 0.001 is the r-value tolerance
            r_last = sum(r_vals)
            temperatures = self._temperature_profile_from_r_values(r_vals)
            r_vals = self._layered_r_value(temperatures, r_vals, emissivities)
            r_next = sum(r_vals)
        return r_vals

    def _layered_r_value_initial(self, gap_count, delta_t_guess=15,
                                 avg_t_guess=273.15, wind_speed=6.7):
        """Compute initial r-values of each layer within a layered construction."""
        r_vals = [1 / self.out_h(wind_speed, avg_t_guess - delta_t_guess)]
        emiss = []
        delta_t = delta_t_guess / gap_count
        for i, mat in enumerate(self.materials):
            if isinstance(mat, _EnergyWindowMaterialGlazingBase):
                r_vals.append(mat.r_value)
                emiss.append(None)
            elif isinstance(mat, _EnergyWindowMaterialGasBase):
                e_front = self.materials[i + 1].emissivity
                try:
                    e_back = self.materials[i - 1].emissivity_back
                except AttributeError:
                    e_back = self.materials[i - 1].emissivity
                r_vals.append(1 / mat.u_value(
                    delta_t, e_back, e_front, t_kelvin=avg_t_guess))
                emiss.append((e_back, e_front))
            else:  # shade material
                if i == 0:
                    e_back = self.materials[i + 1].emissivity
                    r_vals.append(mat.r_value_exterior(
                        delta_t, e_back, t_kelvin=avg_t_guess))
                    emiss.append(e_back)
                elif i == len(self.materials) - 1:
                    e_front = self.materials[i - 1].emissivity_back
                    r_vals.append(mat.r_value_interior(
                        delta_t, e_front, t_kelvin=avg_t_guess))
                    emiss.append(e_front)
                else:
                    e_back = self.materials[i + 1].emissivity
                    e_front = self.materials[i - 1].emissivity_back
                    r_vals.append(mat.r_value_between(
                        delta_t, e_back, e_front, t_kelvin=avg_t_guess))
                    emiss.append((e_back, e_front))
        r_vals.append(1 / self.in_h_simple())
        return r_vals, emiss

    def _layered_r_value(self, temperatures, r_values_init, emiss,
                         height=1.0, angle=90.0, pressure=101325):
        """Compute delta_t adjusted r-values of each layer within a construction."""
        r_vals = [r_values_init[0]]
        for i, mat in enumerate(self.materials):
            if isinstance(mat, _EnergyWindowMaterialGlazingBase):
                r_vals.append(r_values_init[i + 1])
            elif isinstance(mat, _EnergyWindowMaterialGasBase):
                delta_t = abs(temperatures[i + 1] - temperatures[i + 2])
                avg_temp = ((temperatures[i + 1] + temperatures[i + 2]) / 2) + 273.15
                r_vals.append(1 / mat.u_value_at_angle(
                    delta_t, emiss[i][0], emiss[i][1], height, angle,
                    avg_temp, pressure))
            else:  # shade material
                delta_t = abs(temperatures[i + 1] - temperatures[i + 2])
                avg_temp = ((temperatures[i + 1] + temperatures[i + 2]) / 2) + 273.15
                if i == 0:
                    r_vals.append(mat.r_value_exterior(
                        delta_t, emiss[i], height, angle, avg_temp, pressure))
                elif i == len(self.materials) - 1:
                    r_vals.append(mat.r_value_interior(
                        delta_t, emiss[i], height, angle, avg_temp, pressure))
                else:
                    r_vals.append(mat.r_value_between(
                        delta_t, emiss[i][0], emiss[i][1],
                        height, angle, avg_temp, pressure))
        delta_t = abs(temperatures[-1] - temperatures[-2])
        avg_temp = ((temperatures[-1] + temperatures[-2]) / 2) + 273.15
        r_vals.append(1 / self.in_h(avg_temp, delta_t, height, angle, pressure))
        return r_vals

    def __repr__(self):
        """Represent window energy construction."""
        return self._generate_ep_string('window', self.name, self.materials)
