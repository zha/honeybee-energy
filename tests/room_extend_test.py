"""Tests the features that honeybee_energy adds to honeybee_core Room."""
from honeybee.room import Room
from honeybee.door import Door

from honeybee_energy.properties.room import RoomEnergyProperties
from honeybee_energy.programtype import ProgramType
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.idealair import IdealAirSystem
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.construction.shade import ShadeConstruction
from honeybee_energy.material.opaque import EnergyMaterial
from honeybee_energy.load.equipment import ElectricEquipment
from honeybee_energy.load.ventilation import Ventilation
from honeybee_energy.schedule.day import ScheduleDay
from honeybee_energy.schedule.ruleset import ScheduleRuleset
import honeybee_energy.lib.scheduletypelimits as schedule_types

from honeybee_energy.lib.programtypes import office_program

from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D

from ladybug.dt import Time

import pytest


def test_energy_properties():
    """Test the existence of the Room energy properties."""
    room = Room.from_box('Shoe Box', 5, 10, 3, 90, Point3D(0, 0, 3))
    room.properties.energy.program_type = office_program
    room.properties.energy.hvac = IdealAirSystem()

    assert hasattr(room.properties, 'energy')
    assert isinstance(room.properties.energy, RoomEnergyProperties)
    assert isinstance(room.properties.energy.construction_set, ConstructionSet)
    assert isinstance(room.properties.energy.program_type, ProgramType)
    assert isinstance(room.properties.energy.hvac, IdealAirSystem)
    assert room.properties.energy.program_type == office_program
    assert room.properties.energy.is_conditioned
    assert room.properties.energy.people == office_program.people
    assert room.properties.energy.lighting == office_program.lighting
    assert room.properties.energy.electric_equipment == office_program.electric_equipment
    assert room.properties.energy.gas_equipment == office_program.gas_equipment
    assert room.properties.energy.infiltration == office_program.infiltration
    assert room.properties.energy.ventilation == office_program.ventilation
    assert room.properties.energy.setpoint == office_program.setpoint


def test_default_properties():
    """Test the auto-assigning of Room properties."""
    room = Room.from_box('Shoe Box', 5, 10, 3, 90, Point3D(0, 0, 3))

    assert room.properties.energy.construction_set.name == \
        'Default Generic Construction Set'
    assert room.properties.energy.program_type.name == 'Plenum'
    assert room.properties.energy.hvac is None
    assert not room.properties.energy.is_conditioned
    assert room.properties.energy.people is None
    assert room.properties.energy.lighting is None
    assert room.properties.energy.electric_equipment is None
    assert room.properties.energy.gas_equipment is None
    assert room.properties.energy.infiltration is None
    assert room.properties.energy.ventilation is None
    assert room.properties.energy.setpoint is None


def test_set_construction_set():
    """Test the setting of a ConstructionSet on a Room."""
    room = Room.from_box('Shoe Box', 5, 10, 3)
    door_verts = [[1, 0, 0.1], [2, 0, 0.1], [2, 0, 3], [1, 0, 3]]
    room[3].add_door(Door.from_vertices('test_door', door_verts))
    room[1].apertures_by_ratio(0.4, 0.01)
    room[1].apertures[0].overhang(0.5, indoor=False)
    room[1].apertures[0].overhang(0.5, indoor=True)
    room[1].apertures[0].move_shades(Vector3D(0, 0, -0.5))

    mass_set = ConstructionSet('Thermal Mass Construction Set')
    concrete20 = EnergyMaterial('20cm Concrete', 0.2, 2.31, 2322, 832,
                                'MediumRough', 0.95, 0.75, 0.8)
    concrete10 = EnergyMaterial('10cm Concrete', 0.1, 2.31, 2322, 832,
                                'MediumRough', 0.95, 0.75, 0.8)
    stone_door = EnergyMaterial('Stone Door', 0.05, 2.31, 2322, 832,
                                'MediumRough', 0.95, 0.75, 0.8)
    thick_constr = OpaqueConstruction('Thick Concrete Construction', [concrete20])
    thin_constr = OpaqueConstruction('Thin Concrete Construction', [concrete10])
    door_constr = OpaqueConstruction('Stone Door', [stone_door])
    shade_constr = ShadeConstruction('Light Shelf', 0.5, 0.5)
    mass_set.wall_set.exterior_construction = thick_constr
    mass_set.roof_ceiling_set.exterior_construction = thin_constr
    mass_set.door_set.exterior_construction = door_constr
    mass_set.shade_construction = shade_constr

    room.properties.energy.construction_set = mass_set
    assert room.properties.energy.construction_set == mass_set
    assert room[1].properties.energy.construction == thick_constr
    assert room[5].properties.energy.construction == thin_constr
    assert room[3].doors[0].properties.energy.construction == door_constr
    assert room[1].apertures[0].shades[0].properties.energy.construction == shade_constr

    with pytest.raises(AttributeError):
        room[1].properties.energy.construction.thickness = 0.3
    with pytest.raises(AttributeError):
        room[5].properties.energy.construction.thickness = 0.3
    with pytest.raises(AttributeError):
        room[3].doors[0].properties.energy.construction.thickness = 0.3


