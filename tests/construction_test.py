# coding=utf-8
from honeybee_energy.material.opaque import EnergyMaterial, EnergyMaterialNoMass
from honeybee_energy.material.glazing import EnergyWindowMaterialGlazing
from honeybee_energy.material.gas import EnergyWindowMaterialGas, \
    EnergyWindowMaterialGasMixture
from honeybee_energy.material.shade import EnergyWindowMaterialShade, \
    EnergyWindowMaterialBlind
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.construction.window import WindowConstruction
from honeybee_energy.construction.shade import ShadeConstruction

import pytest
import json


def test_opaque_construction_init():
    """Test the initalization of OpaqueConstruction objects and basic properties."""
    concrete = EnergyMaterial('Concrete', 0.15, 2.31, 2322, 832, 'MediumRough',
                              0.95, 0.75, 0.8)
    insulation = EnergyMaterialNoMass('Insulation R-3', 3, 'MediumSmooth')
    wall_gap = EnergyMaterial('Wall Air Gap', 0.1, 0.67, 1.2925, 1006.1)
    gypsum = EnergyMaterial('Gypsum', 0.0127, 0.16, 784.9, 830, 'MediumRough',
                            0.93, 0.6, 0.65)
    wall_constr = OpaqueConstruction(
        'Generic Wall Construction', [concrete, insulation, wall_gap, gypsum])
    str(wall_constr)  # test the string representation of the construction
    constr_dup = wall_constr.duplicate()

    assert wall_constr.name == constr_dup.name == 'Generic Wall Construction'
    assert len(wall_constr.materials) == len(constr_dup.materials) == 4
    assert wall_constr.r_value == constr_dup.r_value == \
        pytest.approx(3.29356, rel=1e-2)
    assert wall_constr.u_value == constr_dup.u_value == \
        pytest.approx(0.30362, rel=1e-2)
    assert wall_constr.u_factor == constr_dup.u_factor == \
        pytest.approx(0.2894284, rel=1e-2)
    assert wall_constr.r_factor == constr_dup.r_factor == \
        pytest.approx(3.4550859, rel=1e-2)
    assert wall_constr.mass_area_density == constr_dup.mass_area_density == \
        pytest.approx(358.397, rel=1e-2)
    assert wall_constr.area_heat_capacity == constr_dup.area_heat_capacity == \
        pytest.approx(298189.26, rel=1e-2)
    assert wall_constr.inside_emissivity == constr_dup.inside_emissivity == 0.93
    assert wall_constr.inside_solar_reflectance == \
        constr_dup.inside_solar_reflectance == 0.4
    assert wall_constr.inside_visible_reflectance == \
        constr_dup.inside_visible_reflectance == 0.35
    assert wall_constr.outside_emissivity == \
        constr_dup.outside_emissivity == 0.95
    assert wall_constr.outside_solar_reflectance == \
        constr_dup.outside_solar_reflectance == 0.25
    assert wall_constr.outside_visible_reflectance == \
        constr_dup.outside_visible_reflectance == pytest.approx(0.2, rel=1e-2)


def test_opaque_lockability():
    """Test the lockability of the construction."""
    concrete = EnergyMaterial('Concrete', 0.15, 2.31, 2322, 832, 'MediumRough',
                              0.95, 0.75, 0.8)
    insulation = EnergyMaterialNoMass('Insulation R-3', 3, 'MediumSmooth')
    wall_gap = EnergyMaterial('Wall Air Gap', 0.1, 0.67, 1.2925, 1006.1)
    gypsum = EnergyMaterial('Gypsum', 0.0127, 0.16, 784.9, 830, 'MediumRough',
                            0.93, 0.6, 0.65)
    wall_constr = OpaqueConstruction(
        'Generic Wall Construction', [concrete, insulation, wall_gap, gypsum])

    wall_constr.materials = [concrete, wall_gap, gypsum]
    wall_constr.lock()
    with pytest.raises(AttributeError):
        wall_constr.materials = [concrete, insulation, wall_gap, gypsum]
    with pytest.raises(AttributeError):
        wall_constr[0].density = 600
    wall_constr.unlock()
    wall_constr.materials = [concrete, insulation, wall_gap, gypsum]
    wall_constr[0].density = 600


