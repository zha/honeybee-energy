# coding=utf-8
from honeybee_energy.material.opaque import EnergyMaterial, EnergyMaterialNoMass

import pytest


def test_material_init():
    """Test the initalization of EnergyMaterial objects and basic properties."""
    concrete = EnergyMaterial('Concrete', 0.2, 0.5, 800, 0.75,
                              'MediumSmooth', 0.95, 0.75, 0.8)
    str(concrete)  # test the string representation of the material
    concrete_dup = concrete.duplicate()

    assert concrete.name == concrete_dup.name == 'Concrete'
    assert concrete.thickness == concrete_dup.thickness == 0.2
    assert concrete.conductivity == concrete_dup.conductivity == 0.5
    assert concrete.density == concrete_dup.density == 800
    assert concrete.specific_heat == concrete_dup.specific_heat == 0.75
    assert concrete.roughness == concrete_dup.roughness == 'MediumSmooth'
    assert concrete.thermal_absorptance == concrete_dup.thermal_absorptance == 0.95
    assert concrete.solar_absorptance == concrete_dup.solar_absorptance == 0.75
    assert concrete.visible_absorptance == concrete_dup.visible_absorptance == 0.8

    assert concrete.resistivity == 1 / 0.5
    assert concrete.u_value == pytest.approx(2.5, rel=1e-2)
    assert concrete.r_value == pytest.approx(0.4, rel=1e-2)
    assert concrete.mass_area_density == pytest.approx(160, rel=1e-2)
    assert concrete.area_heat_capacity == pytest.approx(120, rel=1e-2)

    concrete.r_value = 0.5
    assert concrete.conductivity != concrete_dup.conductivity
    assert concrete.r_value == 0.5
    assert concrete.conductivity == pytest.approx(0.4, rel=1e-2)


def test_material_defaults():
    """Test the EnergyMaterial default properties."""
    concrete = EnergyMaterial('Concrete [HW]', 0.2, 0.5, 800, 0.75)

    assert concrete.name == 'Concrete HW'
    assert concrete.roughness == 'MediumRough'
    assert concrete.thermal_absorptance == 0.9
    assert concrete.solar_absorptance == concrete.visible_absorptance == 0.7


def test_material_invalid():
    """Test the initalization of EnergyMaterial objects with invalid properties."""
    concrete = EnergyMaterial('Concrete', 0.2, 0.5, 800, 0.75)

    with pytest.raises(Exception):
        concrete.name = ['test_name']
    with pytest.raises(Exception):
        concrete.thickness = -1
    with pytest.raises(Exception):
        concrete.conductivity = -1
    with pytest.raises(Exception):
        concrete.density = -1
    with pytest.raises(Exception):
        concrete.specific_heat = -1
    with pytest.raises(Exception):
        concrete.roughness = 'Medium'
    with pytest.raises(Exception):
        concrete.thermal_absorptance = 2
    with pytest.raises(Exception):
        concrete.solar_absorptance = 2
    with pytest.raises(Exception):
        concrete.visible_absorptance = 2

    with pytest.raises(Exception):
        concrete.resistivity = -1
    with pytest.raises(Exception):
        concrete.u_value = -1
    with pytest.raises(Exception):
        concrete.r_value = -1


def test_material_to_from_idf():
    """Test the initialization of EnergyMaterial objects from EnergyPlus strings."""
    ep_str_1 = "Material,\n" \
        " M01 100mm brick,                    !- Name\n" \
        " MediumRough,                            !- Roughness\n" \
        " 0.1016,                                 !- Thickness {m}\n" \
        " 0.89,                                   !- Conductivity {W/m-K}\n" \
        " 1920,                                   !- Density {kg/m3}\n" \
        " 790,                                    !- Specific Heat {J/kg-K}\n" \
        " 0.9,                                    !- Thermal Absorptance\n" \
        " 0.7,                                    !- Solar Absorptance\n" \
        " 0.7;                                    !- Visible Absorptance"
    mat_1 = EnergyMaterial.from_idf(ep_str_1)

    ep_str_2 = "Material, M01 100mm brick, MediumRough, " \
        "0.1016, 0.89, 1920, 790, 0.9, 0.7, 0.7;"
    mat_2 = EnergyMaterial.from_idf(ep_str_2)

    ep_str_3 = "Material, M01 100mm brick, MediumRough, " \
        "0.1016, 0.89, 1920, 790;"
    mat_3 = EnergyMaterial.from_idf(ep_str_3)

    assert mat_1.name == mat_2.name == mat_3.name

    idf_str = mat_1.to_idf()
    new_mat_1 = EnergyMaterial.from_idf(idf_str)
    assert idf_str == new_mat_1.to_idf()


def test_material_to_from_standards_dict():
    """Test the initialization of EnergyMaterial objects from standards gem."""
    standards_dict = {
        "name": "Extruded Polystyrene - XPS - 6 in. R30.00",
        "material_type": "StandardOpaqueMaterial",
        "roughness": "MediumSmooth",
        "thickness": 6.0,
        "conductivity": 0.20,
        "resistance": 29.9999994,
        "density": 1.3,
        "specific_heat": 0.35,
        "thermal_absorptance": None,
        "solar_absorptance": None,
        "visible_absorptance": None}
    mat_1 = EnergyMaterial.from_standards_dict(standards_dict)

    assert mat_1.name == 'Extruded Polystyrene - XPS - 6 in. R30.00'
    assert mat_1.thickness == pytest.approx(0.1524, rel=1e-3)
    assert mat_1.conductivity == pytest.approx(0.028826, rel=1e-3)
    assert mat_1.density == pytest.approx(20.82, rel=1e-3)
    assert mat_1.specific_heat == pytest.approx(1464.435, rel=1e-3)
    assert mat_1.roughness == 'MediumSmooth'
    assert mat_1.resistivity == pytest.approx(1 / 0.028826, rel=1e-3)


