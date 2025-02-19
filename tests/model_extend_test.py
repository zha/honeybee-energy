"""Tests the features that honeybee_energy adds to honeybee_core Model."""
from honeybee.model import Model
from honeybee.room import Room
from honeybee.face import Face
from honeybee.shade import Shade
from honeybee.aperture import Aperture
from honeybee.door import Door
from honeybee.boundarycondition import boundary_conditions, Ground, Outdoors
from honeybee.facetype import face_types

from honeybee_energy.properties.model import ModelEnergyProperties
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.idealair import IdealAirSystem
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.construction.window import WindowConstruction
from honeybee_energy.construction.shade import ShadeConstruction
from honeybee_energy.material._base import _EnergyMaterialBase
from honeybee_energy.material.opaque import EnergyMaterial
from honeybee_energy.schedule.ruleset import ScheduleRuleset
from honeybee_energy.schedule.fixedinterval import ScheduleFixedInterval
from honeybee_energy.schedule.typelimit import ScheduleTypeLimit
from honeybee_energy.load.people import People

from honeybee_energy.lib.programtypes import office_program
import honeybee_energy.lib.scheduletypelimits as schedule_types
from honeybee_energy.lib.materials import clear_glass, air_gap, roof_membrane, \
    wood, insulation
from honeybee_energy.lib.constructions import generic_exterior_wall, \
    generic_interior_wall, generic_interior_floor, generic_interior_ceiling, \
    generic_double_pane

from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.plane import Plane
from ladybug_geometry.geometry3d.face import Face3D

import random
import json
import pytest


def test_energy_properties():
    """Test the existence of the Model energy properties."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    room.properties.energy.program_type = office_program
    room.properties.energy.hvac = IdealAirSystem()
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    fritted_glass_trans = ScheduleRuleset.from_constant_value(
        'Fritted Glass', 0.5, schedule_types.fractional)
    south_face.apertures[0].outdoor_shades[0].properties.energy.transmittance_schedule = \
        fritted_glass_trans
    model = Model('Tiny House', [room])

    assert hasattr(model.properties, 'energy')
    assert isinstance(model.properties.energy, ModelEnergyProperties)
    assert isinstance(model.properties.host, Model)
    assert len(model.properties.energy.materials) == 15
    for mat in model.properties.energy.materials:
        assert isinstance(mat, _EnergyMaterialBase)
    assert len(model.properties.energy.constructions) == 14
    for cnst in model.properties.energy.constructions:
        assert isinstance(
            cnst, (WindowConstruction, OpaqueConstruction, ShadeConstruction))
    assert len(model.properties.energy.face_constructions) == 0
    assert len(model.properties.energy.construction_sets) == 0
    assert isinstance(model.properties.energy.global_construction_set, ConstructionSet)
    assert len(model.properties.energy.schedule_type_limits) == 3
    assert len(model.properties.energy.schedules) == 8
    assert len(model.properties.energy.shade_schedules) == 1
    assert len(model.properties.energy.room_schedules) == 0
    assert len(model.properties.energy.program_types) == 1


def test_check_duplicate_construction_set_names():
    """Test the check_duplicate_construction_set_names method."""
    first_floor = Room.from_box('First Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    for face in first_floor[1:5]:
        face.apertures_by_ratio(0.2, 0.01)
    for face in second_floor[1:5]:
        face.apertures_by_ratio(0.2, 0.01)

    pts_1 = [Point3D(0, 0, 6), Point3D(0, 10, 6), Point3D(10, 10, 6), Point3D(10, 0, 6)]
    pts_2 = [Point3D(0, 0, 6), Point3D(5, 0, 9), Point3D(5, 10, 9), Point3D(0, 10, 6)]
    pts_3 = [Point3D(10, 0, 6), Point3D(10, 10, 6), Point3D(5, 10, 9), Point3D(5, 0, 9)]
    pts_4 = [Point3D(0, 0, 6), Point3D(10, 0, 6), Point3D(5, 0, 9)]
    pts_5 = [Point3D(10, 10, 6), Point3D(0, 10, 6), Point3D(5, 10, 9)]
    face_1 = Face('Attic Face 1', Face3D(pts_1))
    face_2 = Face('Attic Face 2', Face3D(pts_2))
    face_3 = Face('Attic Face 3', Face3D(pts_3))
    face_4 = Face('Attic Face 4', Face3D(pts_4))
    face_5 = Face('Attic Face 5', Face3D(pts_5))
    attic = Room('Attic', [face_1, face_2, face_3, face_4, face_5], 0.01, 1)

    constr_set = ConstructionSet('Attic Construction Set')
    polyiso = EnergyMaterial('PolyIso', 0.2, 0.03, 43, 1210, 'MediumRough')
    roof_constr = OpaqueConstruction('Attic Roof Construction',
                                     [roof_membrane, polyiso, wood])
    floor_constr = OpaqueConstruction('Attic Floor Construction',
                                      [wood, insulation, wood])
    constr_set.floor_set.interior_construction = floor_constr
    constr_set.roof_ceiling_set.exterior_construction = roof_constr
    attic.properties.energy.construction_set = constr_set

    Room.solve_adjacency([first_floor, second_floor, attic], 0.01)

    model = Model('Multi Zone Single Family House', [first_floor, second_floor, attic])

    assert model.properties.energy.check_duplicate_construction_set_names(False)
    constr_set.unlock()
    constr_set.name = 'Default Generic Construction Set'
    constr_set.lock()
    assert not model.properties.energy.check_duplicate_construction_set_names(False)
    with pytest.raises(ValueError):
        model.properties.energy.check_duplicate_construction_set_names(True)


def test_check_duplicate_construction_names():
    """Test the check_duplicate_construction_names method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)

    stone = EnergyMaterial('Thick Stone', 0.3, 2.31, 2322, 832, 'Rough',
                           0.95, 0.75, 0.8)
    thermal_mass_constr = OpaqueConstruction('Custom Construction', [stone])
    room[0].properties.energy.construction = thermal_mass_constr

    north_face = room[1]
    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    aperture = Aperture('Front Aperture', Face3D(aperture_verts))
    aperture.is_operable = True
    triple_pane = WindowConstruction(
        'Custom Window Construction', [clear_glass, air_gap, clear_glass, air_gap, clear_glass])
    aperture.properties.energy.construction = triple_pane
    north_face.add_aperture(aperture)

    model = Model('Tiny House', [room])

    assert model.properties.energy.check_duplicate_construction_names(False)
    triple_pane.unlock()
    triple_pane.name = 'Custom Construction'
    triple_pane.lock()
    assert not model.properties.energy.check_duplicate_construction_names(False)
    with pytest.raises(ValueError):
        model.properties.energy.check_duplicate_construction_names(True)