def test_opaque_equivalency():
    """Test the equality of an opaque construction to another."""
    concrete = EnergyMaterial('Concrete', 0.15, 2.31, 2322, 832)
    insulation = EnergyMaterial('Insulation', 0.05, 0.049, 265, 836)
    wall_gap = EnergyMaterial('Wall Air Gap', 0.1, 0.67, 1.2925, 1006.1)
    gypsum = EnergyMaterial('Gypsum', 0.0127, 0.16, 784.9, 830)
    wall_constr_1 = OpaqueConstruction(
        'Wall Construction', [concrete, insulation, wall_gap, gypsum])
    wall_constr_2 = wall_constr_1.duplicate()
    wall_constr_3 = OpaqueConstruction(
        'Wall Construction', [concrete, wall_gap, gypsum, insulation])
    wall_constr_4 = OpaqueConstruction(
        'Other Wall Construction', [concrete, insulation, wall_gap, gypsum])

    collection = [wall_constr_1, wall_constr_1, wall_constr_2, wall_constr_3]
    assert len(set(collection)) == 2
    assert wall_constr_1 == wall_constr_2
    assert wall_constr_1 != wall_constr_3
    assert wall_constr_1 != wall_constr_4

    wall_constr_2.name = 'Roof Construction'
    assert wall_constr_1 != wall_constr_2


def test_opaque_symmetric():
    """Test that the opaque construction is_symmetric property."""
    concrete = EnergyMaterial('Concrete', 0.15, 2.31, 2322, 832)
    insulation = EnergyMaterial('Insulation', 0.05, 0.049, 265, 836)
    wall_gap = EnergyMaterial('Wall Air Gap', 0.1, 0.67, 1.2925, 1006.1)
    gypsum = EnergyMaterial('Gypsum', 0.0127, 0.16, 784.9, 830)
    wall_constr_1 = OpaqueConstruction(
        'Wall Construction', [concrete, insulation, wall_gap, gypsum])
    wall_constr_2 = OpaqueConstruction(
        'Wall Construction', [gypsum, wall_gap, gypsum])
    wall_constr_3 = OpaqueConstruction(
        'Wall Construction', [concrete])
    wall_constr_4 = OpaqueConstruction(
        'Wall Construction', [concrete, concrete])
    wall_constr_5 = OpaqueConstruction(
        'Other Wall Construction', [concrete, insulation, wall_gap, insulation, concrete])

    assert not wall_constr_1.is_symmetric
    assert wall_constr_2.is_symmetric
    assert wall_constr_3.is_symmetric
    assert wall_constr_4.is_symmetric
    assert wall_constr_5.is_symmetric


def test_opaque_temperature_profile():
    """Test the opaque construction temperature profile."""
    concrete = EnergyMaterial('Concrete', 0.15, 2.31, 2322, 832)
    insulation = EnergyMaterial('Insulation', 0.05, 0.049, 265, 836)
    wall_gap = EnergyMaterial('Wall Air Gap', 0.1, 0.67, 1.2925, 1006.1)
    gypsum = EnergyMaterial('Gypsum', 0.0127, 0.16, 784.9, 830)
    wall_constr = OpaqueConstruction(
        'Wall Construction', [concrete, insulation, wall_gap, gypsum])

    temperatures, r_values = wall_constr.temperature_profile(-18, 21)
    assert len(temperatures) == 7
    assert temperatures[0] == pytest.approx(-18, rel=1e-2)
    assert temperatures[-1] == pytest.approx(21, rel=1e-2)
    assert len(r_values) == 6
    assert sum(r_values) == pytest.approx(wall_constr.r_factor, rel=1e-1)
    assert r_values[-1] == pytest.approx((1 / wall_constr.in_h_simple()), rel=1)
    for i, mat in enumerate(wall_constr.materials):
        assert mat.r_value == pytest.approx(r_values[i + 1])

    temperatures, r_values = wall_constr.temperature_profile(
        36, 21, 4, 2., 180.0, 100000)
    assert len(temperatures) == 7
    assert temperatures[0] == pytest.approx(36, rel=1e-2)
    assert temperatures[-1] == pytest.approx(21, rel=1e-2)
    assert len(r_values) == 6