def test_material_dict_methods():
    """Test the to/from dict methods."""
    material = EnergyMaterial('Concrete', 0.2, 0.5, 800, 0.75)
    material_dict = material.to_dict()
    new_material = EnergyMaterial.from_dict(material_dict)
    assert material_dict == new_material.to_dict()


def test_material_nomass_init():
    """Test the initalization of EnergyMaterialNoMass and basic properties."""
    insul_r2 = EnergyMaterialNoMass('Insulation R-2', 2,
                                    'MediumSmooth', 0.95, 0.75, 0.8)
    str(insul_r2)  # test the string representation of the material
    insul_r2_dup = insul_r2.duplicate()

    assert insul_r2.name == insul_r2_dup.name == 'Insulation R-2'
    assert insul_r2.r_value == insul_r2_dup.r_value == 2
    assert insul_r2.roughness == insul_r2_dup.roughness == 'MediumSmooth'
    assert insul_r2.thermal_absorptance == insul_r2_dup.thermal_absorptance == 0.95
    assert insul_r2.solar_absorptance == insul_r2_dup.solar_absorptance == 0.75
    assert insul_r2.visible_absorptance == insul_r2_dup.visible_absorptance == 0.8

    assert insul_r2.u_value == pytest.approx(0.5, rel=1e-2)
    assert insul_r2.r_value == pytest.approx(2, rel=1e-2)

    insul_r2.r_value = 3
    assert insul_r2.r_value == 3


def test_material_nomass_defaults():
    """Test the EnergyMaterialNoMass default properties."""
    insul_r2 = EnergyMaterialNoMass('Insulation [R-2]', 2)

    assert insul_r2.name == 'Insulation R-2'
    assert insul_r2.roughness == 'MediumRough'
    assert insul_r2.thermal_absorptance == 0.9
    assert insul_r2.solar_absorptance == insul_r2.visible_absorptance == 0.7


def test_material_nomass_invalid():
    """Test the initalization of EnergyMaterial objects with invalid properties."""
    insul_r2 = EnergyMaterialNoMass('Insulation [R-2]', 2)

    with pytest.raises(Exception):
        insul_r2.name = ['test_name']
    with pytest.raises(Exception):
        insul_r2.r_value = -1
    with pytest.raises(Exception):
        insul_r2.roughness = 'Medium'
    with pytest.raises(Exception):
        insul_r2.thermal_absorptance = 2
    with pytest.raises(Exception):
        insul_r2.solar_absorptance = 2
    with pytest.raises(Exception):
        insul_r2.visible_absorptance = 2
    with pytest.raises(Exception):
        insul_r2.u_value = -1


def test_material_nomass_init_from_idf():
    """Test the initialization of EnergyMaterialNoMass objects from strings."""
    ep_str_1 = "Material:NoMass,\n" \
        "CP02 CARPET PAD,                        !- Name\n" \
        "Smooth,                                 !- Roughness\n" \
        "0.1,                                    !- Thermal Resistance {m2-K/W}\n" \
        "0.9,                                    !- Thermal Absorptance\n" \
        "0.8,                                    !- Solar Absorptance\n" \
        "0.8;                                    !- Visible Absorptance"
    mat_1 = EnergyMaterialNoMass.from_idf(ep_str_1)

    idf_str = mat_1.to_idf()
    new_mat_1 = EnergyMaterialNoMass.from_idf(idf_str)
    assert idf_str == new_mat_1.to_idf()


def test_material_nomass_to_from_standards_dict():
    """Test the initialization of EnergyMaterialNoMass objects from standards gem."""
    standards_dict = {
        "name": "MAT-SHEATH",
        "material_type": "MasslessOpaqueMaterial",
        "roughness": None,
        "thickness": None,
        "conductivity": 6.24012461866438,
        "resistance": 0.160253209849203,
        "density": 0.0436995724033012,
        "specific_heat": 0.000167192127639247,
        "thermal_absorptance": 0.9,
        "solar_absorptance": 0.7,
        "visible_absorptance": 0.7}
    mat_1 = EnergyMaterialNoMass.from_standards_dict(standards_dict)

    assert mat_1.name == 'MAT-SHEATH'
    assert mat_1.roughness == 'MediumRough'
    assert mat_1.r_value == pytest.approx(0.1602532098 / 5.678, rel=1e-2)
    assert mat_1.thermal_absorptance == 0.9
    assert mat_1.solar_absorptance == 0.7
    assert mat_1.visible_absorptance == 0.7


def test_material_nomass_dict_methods():
    """Test the to/from dict methods."""
    material = EnergyMaterialNoMass('Insulation R-2', 2)
    material_dict = material.to_dict()
    new_material = EnergyMaterialNoMass.from_dict(material_dict)
    assert material_dict == new_material.to_dict()