def test_set_program_type():
    """Test the setting of a ProgramType on a Room."""
    lab_equip_day = ScheduleDay('Daily Lab Equipment', [0.25, 0.5, 0.25],
                                [Time(0, 0), Time(9, 0), Time(20, 0)])
    lab_equipment = ScheduleRuleset('Lab Equipment', lab_equip_day,
                                    None, schedule_types.fractional)
    lab_vent_day = ScheduleDay('Daily Lab Ventilation', [0.5, 1, 0.5],
                               [Time(0, 0), Time(9, 0), Time(20, 0)])
    lab_ventilation = ScheduleRuleset('Lab Ventilation', lab_vent_day,
                                      None, schedule_types.fractional)
    lab_program = office_program.duplicate()
    lab_program.name = 'Bio Laboratory'
    lab_program.electric_equipment.watts_per_area = 50
    lab_program.electric_equipment.schedule = lab_equipment
    lab_program.ventilation.flow_per_person = 0
    lab_program.ventilation.flow_per_area = 0
    lab_program.ventilation.air_changes_per_hour = 6
    lab_program.ventilation.schedule = lab_ventilation

    room = Room.from_box('Shoe Box', 5, 10, 3)
    room.properties.energy.program_type = lab_program

    assert room.properties.energy.program_type.name == 'Bio Laboratory'
    assert room.properties.energy.program_type == lab_program
    assert room.properties.energy.electric_equipment.watts_per_area == 50
    assert room.properties.energy.electric_equipment.schedule == lab_equipment
    assert room.properties.energy.ventilation.flow_per_person == 0
    assert room.properties.energy.ventilation.flow_per_area == 0
    assert room.properties.energy.ventilation.air_changes_per_hour == 6
    assert room.properties.energy.ventilation.schedule == lab_ventilation


def test_set_loads():
    """Test the setting of a load objects on a Room."""
    lab_equip_day = ScheduleDay('Daily Lab Equipment', [0.25, 0.5, 0.25],
                                [Time(0, 0), Time(9, 0), Time(20, 0)])
    lab_equipment = ScheduleRuleset('Lab Equipment', lab_equip_day,
                                    None, schedule_types.fractional)
    lab_vent_day = ScheduleDay('Daily Lab Ventilation', [0.5, 1, 0.5],
                               [Time(0, 0), Time(9, 0), Time(20, 0)])
    lab_ventilation = ScheduleRuleset('Lab Ventilation', lab_vent_day,
                                      None, schedule_types.fractional)

    room = Room.from_box('Bio Laboratory Zone', 5, 10, 3)
    room.properties.energy.program_type = office_program
    lab_equip = ElectricEquipment('Lab Equipment', 50, lab_equipment)
    lav_vent = Ventilation('Lab Ventilation', 0, 0, 0, 6, lab_ventilation)
    lab_setpt = room.properties.energy.setpoint.duplicate()
    lab_setpt.heating_setpoint = 22
    lab_setpt.cooling_setpoint = 24
    room.properties.energy.electric_equipment = lab_equip
    room.properties.energy.ventilation = lav_vent
    room.properties.energy.setpoint = lab_setpt

    assert room.properties.energy.program_type == office_program
    assert room.properties.energy.electric_equipment.watts_per_area == 50
    assert room.properties.energy.electric_equipment.schedule == lab_equipment
    assert room.properties.energy.ventilation.flow_per_person == 0
    assert room.properties.energy.ventilation.flow_per_area == 0
    assert room.properties.energy.ventilation.air_changes_per_hour == 6
    assert room.properties.energy.ventilation.schedule == lab_ventilation
    assert room.properties.energy.setpoint.heating_setpoint == 22
    assert room.properties.energy.setpoint.heating_setback == 22
    assert room.properties.energy.setpoint.cooling_setpoint == 24
    assert room.properties.energy.setpoint.cooling_setback == 24