def test_check_duplicate_material_names():
    """Test the check_duplicate_material_names method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)

    stone = EnergyMaterial('Stone', 0.3, 2.31, 2322, 832, 'Rough',
                           0.95, 0.75, 0.8)
    thin_stone = EnergyMaterial('Thin Stone', 0.05, 2.31, 2322, 832, 'Rough',
                                0.95, 0.75, 0.8)
    thermal_mass_constr = OpaqueConstruction('Custom Construction', [stone])
    door_constr = OpaqueConstruction('Custom Door Construction', [thin_stone])
    room[0].properties.energy.construction = thermal_mass_constr

    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    door.properties.energy.construction = door_constr
    north_face.add_door(door)

    model = Model('Tiny House', [room])

    assert model.properties.energy.check_duplicate_material_names(False)
    thin_stone.unlock()
    thin_stone.name = 'Stone'
    thin_stone.lock()
    assert not model.properties.energy.check_duplicate_material_names(False)
    with pytest.raises(ValueError):
        model.properties.energy.check_duplicate_material_names(True)


def test_check_duplicate_schedule_names():
    """Test the check_duplicate_schedule_names method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    room.properties.energy.program_type = office_program
    room.properties.energy.hvac = IdealAirSystem()
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    fritted_glass_trans = ScheduleRuleset.from_constant_value(
        'Fritted Glass', 0.6, schedule_types.fractional)
    half_occ = ScheduleRuleset.from_constant_value(
        'Half Occupied', 0.5, schedule_types.fractional)
    south_face.apertures[0].outdoor_shades[0].properties.energy.transmittance_schedule = \
        fritted_glass_trans
    room.properties.energy.people = People('Office Occ', 0.05, half_occ)
    model = Model('Tiny House', [room])

    assert model.properties.energy.check_duplicate_schedule_names(False)
    half_occ.unlock()
    half_occ.name = 'Fritted Glass'
    half_occ.lock()
    assert not model.properties.energy.check_duplicate_schedule_names(False)
    with pytest.raises(ValueError):
        model.properties.energy.check_duplicate_schedule_names(True)


