"""commands to generate honeybee energy simulation settings."""
import click
import sys
import logging
import json
import os

from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.simulation.runperiod import RunPeriod
from honeybee_energy.simulation.control import SimulationControl
from honeybee.config import folders
from ladybug.futil import preparedir
from ladybug.analysisperiod import AnalysisPeriod
from ladybug.dt import Date

_logger = logging.getLogger(__name__)


@click.group(help='Commands for simulating Honeybee JSON files in EnergyPlus.')
def settings():
    pass


@settings.command('default-sim-par')
@click.argument('ddy-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--run-period-json', '-rp', help='Full path to a honeybee RunPeriod JSON '
              'that describes the duration of the simulation. If not specified, the '
              'simulation will be for the whole year.', default=None, show_default=True,
              type=click.Path(
                  exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--filter-des-days/--all-des-days', ' /-all',  help='Flag to note whether '
              'the design days in the ddy-file should be filtered to only include 99.6 '
              'and 0.4 design days.', default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the JSON string of '
              'the simulation parameters. By default, it will be printed to stdout.',
              type=click.File('w'), default='-', show_default=True)
def default_sim_par(ddy_file, run_period_json, filter_des_days, output_file):
    """Get a SimulationParameter JSON with default outputs for energy use only.

    \b
    Args:
        ddy_file: Full path to a DDY file that will be used to specify design days
            within the simulation parameter.
    """
    try:
        sim_par = SimulationParameter()
        sim_par.output.add_zone_energy_use()
        sim_par.output.add_hvac_energy_use()
        if run_period_json is not None:
            with open(run_period_json) as json_file:
                data = json.load(json_file)
            sim_par.run_period = RunPeriod.from_dict(data)
        if filter_des_days:
            sim_par.sizing_parameter.add_from_ddy_996_004(ddy_file)
        else:
            sim_par.sizing_parameter.add_from_ddy(ddy_file)
        output_file.write(json.dumps(sim_par.to_dict()))
    except Exception as e:
        _logger.exception('Failed to generate simulation parameter.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@settings.command('load-balance-sim-par')
@click.argument('ddy-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--load-type', '-lt', help='A text value to set the type of load outputs '
              'requested. Choose from the following:\nAll - all energy use '
              'including heat lost from the zone\nTotal - the total load added to the '
              'zone (both sensible and latent)\nSensible - the sensible load added to '
              'the zone\nLatent - the latent load added to the zone.',
              type=str, default='Total', show_default=True)
@click.option('--run-period-json', '-rp', help='Full path to a honeybee RunPeriod JSON '
              'that describes the duration of the simulation. If not specified, the '
              'simulation will be for the whole year.', default=None, show_default=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--filter-des-days/--all-des-days', ' /-all',  help='Flag to note whether '
              'the design days in the ddy-file should be filtered to only include 99.6 '
              'and 0.4 design days.', default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the JSON string of '
              'the simulation parameters. By default, it will be printed to stdout.',
              type=click.File('w'), default='-', show_default=True)
def load_balance_sim_par(ddy_file, load_type, run_period_json, filter_des_days,
                         output_file):
    """Get a SimulationParameter JSON with outputs for thermal load balances.

    \b
    Args:
        ddy_file: Full path to a DDY file that will be used to specify design days
            within the simulation parameter.
    """
    try:
        sim_par = SimulationParameter()
        sim_par.output.add_zone_energy_use(load_type)
        gl_load_type = load_type if load_type != 'All' else 'Total'
        sim_par.output.add_gains_and_losses(gl_load_type)
        sim_par.output.add_surface_energy_flow()
        if run_period_json is not None:
            with open(run_period_json) as json_file:
                data = json.load(json_file)
            sim_par.run_period = RunPeriod.from_dict(data)
        if filter_des_days:
            sim_par.sizing_parameter.add_from_ddy_996_004(ddy_file)
        else:
            sim_par.sizing_parameter.add_from_ddy(ddy_file)
        output_file.write(json.dumps(sim_par.to_dict()))
    except Exception as e:
        _logger.exception('Failed to generate simulation parameter.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@settings.command('comfort-sim-par')
@click.argument('ddy-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--run-period-json', '-rp', help='Full path to a honeybee RunPeriod JSON '
              'that describes the duration of the simulation. If not specified, the '
              'simulation will be for the whole year.', default=None, show_default=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--filter-des-days/--all-des-days', ' /-all',  help='Flag to note whether '
              'the design days in the ddy-file should be filtered to only include 99.6 '
              'and 0.4 design days.', default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the JSON string of '
              'the simulation parameters. By default, it will be printed to stdout.',
              type=click.File('w'), default='-', show_default=True)
def comfort_sim_par(ddy_file, run_period_json, filter_des_days, output_file):
    """Get a SimulationParameter JSON with outputs for thermal comfort mapping.

    \b
    Args:
        ddy_file: Full path to a DDY file that will be used to specify design days
            within the simulation parameter.
    """
    try:
        sim_par = SimulationParameter()
        sim_par.output.add_comfort_metrics()
        sim_par.output.add_surface_temperature()
        if run_period_json is not None:
            with open(run_period_json) as json_file:
                data = json.load(json_file)
            sim_par.run_period = RunPeriod.from_dict(data)
        if filter_des_days:
            sim_par.sizing_parameter.add_from_ddy_996_004(ddy_file)
        else:
            sim_par.sizing_parameter.add_from_ddy(ddy_file)
        output_file.write(json.dumps(sim_par.to_dict()))
    except Exception as e:
        _logger.exception('Failed to generate simulation parameter.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@settings.command('sizing-sim-par')
@click.argument('ddy-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.option('--load-type', '-lt', help='A text value to set the type of load outputs '
              'requested. Choose from the following:\nAll - all energy use '
              'including heat lost from the zone\nTotal - the total load added to the '
              'zone (both sensible and latent)\nSensible - the sensible load added to '
              'the zone\nLatent - the latent load added to the zone.',
              type=str, default='Total', show_default=True)
@click.option('--filter-des-days/--all-des-days', ' /-all',  help='Flag to note whether '
              'the design days in the ddy-file should be filtered to only include 99.6 '
              'and 0.4 design days.', default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the JSON string of '
              'the simulation parameters. By default, it will be printed to stdout.',
              type=click.File('w'), default='-', show_default=True)
def sizing_sim_par(ddy_file, load_type, filter_des_days, output_file):
    """Get a SimulationParameter JSON with outputs and run period for HVAC sizing.

    \b
    Args:
        ddy_file: Full path to a DDY file that will be used to specify design days
            within the simulation parameter.
    """
    try:
        sim_par = SimulationParameter()
        sim_par.output.add_zone_energy_use(load_type)
        gl_load_type = load_type if load_type != 'All' else 'Total'
        sim_par.output.add_gains_and_losses(gl_load_type)
        sim_par.output.add_surface_energy_flow()
        sim_par.simulation_control = SimulationControl(True, True, True, True, False)
        if filter_des_days:
            sim_par.sizing_parameter.add_from_ddy_996_004(ddy_file)
        else:
            sim_par.sizing_parameter.add_from_ddy(ddy_file)
        output_file.write(json.dumps(sim_par.to_dict()))
    except Exception as e:
        _logger.exception('Failed to generate simulation parameter.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@settings.command('custom-sim-par')
@click.argument('ddy-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('output-names', nargs=-1)
@click.option('--run-period-json', '-rp', help='Full path to a honeybee RunPeriod JSON '
              'that describes the duration of the simulation. If not specified, the '
              'simulation will be for the whole year.', default=None, show_default=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--filter-des-days/--all-des-days', ' /-all',  help='Flag to note whether '
              'the design days in the ddy-file should be filtered to only include 99.6 '
              'and 0.4 design days.', default=True, show_default=True)
@click.option('--output-file', '-f', help='Optional file to output the JSON string of '
              'the simulation parameters. By default, it will be printed to stdout.',
              type=click.File('w'), default='-', show_default=True)
def custom_sim_par(ddy_file, output_names, run_period_json, filter_des_days,
                   output_file):
    """Get a SimulationParameter JSON with an option for custom outputs.

    \b
    Args:
        ddy_file: Full path to a DDY file that will be used to specify design days
            within the simulation parameter.
        output_names: Any number of EnergyPlus output names as strings (eg.
            'Surface Window System Solar Transmittance'. These outputs will be
            requested from the simulation.
    """
    try:
        sim_par = SimulationParameter()
        for output_name in output_names:
            sim_par.output.add_output(output_name)
        if run_period_json is not None:
            with open(run_period_json) as json_file:
                data = json.load(json_file)
            sim_par.run_period = RunPeriod.from_dict(data)
        if filter_des_days:
            sim_par.sizing_parameter.add_from_ddy_996_004(ddy_file)
        else:
            sim_par.sizing_parameter.add_from_ddy(ddy_file)
        output_file.write(json.dumps(sim_par.to_dict()))
    except Exception as e:
        _logger.exception('Failed to generate simulation parameter.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@settings.command('orientation-sim-pars')
@click.argument('ddy-file', type=click.Path(
    exists=True, file_okay=True, dir_okay=False, resolve_path=True))
@click.argument('north-angles', nargs=-1, type=float)
@click.option('--output-name', '-o', help='Any number of EnergyPlus output names as '
              'strings (eg. Surface Window System Solar Transmittance). These outputs '
              'will be requested from the simulation.',
              type=click.STRING, multiple=True, default=None, show_default=True)
@click.option('--run-period-json', '-rp', help='Full path to a honeybee RunPeriod JSON '
              'that describes the duration of the simulation. If not specified, the '
              'simulation will be for the whole year.', default=None, show_default=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False,
                              resolve_path=True))
@click.option('--filter-des-days/--all-des-days', ' /-all',  help='Flag to note whether '
              'the design days in the ddy-file should be filtered to only include 99.6 '
              'and 0.4 design days.', default=True, show_default=True)
@click.option('--folder', '-f', help='Output folder for the simulation parameter JSONS.',
              default=None, show_default=True,
              type=click.Path(file_okay=False, dir_okay=True, resolve_path=True))
@click.option('--log-file', '-log', help='Optional log file to output the paths of the '
              'simulation parameters. By default the list will be printed out to stdout.',
              type=click.File('w'), default='-')
def orientation_sim_pars(ddy_file, north_angles, output_name, run_period_json,
                         filter_des_days, folder, log_file):
    """Get SimulationParameter JSONs with different north angles for orientation studies.

    \b
    Args:
        ddy_file: Full path to a DDY file that will be used to specify design days
            within the simulation parameter.
        north_angles: Any number of values between -360 and 360 for the counterclockwise
            difference between the North and the positive Y-axis in degrees. 90 is
            West and 270 is East.
    """
    try:
        # get a default folder if none was specified
        if folder is None:
            folder = os.path.join(folders.default_simulation_folder, 'orientation_study')
        preparedir(folder, remove_content=False)

        # create a base set of simulation parameters to be edited parametrically
        sim_par = SimulationParameter()
        for out_name in output_name:
            sim_par.output.add_output(out_name)
        if run_period_json is not None:
            with open(run_period_json) as json_file:
                data = json.load(json_file)
            sim_par.run_period = RunPeriod.from_dict(data)
        if filter_des_days:
            sim_par.sizing_parameter.add_from_ddy_996_004(ddy_file)
        else:
            sim_par.sizing_parameter.add_from_ddy(ddy_file)

        # loop through the north angles and write a simulation parameter for each
        json_files = []
        for angle in north_angles:
            sim_par.north_angle = angle
            base_name = 'sim_par_north_{}'.format(int(angle))
            file_name = '{}.json'.format(base_name)
            file_path = os.path.join(folder, file_name)
            with open(file_path, 'w') as fp:
                json.dump(sim_par.to_dict(), fp)
            sp_info = {
                'id': base_name,
                'path': file_name,
                'full_path': os.path.abspath(file_path)
            }
            json_files.append(sp_info)
        log_file.write(json.dumps(json_files))
    except Exception as e:
        _logger.exception('Failed to generate simulation parameters.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)


@settings.command('run-period')
@click.argument('start-month', type=int)
@click.argument('start-day', type=int)
@click.argument('end-month', type=int)
@click.argument('end-day', type=int)
@click.option('--start-day-of-week', '-dow', help='Text for the day of the week on which '
              'the simulation starts.', type=str, default='Sunday', show_default=True)
@click.option('--holidays', '-h', help='Text for the holidays within the simulation. '
              'Dates should be formatted as follows: "[day int] [month text]" '
              '(eg. "25 Dec"). If not specified, no holidays are applied.',
              type=str, default=None, show_default=True, multiple=True)
@click.option('--output-file', '-f', help='Optional file to output the JSON string of '
              'the run period. By default, it will be printed to stdout.',
              type=click.File('w'), default='-', show_default=True)
def run_period(start_month, start_day, end_month, end_day, start_day_of_week,
               holidays, output_file):
    """Get a RunPeriod JSON that can be used to set the simulation run period.

    \b
    Args:
        start_month: Start month (1-12).
        start_day: Start day (1-31).
        end_month: End month (1-12).
        end_day: End day (1-31).
    """
    try:
        # create the run period
        a_period = AnalysisPeriod(start_month, start_day, 0, end_month, end_day, 23)
        run_period = RunPeriod.from_analysis_period(a_period)
        # set the start day of the week if it is input
        if start_day_of_week is not None:
            run_period.start_day_of_week = start_day_of_week.title()
        # set the holidays if requested.
        if holidays:
            dates = tuple(Date.from_date_string(date) for date in holidays)
            run_period.holidays = dates
        output_file.write(json.dumps(run_period.to_dict()))
    except Exception as e:
        _logger.exception('Failed to generate run period.\n{}'.format(e))
        sys.exit(1)
    else:
        sys.exit(0)