def test_duplicate():
    """Test what happens to energy properties when duplicating a Room."""
    mass_set = ConstructionSet('Thermal Mass Construction Set')
    room_original = Room.from_box('Shoe Box', 5, 10, 3)
    room_dup_1 = room_original.duplicate()

    assert room_original.properties.energy.host is room_original
    assert room_dup_1.properties.energy.host is room_dup_1
    assert room_original.properties.energy.host is not \
        room_dup_1.properties.energy.host

    assert room_original.properties.energy.construction_set == \
        room_dup_1.properties.energy.construction_set
    room_dup_1.properties.energy.construction_set = mass_set
    assert room_original.properties.energy.construction_set != \
        room_dup_1.properties.energy.construction_set

    room_dup_2 = room_dup_1.duplicate()

    assert room_dup_1.properties.energy.construction_set == \
        room_dup_2.properties.energy.construction_set
    room_dup_2.properties.energy.construction_set = None
    assert room_dup_1.properties.energy.construction_set != \
        room_dup_2.properties.energy.construction_set


def test_to_dict():
    """Test the Room to_dict method with energy properties."""
    mass_set = ConstructionSet('Thermal Mass Construction Set')
    room = Room.from_box('Shoe Box', 5, 10, 3)

    rd = room.to_dict()
    assert 'properties' in rd
    assert rd['properties']['type'] == 'RoomProperties'
    assert 'energy' in rd['properties']
    assert rd['properties']['energy']['type'] == 'RoomEnergyProperties'
    assert 'program_type' not in rd['properties']['energy'] or \
        rd['properties']['energy']['program_type'] is None
    assert 'construction_set' not in rd['properties']['energy'] or \
        rd['properties']['energy']['construction_set'] is None
    assert 'hvac' not in rd['properties']['energy'] or \
        rd['properties']['energy']['hvac'] is None
    assert 'people' not in rd['properties']['energy'] or \
        rd['properties']['energy']['people'] is None
    assert 'lighting' not in rd['properties']['energy'] or \
        rd['properties']['energy']['lighting'] is None
    assert 'electric_equipment' not in rd['properties']['energy'] or \
        rd['properties']['energy']['electric_equipment'] is None
    assert 'gas_equipment' not in rd['properties']['energy'] or \
        rd['properties']['energy']['gas_equipment'] is None
    assert 'infiltration' not in rd['properties']['energy'] or \
        rd['properties']['energy']['infiltration'] is None
    assert 'ventilation' not in rd['properties']['energy'] or \
        rd['properties']['energy']['ventilation'] is None
    assert 'setpoint' not in rd['properties']['energy'] or \
        rd['properties']['energy']['setpoint'] is None

    room.properties.energy.construction_set = mass_set
    rd = room.to_dict()
    assert rd['properties']['energy']['construction_set'] is not None


def test_from_dict():
    """Test the Room from_dict method with energy properties."""
    mass_set = ConstructionSet('Thermal Mass Construction Set')
    room = Room.from_box('Shoe Box', 5, 10, 3)
    room.properties.energy.construction_set = mass_set

    rd = room.to_dict()
    new_room = Room.from_dict(rd)
    assert new_room.properties.energy.construction_set.name == \
        'Thermal Mass Construction Set'
    assert new_room.to_dict() == rd


def test_writer_to_idf():
    """Test the Room to_idf method."""
    room = Room.from_box('ClosedOffice', 5, 10, 3)
    room.properties.energy.program_type = office_program
    room.properties.energy.hvac = IdealAirSystem()

    assert hasattr(room.to, 'idf')
    idf_string = room.to.idf(room)
    assert 'ClosedOffice,' in idf_string
    assert 'Zone,' in idf_string
    assert 'People' in idf_string
    assert 'Lights' in idf_string
    assert 'ElectricEquipment' in idf_string
    assert 'GasEquipment' not in idf_string
    assert 'ZoneInfiltration:DesignFlowRate' in idf_string
    assert 'DesignSpecification:OutdoorAir' in idf_string
    assert 'HVACTemplate:Thermostat' in idf_string
    assert 'HVACTemplate:Zone:IdealLoadsAirSystem' in idf_string