def test_check_duplicate_schedule_type_limit_names():
    """Test the check_duplicate_schedule_type_limit_names method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    room.properties.energy.program_type = office_program
    room.properties.energy.hvac = IdealAirSystem()
    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    fritted_glass_trans = ScheduleRuleset.from_constant_value(
        'Fritted Glass', 0.6, schedule_types.fractional)
    on_off = ScheduleTypeLimit('On-off', 0, 1, 'Discrete')
    full_occ = ScheduleRuleset.from_constant_value('Occupied', 1, on_off)
    south_face.apertures[0].outdoor_shades[0].properties.energy.transmittance_schedule = \
        fritted_glass_trans
    room.properties.energy.people = People('Office Occ', 0.05, full_occ)
    model = Model('Tiny House', [room])

    assert model.properties.energy.check_duplicate_schedule_type_limit_names(False)
    full_occ.unlock()
    new_sch_type = ScheduleTypeLimit('Fractional', 0, 1, 'Discrete')
    full_occ.schedule_type_limit = new_sch_type
    full_occ.lock()
    assert not model.properties.energy.check_duplicate_schedule_type_limit_names(False)
    with pytest.raises(ValueError):
        model.properties.energy.check_duplicate_schedule_type_limit_names(True)


def test_to_from_dict():
    """Test the Model to_dict and from_dict method with a single zone model."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    room.properties.energy.program_type = office_program
    room.properties.energy.hvac = IdealAirSystem()

    stone = EnergyMaterial('Thick Stone', 0.3, 2.31, 2322, 832, 'Rough',
                           0.95, 0.75, 0.8)
    thermal_mass_constr = OpaqueConstruction('Thermal Mass Floor', [stone])
    room[0].properties.energy.construction = thermal_mass_constr

    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.apertures[0].move_shades(Vector3D(0, 0, -0.5))
    light_shelf_out = ShadeConstruction('Outdoor Light Shelf', 0.5, 0.5)
    light_shelf_in = ShadeConstruction('Indoor Light Shelf', 0.7, 0.7)
    south_face.apertures[0].shades[0].properties.energy.construction = light_shelf_out
    south_face.apertures[0].shades[1].properties.energy.construction = light_shelf_in

    north_face = room[1]
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    north_face.add_door(door)

    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    aperture = Aperture('Front Aperture', Face3D(aperture_verts))
    aperture.is_operable = True
    triple_pane = WindowConstruction(
        'Triple Pane Window', [clear_glass, air_gap, clear_glass, air_gap, clear_glass])
    aperture.properties.energy.construction = triple_pane
    north_face.add_aperture(aperture)

    tree_canopy_geo = Face3D.from_regular_polygon(
        6, 2, Plane(Vector3D(0, 0, 1), Point3D(5, -3, 4)))
    tree_canopy = Shade('Tree Canopy', tree_canopy_geo)
    tree_trans = ScheduleRuleset.from_constant_value(
        'Tree Transmittance', 0.75, schedule_types.fractional)
    tree_canopy.properties.energy.transmittance_schedule = tree_trans

    model = Model('Tiny House', [room], orphaned_shades=[tree_canopy])
    model.north_angle = 15
    model_dict = model.to_dict()
    new_model = Model.from_dict(model_dict)
    assert model_dict == new_model.to_dict()

    assert stone in new_model.properties.energy.materials
    assert thermal_mass_constr in new_model.properties.energy.constructions
    assert new_model.rooms[0][0].properties.energy.construction == thermal_mass_constr
    assert new_model.rooms[0][3].apertures[0].indoor_shades[0].properties.energy.construction == light_shelf_in
    assert new_model.rooms[0][3].apertures[0].outdoor_shades[0].properties.energy.construction == light_shelf_out
    assert triple_pane in new_model.properties.energy.constructions
    assert new_model.rooms[0][1].apertures[0].properties.energy.construction == triple_pane
    assert new_model.rooms[0][1].apertures[0].is_operable
    assert len(new_model.orphaned_shades) == 1
    assert new_model.north_angle == 15

    assert new_model.rooms[0][0].type == face_types.floor
    assert new_model.rooms[0][1].type == face_types.wall
    assert isinstance(new_model.rooms[0][0].boundary_condition, Ground)
    assert isinstance(new_model.rooms[0][1].boundary_condition, Outdoors)

    assert new_model.rooms[0].properties.energy.program_type == office_program
    assert len(new_model.properties.energy.schedule_type_limits) == 3
    assert len(model.properties.energy.schedules) == 8
    assert new_model.rooms[0].properties.energy.is_conditioned
    assert new_model.rooms[0].properties.energy.hvac == IdealAirSystem()

    assert new_model.orphaned_shades[0].properties.energy.transmittance_schedule == tree_trans


