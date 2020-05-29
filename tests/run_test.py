# coding=utf-8
from honeybee_energy.run import measure_compatible_model_json, run_idf, \
    prepare_idf_for_simulation, to_openstudio_osw
from honeybee_energy.result.err import Err
from honeybee_energy.lib.programtypes import office_program
from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.measure import Measure

from ladybug.dt import Date
from ladybug.futil import write_to_file
from honeybee.model import Model
from honeybee.room import Room
from honeybee.config import folders

import os
import json
import pytest


def test_measure_compatible_model_json():
    """Test measure_compatible_model_json."""
    room = Room.from_box('TinyHouseZone', 120, 240, 96)
    inches_conversion = Model.conversion_factor_to_meters('Inches')

    model = Model('TinyHouse', [room], units='Inches')
    model_json_path = './tests/simulation/model_inches.json'
    with open(model_json_path, 'w') as fp:
        json.dump(model.to_dict(included_prop=['energy']), fp)

    osm_model_json = measure_compatible_model_json(model_json_path)
    assert os.path.isfile(osm_model_json)

    with open(osm_model_json) as json_file:
        data = json.load(json_file)

    parsed_model = Model.from_dict(data)

    assert parsed_model.rooms[0].floor_area == \
        pytest.approx(120 * 240 * (inches_conversion ** 2), rel=1e-3)
    assert parsed_model.rooms[0].volume == \
        pytest.approx(120 * 240 * 96 * (inches_conversion ** 3), rel=1e-3)
    assert parsed_model.units == 'Meters'

    os.remove(model_json_path)
    os.remove(osm_model_json)


def test_to_openstudio_osw():
    """Test to_openstudio_osw."""
    # create the model
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
    model = Model('TinyHouse', [room])
    model_json_path = './tests/simulation/model_osw_test.json'
    with open(model_json_path, 'w') as fp:
        json.dump(model.to_dict(included_prop=['energy']), fp)

    # create the simulation parameter
    sim_par = SimulationParameter()
    sim_par.output.add_zone_energy_use()
    simpar_json_path = './tests/simulation/simpar_osw_test.json'
    with open(simpar_json_path, 'w') as fp:
        json.dump(sim_par.to_dict(), fp)

    # create additional measures
    measure_path = './tests/measure/edit_fraction_radiant_of_lighting_and_equipment'
    measure = Measure(measure_path)
    measure.arguments[0].value = 0.25
    measure.arguments[1].value = 0.25

    # test it without measures
    folder = './tests/simulation/'
    osw_path = os.path.join(folder, 'workflow.osw')

    osw = to_openstudio_osw(folder, model_json_path, simpar_json_path)
    assert os.path.isfile(osw_path)
    os.remove(osw_path)

    # test it with measures
    osw = to_openstudio_osw(folder, model_json_path, additional_measures=[measure])
    assert os.path.isfile(osw_path)
    os.remove(osw_path)

    os.remove(model_json_path)
    os.remove(simpar_json_path)


def test_run_idf():
    """Test the prepare_idf_for_simulation and run_idf methods."""
    # Get input Model
    room = Room.from_box('TinyHouseZone', 5, 10, 3)
    room.properties.energy.program_type = office_program
    room.properties.energy.add_default_ideal_air()
    model = Model('TinyHouse', [room])

    # Get the input SimulationParameter
    sim_par = SimulationParameter()
    sim_par.output.add_zone_energy_use()
    ddy_file = './tests/ddy/chicago.ddy'
    sim_par.sizing_parameter.add_from_ddy_996_004(ddy_file)
    sim_par.run_period.end_date = Date(1, 7)

    # create the IDF string for simulation paramters and model
    idf_str = '\n\n'.join((sim_par.to_idf(), model.to.idf(model)))

    # write the final string into an IDF
    idf = os.path.join(folders.default_simulation_folder, 'test_file', 'in.idf')
    write_to_file(idf, idf_str, True)

    # prepare the IDF for simulation
    epw_file = './tests/simulation/chicago.epw'
    prepare_idf_for_simulation(idf, epw_file)

    # run the IDF through EnergyPlus
    sql, zsz, rdd, html, err = run_idf(idf, epw_file)

    assert os.path.isfile(sql)
    assert os.path.isfile(err)
    err_obj = Err(err)
    assert 'EnergyPlus Completed Successfully' in err_obj.file_contents


def test_run_idf_colinear():
    """Test the Model.to.idf and run_idf method with a model that has colinear vertices."""
    # Get input Model
    input_hb_model = './tests/json/model_colinear_verts.json'
    with open(input_hb_model) as json_file:
        data = json.load(json_file)
    model = Model.from_dict(data)

    # Get the input SimulationParameter
    sim_par = SimulationParameter()
    sim_par.output.add_zone_energy_use()
    ddy_file = './tests/ddy/chicago.ddy'
    sim_par.sizing_parameter.add_from_ddy_996_004(ddy_file)
    sim_par.run_period.end_date = Date(1, 7)

    # create the IDF string for simulation paramters and model
    idf_str = '\n\n'.join((sim_par.to_idf(), model.to.idf(model)))

    # write the final string into an IDF
    idf = os.path.join(folders.default_simulation_folder, 'test_file_colinear', 'in.idf')
    write_to_file(idf, idf_str, True)

    # prepare the IDF for simulation
    epw_file = './tests/simulation/chicago.epw'
    prepare_idf_for_simulation(idf, epw_file)

    # run the IDF through EnergyPlus
    sql, zsz, rdd, html, err = run_idf(idf, epw_file)

    assert os.path.isfile(sql)
    assert os.path.isfile(err)
    err_obj = Err(err)
    assert 'EnergyPlus Completed Successfully' in err_obj.file_contents