def test_opaque_construction_from_idf():
    """Test the OpaqueConstruction to/from idf methods."""
    concrete = EnergyMaterial('Concrete', 0.15, 2.31, 2322, 832)
    insulation = EnergyMaterial('Insulation', 0.05, 0.049, 265, 836)
    wall_gap = EnergyMaterial('Wall Air Gap', 0.1, 0.67, 1.2925, 1006.1)
    gypsum = EnergyMaterial('Gypsum', 0.0127, 0.16, 784.9, 830)
    wall_constr = OpaqueConstruction(
        'Wall Construction', [concrete, insulation, wall_gap, gypsum])
    constr_str = wall_constr.to_idf()
    mat_str = [mat.to_idf() for mat in wall_constr.unique_materials]
    new_wall_constr = OpaqueConstruction.from_idf(constr_str, mat_str)
    new_constr_str = new_wall_constr.to_idf()

    assert wall_constr.r_value == new_wall_constr.r_value
    assert wall_constr.r_factor == new_wall_constr.r_factor
    assert wall_constr.thickness == new_wall_constr.thickness
    assert constr_str == new_constr_str


def test_opaque_dict_methods():
    """Test the to/from dict methods."""
    concrete = EnergyMaterial('Concrete', 0.15, 2.31, 2322, 832)
    insulation = EnergyMaterial('Insulation', 0.05, 0.049, 265, 836)
    wall_gap = EnergyMaterial('Wall Air Gap', 0.1, 0.67, 1.2925, 1006.1)
    gypsum = EnergyMaterial('Gypsum', 0.0127, 0.16, 784.9, 830)
    wall_constr = OpaqueConstruction(
        'Wall Construction', [concrete, insulation, wall_gap, gypsum])
    constr_dict = wall_constr.to_dict()
    new_constr = OpaqueConstruction.from_dict(constr_dict)
    assert constr_dict == new_constr.to_dict()


def test_window_construction_init():
    """Test the initalization of WindowConstruction objects and basic properties."""
    lowe_glass = EnergyWindowMaterialGlazing(
        'Low-e Glass', 0.00318, 0.4517, 0.359, 0.714, 0.207,
        0, 0.84, 0.046578, 1.0)
    clear_glass = EnergyWindowMaterialGlazing(
        'Clear Glass', 0.005715, 0.770675, 0.07, 0.8836, 0.0804,
        0, 0.84, 0.84, 1.0)
    gap = EnergyWindowMaterialGas('air gap', thickness=0.0127)
    double_low_e = WindowConstruction(
        'Double Low-E Window', [lowe_glass, gap, clear_glass])
    double_clear = WindowConstruction(
        'Double Clear Window', [clear_glass, gap, clear_glass])
    triple_clear = WindowConstruction(
        'Triple Clear Window', [clear_glass, gap, clear_glass, gap, clear_glass])
    double_low_e_dup = double_low_e.duplicate()
    str(double_low_e)  # test the string representation of the construction

    assert double_low_e.name == double_low_e_dup.name == 'Double Low-E Window'
    assert len(double_low_e.materials) == len(double_low_e_dup.materials) == 3
    assert double_low_e.r_value == double_low_e_dup.r_value == \
        pytest.approx(0.41984, rel=1e-2)
    assert double_low_e.u_value == double_low_e_dup.u_value == \
        pytest.approx(2.3818, rel=1e-2)
    assert double_low_e.u_factor == double_low_e_dup.u_factor == \
        pytest.approx(1.69802, rel=1e-2)
    assert double_low_e.r_factor == double_low_e_dup.r_factor == \
        pytest.approx(0.588919, rel=1e-2)
    assert double_low_e.inside_emissivity == \
        double_low_e_dup.inside_emissivity == 0.84
    assert double_low_e.outside_emissivity == \
        double_low_e_dup.outside_emissivity == 0.84
    assert double_low_e.unshaded_solar_transmittance == \
        double_low_e_dup.unshaded_solar_transmittance == 0.4517 * 0.770675
    assert double_low_e.unshaded_visible_transmittance == \
        double_low_e_dup.unshaded_visible_transmittance == 0.714 * 0.8836
    assert double_low_e.glazing_count == double_low_e_dup.glazing_count == 2
    assert double_low_e.gap_count == double_low_e_dup.gap_count == 1
    assert double_low_e.has_shade is double_low_e_dup.has_shade is False
    assert double_low_e.shade_location is double_low_e_dup.shade_location is None

    assert double_clear.u_factor == pytest.approx(2.72, rel=1e-2)
    assert double_low_e.u_factor == pytest.approx(1.698, rel=1e-2)
    assert triple_clear.u_factor == pytest.approx(1.757, rel=1e-2)