def test_to_dict_single_zone():
    """Test the Model to_dict method with a single zone model."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    room.properties.energy.program_type = office_program
    room.properties.energy.hvac = IdealAirSystem()

    stone = EnergyMaterial('Thick Stone', 0.3, 2.31, 2322, 832, 'Rough',
                           0.95, 0.75, 0.8)
    thermal_mass_constr = OpaqueConstruction('Thermal Mass Floor', [stone])
    room[0].properties.energy.construction = thermal_mass_constr

    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.move_shades(Vector3D(0, 0, -0.5))
    light_shelf_out = ShadeConstruction('Outdoor Light Shelf', 0.5, 0.5)
    light_shelf_in = ShadeConstruction('Indoor Light Shelf', 0.7, 0.7)
    south_face.apertures[0].outdoor_shades[0].properties.energy.construction = light_shelf_out
    south_face.apertures[0].indoor_shades[0].properties.energy.construction = light_shelf_in

    north_face = room[1]
    north_face.overhang(0.25, indoor=False)
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    north_face.add_door(door)

    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    aperture = Aperture('Front Aperture', Face3D(aperture_verts))
    triple_pane = WindowConstruction(
        'Triple Pane Window', [clear_glass, air_gap, clear_glass, air_gap, clear_glass])
    aperture.properties.energy.construction = triple_pane
    north_face.add_aperture(aperture)

    tree_canopy_geo = Face3D.from_regular_polygon(
        6, 2, Plane(Vector3D(0, 0, 1), Point3D(5, -3, 4)))
    tree_canopy = Shade('Tree Canopy', tree_canopy_geo)

    table_geo = Face3D.from_rectangle(2, 2, Plane(o=Point3D(1.5, 4, 1)))
    table = Shade('Table', table_geo)
    room.add_indoor_shade(table)

    model = Model('Tiny House', [room], orphaned_shades=[tree_canopy])
    model.north_angle = 15

    model_dict = model.to_dict()

    assert 'energy' in model_dict['properties']
    assert 'materials' in model_dict['properties']['energy']
    assert 'constructions' in model_dict['properties']['energy']
    assert 'construction_sets' in model_dict['properties']['energy']
    assert 'global_construction_set' in model_dict['properties']['energy']

    assert len(model_dict['properties']['energy']['materials']) == 16
    assert len(model_dict['properties']['energy']['constructions']) == 18
    assert len(model_dict['properties']['energy']['construction_sets']) == 1

    assert model_dict['rooms'][0]['faces'][0]['properties']['energy']['construction'] == \
        thermal_mass_constr.name
    south_ap_dict = model_dict['rooms'][0]['faces'][3]['apertures'][0]
    assert south_ap_dict['outdoor_shades'][0]['properties']['energy']['construction'] == \
        light_shelf_out.name
    assert south_ap_dict['indoor_shades'][0]['properties']['energy']['construction'] == \
        light_shelf_in.name
    assert model_dict['rooms'][0]['faces'][1]['apertures'][0]['properties']['energy']['construction'] == \
        triple_pane.name

    assert model_dict['rooms'][0]['properties']['energy']['program_type'] == \
        office_program.name
    assert model_dict['rooms'][0]['properties']['energy']['hvac'] == \
        IdealAirSystem().to_dict()

    """
    f_dir = 'C:/Users/chris/Documents/GitHub/energy-model-schema/app/models/samples/json'
    dest_file = f_dir + '/model_single_zone_office.json'
    with open(dest_file, 'w') as fp:
        json.dump(model_dict, fp, indent=4)
    """


def test_to_dict_single_zone_schedule_fixed_interval():
    """Test the Model to_dict method with a single zone model and fixed interval schedules."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    room.properties.energy.program_type = office_program
    room.properties.energy.hvac = IdealAirSystem()

    occ_sched = ScheduleFixedInterval(
        'Random Occupancy', [round(random.random(), 4) for i in range(8760)],
        schedule_types.fractional)
    new_people = room.properties.energy.people.duplicate()
    new_people.occupancy_schedule = occ_sched
    room.properties.energy.people = new_people

    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.move_shades(Vector3D(0, 0, -0.5))
    light_shelf_out = ShadeConstruction('Outdoor Light Shelf', 0.5, 0.5)
    light_shelf_in = ShadeConstruction('Indoor Light Shelf', 0.7, 0.7)
    south_face.apertures[0].outdoor_shades[0].properties.energy.construction = light_shelf_out
    south_face.apertures[0].indoor_shades[0].properties.energy.construction = light_shelf_in

    north_face = room[1]
    north_face.overhang(0.25, indoor=False)
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    north_face.add_door(door)

    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    aperture = Aperture('Front Aperture', Face3D(aperture_verts))
    north_face.add_aperture(aperture)

    tree_canopy_geo = Face3D.from_regular_polygon(
        6, 2, Plane(Vector3D(0, 0, 1), Point3D(5, -3, 4)))
    tree_canopy = Shade('Tree Canopy', tree_canopy_geo)
    winter = [0.75] * 2190
    spring = [0.75 - ((x / 2190) * 0.5) for x in range(2190)]
    summer = [0.25] * 2190
    fall = [0.25 + ((x / 2190) * 0.5) for x in range(2190)]
    trans_sched = ScheduleFixedInterval(
        'Seasonal Tree Transmittance', winter + spring + summer + fall,
        schedule_types.fractional)
    tree_canopy.properties.energy.transmittance_schedule = trans_sched

    model = Model('Tiny House', [room], orphaned_shades=[tree_canopy])
    model.north_angle = 15

    model_dict = model.to_dict()

    assert 'energy' in model_dict['properties']
    assert 'schedules' in model_dict['properties']['energy']
    assert 'program_types' in model_dict['properties']['energy']

    assert len(model_dict['properties']['energy']['program_types']) == 1
    assert len(model_dict['properties']['energy']['schedules']) == 9

    assert 'people' in model_dict['rooms'][0]['properties']['energy']
    assert model_dict['rooms'][0]['properties']['energy']['people']['occupancy_schedule'] \
        == 'Random Occupancy'
    assert model_dict['orphaned_shades'][0]['properties']['energy']['transmittance_schedule'] \
        == 'Seasonal Tree Transmittance'

    assert model_dict['rooms'][0]['properties']['energy']['program_type'] == \
        office_program.name

    """
    f_dir = 'C:/Users/chris/Documents/GitHub/energy-model-schema/app/models/samples/json'
    dest_file = f_dir + '/model_single_zone_office_fixed_interval.json'
    with open(dest_file, 'w') as fp:
        json.dump(model_dict, fp, indent=4)
    """