def test_window_lockability():
    """Test the lockability of the window construction."""
    clear_glass = EnergyWindowMaterialGlazing(
        'Clear Glass', 0.005715, 0.770675, 0.07, 0.8836, 0.0804,
        0, 0.84, 0.84, 1.0)
    gap = EnergyWindowMaterialGas('air gap', thickness=0.0127)
    double_clear = WindowConstruction(
        'Double Clear Window', [clear_glass, gap, clear_glass])

    double_clear.materials = [clear_glass, gap, clear_glass, gap, clear_glass]
    double_clear.lock()
    with pytest.raises(AttributeError):
        double_clear.materials = [clear_glass]
    with pytest.raises(AttributeError):
        double_clear[0].solar_transmittance = 0.45
    double_clear.unlock()
    double_clear.materials = [clear_glass]
    double_clear[0].solar_transmittance = 0.45


def test_window_equivalency():
    """Test the equality of a window construction to another."""
    clear_glass = EnergyWindowMaterialGlazing(
        'Clear Glass', 0.005715, 0.770675, 0.07, 0.8836, 0.0804,
        0, 0.84, 0.84, 1.0)
    gap = EnergyWindowMaterialGas('air gap', thickness=0.0127)
    double_clear = WindowConstruction(
        'Clear Window', [clear_glass, gap, clear_glass])
    double_clear_2 = double_clear.duplicate()
    triple_clear = WindowConstruction(
        'Clear Window', [clear_glass, gap, clear_glass, gap, clear_glass])
    double_clear_3 = WindowConstruction(
        'Double Clear Window', [clear_glass, gap, clear_glass])

    collection = [double_clear, double_clear, double_clear_2, triple_clear]
    assert len(set(collection)) == 2
    assert double_clear == double_clear_2
    assert double_clear != triple_clear
    assert double_clear != double_clear_3

    double_clear_2.name = 'Cool Window'
    assert double_clear != double_clear_2


def test_window_symmetric():
    """Test that the window construction is_symmetric property."""
    clear_glass = EnergyWindowMaterialGlazing(
        'Clear Glass', 0.005715, 0.770675, 0.07, 0.8836, 0.0804,
        0, 0.84, 0.84, 1.0)
    low_e_glass = EnergyWindowMaterialGlazing(
        'Clear Glass', 0.005715, 0.770675, 0.07, 0.8836, 0.0804,
        0, 0.84, 0.05, 1.0)
    gap = EnergyWindowMaterialGas('air gap', thickness=0.0127)
    double_low_e = WindowConstruction(
        'Double Clear Window', [clear_glass, gap, low_e_glass])
    double_clear = WindowConstruction(
        'Clear Window', [clear_glass, gap, clear_glass])
    single_clear = WindowConstruction(
        'Clear Window', [clear_glass])
    triple_clear = WindowConstruction(
        'Clear Window', [clear_glass, gap, clear_glass, gap, clear_glass])

    assert not double_low_e.is_symmetric
    assert double_clear.is_symmetric
    assert single_clear.is_symmetric
    assert triple_clear.is_symmetric


def test_window_construction_init_shade():
    """Test the initalization of WindowConstruction objects with shades."""
    lowe_glass = EnergyWindowMaterialGlazing(
        'Low-e Glass', 0.00318, 0.4517, 0.359, 0.714, 0.207,
        0, 0.84, 0.046578, 1.0)
    clear_glass = EnergyWindowMaterialGlazing(
        'Clear Glass', 0.005715, 0.770675, 0.07, 0.8836, 0.0804,
        0, 0.84, 0.84, 1.0)
    gap = EnergyWindowMaterialGas('air gap', thickness=0.0127)
    shade_mat = EnergyWindowMaterialShade(
        'Low-e Diffusing Shade', 0.025, 0.15, 0.5, 0.25, 0.5, 0, 0.4,
        0.2, 0.1, 0.75, 0.25)
    double_low_e_shade = WindowConstruction(
        'Double Low-E with Shade', [lowe_glass, gap, clear_glass, shade_mat])
    double_low_e_between_shade = WindowConstruction(
        'Double Low-E Between Shade', [lowe_glass, shade_mat, clear_glass])
    double_low_e_ext_shade = WindowConstruction(
        'Double Low-E Outside Shade', [shade_mat, lowe_glass, gap, clear_glass])

    assert double_low_e_shade.name == 'Double Low-E with Shade'
    assert double_low_e_shade.u_factor == pytest.approx(0.9091, rel=1e-2)
    assert double_low_e_between_shade.name == 'Double Low-E Between Shade'
    assert double_low_e_between_shade.u_factor == pytest.approx(1.13374, rel=1e-2)
    assert double_low_e_ext_shade.name == 'Double Low-E Outside Shade'
    assert double_low_e_ext_shade.u_factor == pytest.approx(0.97678, rel=1e-2)