def test_to_dict_shoe_box():
    """Test the Model to_dict method with a shoebox zone model."""
    room = Room.from_box('Simple Shoe Box Zone', 5, 10, 3)
    room[0].boundary_condition = boundary_conditions.adiabatic
    for face in room[2:]:
        face.boundary_condition = boundary_conditions.adiabatic

    north_face = room[1]
    north_face.apertures_by_ratio_rectangle(0.4, 2, 0.7, 2, 0, 0.01)

    constr_set = ConstructionSet('Shoe Box Construction Set')
    constr_set.wall_set.exterior_construction = generic_exterior_wall
    constr_set.wall_set.interior_construction = generic_interior_wall
    constr_set.floor_set.interior_construction = generic_interior_floor
    constr_set.roof_ceiling_set.interior_construction = generic_interior_ceiling
    constr_set.aperture_set.window_construction = generic_double_pane
    room.properties.energy.construction_set = constr_set

    model = Model('Shoe Box', [room])
    model_dict = model.to_dict()
    model_dict['properties']['energy'] = model.properties.energy.to_dict(
        include_global_construction_set=False)['energy']

    assert 'energy' in model_dict['properties']
    assert 'materials' in model_dict['properties']['energy']
    assert 'constructions' in model_dict['properties']['energy']
    assert 'construction_sets' in model_dict['properties']['energy']

    assert len(model_dict['properties']['energy']['materials']) == 10
    assert len(model_dict['properties']['energy']['constructions']) == 5

    assert model_dict['rooms'][0]['faces'][0]['boundary_condition']['type'] == 'Adiabatic'
    assert model_dict['rooms'][0]['faces'][2]['boundary_condition']['type'] == 'Adiabatic'

    """
    f_dir = 'C:/Users/chris/Documents/GitHub/energy-model-schema/app/models/samples/json'
    dest_file = f_dir + '/model_shoe_box.json'
    with open(dest_file, 'w') as fp:
        json.dump(model_dict, fp, indent=4)
    """


def test_to_dict_multizone_house():
    """Test the Model to_dict method with a multi-zone house."""
    first_floor = Room.from_box('First Floor', 10, 10, 3, origin=Point3D(0, 0, 0))
    second_floor = Room.from_box('Second Floor', 10, 10, 3, origin=Point3D(0, 0, 3))
    first_floor.properties.energy.program_type = office_program
    second_floor.properties.energy.program_type = office_program
    first_floor.properties.energy.hvac = IdealAirSystem()
    second_floor.properties.energy.hvac = IdealAirSystem()
    for face in first_floor[1:5]:
        face.apertures_by_ratio(0.2, 0.01)
    for face in second_floor[1:5]:
        face.apertures_by_ratio(0.2, 0.01)

    pts_1 = [Point3D(0, 0, 6), Point3D(0, 10, 6), Point3D(10, 10, 6), Point3D(10, 0, 6)]
    pts_2 = [Point3D(0, 0, 6), Point3D(5, 0, 9), Point3D(5, 10, 9), Point3D(0, 10, 6)]
    pts_3 = [Point3D(10, 0, 6), Point3D(10, 10, 6), Point3D(5, 10, 9), Point3D(5, 0, 9)]
    pts_4 = [Point3D(0, 0, 6), Point3D(10, 0, 6), Point3D(5, 0, 9)]
    pts_5 = [Point3D(10, 10, 6), Point3D(0, 10, 6), Point3D(5, 10, 9)]
    face_1 = Face('Attic Face 1', Face3D(pts_1))
    face_2 = Face('Attic Face 2', Face3D(pts_2))
    face_3 = Face('Attic Face 3', Face3D(pts_3))
    face_4 = Face('Attic Face 4', Face3D(pts_4))
    face_5 = Face('Attic Face 5', Face3D(pts_5))
    attic = Room('Attic', [face_1, face_2, face_3, face_4, face_5], 0.01, 1)

    constr_set = ConstructionSet('Attic Construction Set')
    polyiso = EnergyMaterial('PolyIso', 0.2, 0.03, 43, 1210, 'MediumRough')
    roof_constr = OpaqueConstruction('Attic Roof Construction',
                                     [roof_membrane, polyiso, wood])
    floor_constr = OpaqueConstruction('Attic Floor Construction',
                                      [wood, insulation, wood])
    constr_set.floor_set.interior_construction = floor_constr
    constr_set.roof_ceiling_set.exterior_construction = roof_constr
    attic.properties.energy.construction_set = constr_set

    Room.solve_adjacency([first_floor, second_floor, attic], 0.01)

    model = Model('Multi Zone Single Family House', [first_floor, second_floor, attic])
    model_dict = model.to_dict()

    assert 'energy' in model_dict['properties']
    assert 'materials' in model_dict['properties']['energy']
    assert 'constructions' in model_dict['properties']['energy']
    assert 'construction_sets' in model_dict['properties']['energy']
    assert 'global_construction_set' in model_dict['properties']['energy']

    assert len(model_dict['properties']['energy']['materials']) == 16
    assert len(model_dict['properties']['energy']['constructions']) == 16
    assert len(model_dict['properties']['energy']['construction_sets']) == 2

    assert model_dict['rooms'][0]['faces'][5]['boundary_condition']['type'] == 'Surface'
    assert model_dict['rooms'][1]['faces'][0]['boundary_condition']['type'] == 'Surface'
    assert model_dict['rooms'][1]['faces'][5]['boundary_condition']['type'] == 'Surface'
    assert model_dict['rooms'][2]['faces'][0]['boundary_condition']['type'] == 'Surface'

    assert model_dict['rooms'][2]['properties']['energy']['construction_set'] == \
        constr_set.name

    assert model_dict['rooms'][0]['properties']['energy']['program_type'] == \
        model_dict['rooms'][1]['properties']['energy']['program_type'] == \
        office_program.name
    assert model_dict['rooms'][0]['properties']['energy']['hvac'] == \
        model_dict['rooms'][1]['properties']['energy']['hvac'] == \
        IdealAirSystem().to_dict()

    """
    f_dir = 'C:/Users/chris/Documents/GitHub/energy-model-schema/app/models/samples/json'
    dest_file = f_dir + '/model_multi_zone_office.json'
    with open(dest_file, 'w') as fp:
        json.dump(model_dict, fp, indent=4)
    """