def test_window_construction_init_blind():
    """Test the initalization of WindowConstruction objects with blinds."""
    lowe_glass = EnergyWindowMaterialGlazing(
        'Low-e Glass', 0.00318, 0.4517, 0.359, 0.714, 0.207,
        0, 0.84, 0.046578, 1.0)
    clear_glass = EnergyWindowMaterialGlazing(
        'Clear Glass', 0.005715, 0.770675, 0.07, 0.8836, 0.0804,
        0, 0.84, 0.84, 1.0)
    gap = EnergyWindowMaterialGas('air gap', thickness=0.0127)
    shade_mat = EnergyWindowMaterialBlind(
        'Plastic Blind', 'Vertical', 0.025, 0.01875, 0.003, 90, 0.2, 0.05, 0.4,
        0.05, 0.45, 0, 0.95, 0.1, 1)
    double_low_e_shade = WindowConstruction(
        'Double Low-E with Shade', [lowe_glass, gap, clear_glass, shade_mat])
    double_low_e_between_shade = WindowConstruction(
        'Double Low-E Between Shade', [lowe_glass, shade_mat, clear_glass])
    double_low_e_ext_shade = WindowConstruction(
        'Double Low-E Outside Shade', [shade_mat, lowe_glass, gap, clear_glass])

    assert double_low_e_shade.name == 'Double Low-E with Shade'
    assert double_low_e_shade.u_factor == pytest.approx(1.26296, rel=1e-2)
    assert double_low_e_between_shade.name == 'Double Low-E Between Shade'
    assert double_low_e_between_shade.u_factor == pytest.approx(1.416379, rel=1e-2)
    assert double_low_e_ext_shade.name == 'Double Low-E Outside Shade'
    assert double_low_e_ext_shade.u_factor == pytest.approx(1.2089, rel=1e-2)


def test_window_construction_init_gas_mixture():
    """Test the initalization of WindowConstruction objects with a gas mixture."""
    lowe_glass = EnergyWindowMaterialGlazing(
        'Low-e Glass', 0.00318, 0.4517, 0.359, 0.714, 0.207,
        0, 0.84, 0.046578, 1.0)
    clear_glass = EnergyWindowMaterialGlazing(
        'Clear Glass', 0.005715, 0.770675, 0.07, 0.8836, 0.0804,
        0, 0.84, 0.84, 1.0)
    air_argon = EnergyWindowMaterialGasMixture(
        'Air Argon Gap', 0.0125, ('Air', 'Argon'), (0.1, 0.9))
    double_low_e_argon = WindowConstruction(
        'Double Low-E with Argon', [lowe_glass, air_argon, clear_glass])

    assert double_low_e_argon.u_factor == pytest.approx(1.46319708, rel=1e-2)


def test_window_temperature_profile():
    """Test the window construction temperature profile."""
    clear_glass = EnergyWindowMaterialGlazing(
        'Clear Glass', 0.005715, 0.770675, 0.07, 0.8836, 0.0804,
        0, 0.84, 0.84, 1.0)
    gap = EnergyWindowMaterialGas('air gap', thickness=0.0127)
    triple_clear = WindowConstruction(
        'Triple Clear Window', [clear_glass, gap, clear_glass, gap, clear_glass])
    temperatures, r_values = triple_clear.temperature_profile()

    assert len(temperatures) == 8
    assert temperatures[0] == pytest.approx(-18, rel=1e-2)
    assert temperatures[-1] == pytest.approx(21, rel=1e-2)
    assert len(r_values) == 7
    assert sum(r_values) == pytest.approx(triple_clear.r_factor, rel=1e-1)
    assert r_values[-1] == pytest.approx((1 / triple_clear.in_h_simple()), rel=1)

    temperatures, r_values = triple_clear.temperature_profile(
        36, 21, 4, 2., 180.0, 100000)
    assert len(temperatures) == 8
    assert temperatures[0] == pytest.approx(36, rel=1e-2)
    assert temperatures[-1] == pytest.approx(21, rel=1e-2)
    assert len(r_values) == 7