def test_writer_to_idf():
    """Test the Model to.idf method."""
    room = Room.from_box('Tiny House Zone', 5, 10, 3)
    room.properties.energy.program_type = office_program
    room.properties.energy.hvac = IdealAirSystem()

    stone = EnergyMaterial('Thick Stone', 0.3, 2.31, 2322, 832, 'Rough',
                           0.95, 0.75, 0.8)
    thermal_mass_constr = OpaqueConstruction('Thermal Mass Floor', [stone])
    room[0].properties.energy.construction = thermal_mass_constr

    south_face = room[3]
    south_face.apertures_by_ratio(0.4, 0.01)
    south_face.apertures[0].overhang(0.5, indoor=False)
    south_face.apertures[0].overhang(0.5, indoor=True)
    south_face.move_shades(Vector3D(0, 0, -0.5))
    light_shelf_out = ShadeConstruction('Outdoor Light Shelf', 0.5, 0.5)
    light_shelf_in = ShadeConstruction('Indoor Light Shelf', 0.7, 0.7)
    south_face.apertures[0].outdoor_shades[0].properties.energy.construction = light_shelf_out
    south_face.apertures[0].indoor_shades[0].properties.energy.construction = light_shelf_in

    north_face = room[1]
    north_face.overhang(0.25, indoor=False)
    door_verts = [Point3D(2, 10, 0.1), Point3D(1, 10, 0.1),
                  Point3D(1, 10, 2.5), Point3D(2, 10, 2.5)]
    door = Door('Front Door', Face3D(door_verts))
    north_face.add_door(door)

    aperture_verts = [Point3D(4.5, 10, 1), Point3D(2.5, 10, 1),
                      Point3D(2.5, 10, 2.5), Point3D(4.5, 10, 2.5)]
    aperture = Aperture('Front Aperture', Face3D(aperture_verts))
    triple_pane = WindowConstruction(
        'Triple Pane Window', [clear_glass, air_gap, clear_glass, air_gap, clear_glass])
    aperture.properties.energy.construction = triple_pane
    north_face.add_aperture(aperture)

    tree_canopy_geo = Face3D.from_regular_polygon(
        6, 2, Plane(Vector3D(0, 0, 1), Point3D(5, -3, 4)))
    tree_canopy = Shade('Tree Canopy', tree_canopy_geo)

    table_geo = Face3D.from_rectangle(2, 2, Plane(o=Point3D(1.5, 4, 1)))
    table = Shade('Table', table_geo)
    room.add_indoor_shade(table)

    model = Model('TinyHouse', [room], orphaned_shades=[tree_canopy])
    model.north_angle = 15

    assert hasattr(model.to, 'idf')
    idf_string = model.to.idf(model, schedule_directory='./tests/idf/')
    assert 'TinyHouse,' in idf_string
    assert 'Building,' in idf_string