def test_window_construction_init_from_idf_file():
    """Test the initalization of WindowConstruction from file."""
    lbnl_window_idf_file = './tests/idf/GlzSys_Triple Clear_Avg.idf'
    glaz_constrs, glaz_mats = WindowConstruction.extract_all_from_idf_file(
        lbnl_window_idf_file)

    assert len(glaz_mats) == 2
    glaz_constr = glaz_constrs[0]
    constr_str = glaz_constr.to_idf()
    mat_str = [mat.to_idf() for mat in glaz_constr.unique_materials]
    new_glaz_constr = WindowConstruction.from_idf(constr_str, mat_str)
    new_constr_str = new_glaz_constr.to_idf()

    assert glaz_constr.name == new_glaz_constr.name == 'GlzSys_5'
    assert glaz_constr.u_factor == new_glaz_constr.u_factor == \
        pytest.approx(1.75728, rel=1e-2)
    assert glaz_constr.thickness == new_glaz_constr.thickness == \
        pytest.approx(0.0425, rel=1e-2)
    assert constr_str == new_constr_str


def test_window_dict_methods():
    """Test the to/from dict methods."""
    clear_glass = EnergyWindowMaterialGlazing(
        'Clear Glass', 0.005715, 0.770675, 0.07, 0.8836, 0.0804,
        0, 0.84, 0.84, 1.0)
    gap = EnergyWindowMaterialGas('air gap', thickness=0.0127)
    triple_clear = WindowConstruction(
        'Triple Clear Window', [clear_glass, gap, clear_glass, gap, clear_glass])
    constr_dict = triple_clear.to_dict()
    new_constr = WindowConstruction.from_dict(constr_dict)
    assert constr_dict == new_constr.to_dict()


def test_shade_construction_init():
    """Test the initalization of ShadeConstruction objects and basic properties."""
    default_constr = ShadeConstruction('Default Shade Construction')
    light_shelf_out = ShadeConstruction('Outdoor Light Shelf', 0.5, 0.6)
    str(light_shelf_out)  # test the string representation of the construction
    assert default_constr.is_default
    assert not light_shelf_out.is_default

    constr_dup = light_shelf_out.duplicate()

    assert light_shelf_out.name == constr_dup.name == 'Outdoor Light Shelf'
    assert light_shelf_out.solar_reflectance == constr_dup.solar_reflectance == 0.5
    assert light_shelf_out.visible_reflectance == constr_dup.visible_reflectance == 0.6
    assert light_shelf_out.is_specular is constr_dup.is_specular


def test_shade_construction_to_idf():
    """Test the initalization of ShadeConstruction objects and basic properties."""
    default_constr = ShadeConstruction('Default Shade Construction')
    light_shelf_out = ShadeConstruction('Outdoor Light Shelf', 0.5, 0.6, True)

    assert isinstance(default_constr.to_idf('Test Shade'), str)
    assert isinstance(light_shelf_out.to_idf('Test Shade'), str)

    assert default_constr.glazing_construction() is None
    assert isinstance(light_shelf_out.glazing_construction(), WindowConstruction)


def test_shade_lockability():
    """Test the lockability of the ShadeConstruction."""
    light_shelf_out = ShadeConstruction('Outdoor Light Shelf', 0.4, 0.6)

    light_shelf_out.solar_reflectance = 0.5
    light_shelf_out.lock()
    with pytest.raises(AttributeError):
        light_shelf_out.solar_reflectance = 0.4
    light_shelf_out.unlock()
    light_shelf_out.solar_reflectance = 0.4


def test_shade_equivalency():
    """Test the equality of a ShadeConstruction to another."""
    shade_constr_1 = ShadeConstruction('Outdoor Light Shelf', 0.4, 0.6)
    shade_constr_2 = shade_constr_1.duplicate()
    shade_constr_3 = ShadeConstruction('Outdoor Light Shelf', 0.5, 0.6)
    shade_constr_4 = ShadeConstruction('Indoor Light Shelf', 0.4, 0.6)

    collection = [shade_constr_1, shade_constr_1, shade_constr_2, shade_constr_3]
    assert len(set(collection)) == 2
    assert shade_constr_1 == shade_constr_2
    assert shade_constr_1 != shade_constr_3
    assert shade_constr_1 != shade_constr_4

    shade_constr_2.name = 'Indoor Light Shelf'
    assert shade_constr_1 != shade_constr_2


def test_shade_dict_methods():
    """Test the to/from dict methods."""
    shade_constr = ShadeConstruction('Outdoor Light Shelf', 0.4, 0.6)
    constr_dict = shade_constr.to_dict()
    new_constr = ShadeConstruction.from_dict(constr_dict)
    assert constr_dict == new_constr.to_dict()
