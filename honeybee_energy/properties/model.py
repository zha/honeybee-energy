# coding=utf-8
"""Model Energy Properties."""
from honeybee.extensionutil import model_extension_dicts

from ..lib.constructionsets import generic_construction_set

from ..material.opaque import EnergyMaterial, EnergyMaterialNoMass
from ..material.glazing import EnergyWindowMaterialGlazing, \
    EnergyWindowMaterialSimpleGlazSys
from ..material.gas import EnergyWindowMaterialGas, \
    EnergyWindowMaterialGasMixture, EnergyWindowMaterialGasCustom
from ..material.shade import EnergyWindowMaterialShade, EnergyWindowMaterialBlind
from ..construction.opaque import OpaqueConstruction
from ..construction.window import WindowConstruction
from ..construction.shade import ShadeConstruction
from ..constructionset import ConstructionSet
from ..programtype import ProgramType
from ..schedule.typelimit import ScheduleTypeLimit
from ..schedule.ruleset import ScheduleRuleset
from ..schedule.fixedinterval import ScheduleFixedInterval
from ..writer import generate_idf_string

try:
    from itertools import izip as zip  # python 2
except ImportError:
    pass   # python 3


class ModelEnergyProperties(object):
    """Energy Properties for Honeybee Model.

    Properties:
        * host
        * terrain_type
        * materials
        * constructions
        * face_constructions
        * shade_constructions
        * construction_sets
        * global_construction_set
        * schedule_type_limits
        * schedules
        * shade_schedules
        * room_schedules
        * program_types
    """
    TERRAIN_TYPES = ('Ocean', 'Country', 'Suburbs', 'Urban', 'City')

    def __init__(self, host, terrain_type='City'):
        """Initialize Model energy properties.

        Args:
            host: A honeybee_core Model object that hosts these properties.
            terrain_type: Text for the terrain type in which the model sits.
                Choose from: 'Ocean', 'Country', 'Suburbs', 'Urban', 'City'.
                Default: 'City'.
        """
        self._host = host
        self.terrain_type = terrain_type

    @property
    def host(self):
        """Get the Model object hosting these properties."""
        return self._host

    @property
    def terrain_type(self):
        """Get or set a text string for the terrain in which the model sits.

        This is used to determine the wind profile over the height of the
        building. Default is 'City'. Choose from the following options:
            * Ocean
            * Country
            * Suburbs
            * Urban
            * City
        """
        return self._terrain_type

    @terrain_type.setter
    def terrain_type(self, value):
        if value is not None:
            assert value in self.TERRAIN_TYPES, 'Input terrain_type "{}" is ' \
                'not valid. Choose from the following options:\n{}'.format(
                    value, self.TERRAIN_TYPES)
            self._terrain_type = value
        else:
            self._terrain_type = 'City'

    @property
    def materials(self):
        """List of all unique materials contained within the model.

        This includes materials across all Faces, Apertures, Doors, Room
        ConstructionSets, and the global_construction_set.
        """
        materials = []
        for constr in self.constructions:
            try:
                materials.extend(constr.materials)
            except AttributeError:
                pass  # ShadeConstruction
        return list(set(materials))

    @property
    def constructions(self):
        """A list of all unique constructions in the model.

        This includes constructions across all Faces, Apertures, Doors, Shades,
        Room ConstructionSets, and the global_construction_set.
        """
        room_constrs = []
        for cnstr_set in self.construction_sets:
            room_constrs.extend(cnstr_set.modified_constructions_unique)
        # all_constrs = self.global_construction_set.constructions_unique + \
            # room_constrs + self.face_constructions + self.shade_constructions
        return list(set(self.face_constructions)) + self.with_shade_construction  # Modification 1: only return constructions that are used

    @property
    def face_constructions(self):
        """A list of all unique constructions assigned to Faces, Apertures and Doors."""
        constructions = []
        for room in self.host.rooms:
            for face in room.faces:  # check all Face constructions
                self._check_and_add_obj_construction(face, constructions)
                for ap in face.apertures:  # check all Aperture constructions
                    self._check_and_add_obj_construction(ap, constructions)
                for dr in face.doors:  # check all Door constructions
                    self._check_and_add_obj_construction(dr, constructions)


        return list(set(constructions))

    @property
    def shade_constructions(self):
        """A list of all unique constructions assigned to Shades in the model."""
        constructions = []
        for shade in self.host.orphaned_shades:
            self._check_and_add_obj_construction(shade, constructions)
        for room in self.host.rooms:
            for shade in room.shades:
                self._check_and_add_obj_construction(shade, constructions)
            for face in room.faces:  # check all Face constructions
                for shade in face.shades:
                    self._check_and_add_obj_construction(shade, constructions)
                for ap in face.apertures:  # check all Aperture constructions
                    for shade in ap.shades:
                        self._check_and_add_obj_construction(shade, constructions)
        return list(set(constructions))

    @property
    def with_shade_construction(self):
        with_shade_construction = []
        for room in self.host.rooms:
            if room.properties.energy.shade_control is not None:
                with_shade_construction.append(room.properties.energy.shade_control.construction)
        return list(set(with_shade_construction))

    @property
    def construction_sets(self):
        """A list of all unique Room-Assigned ConstructionSets in the Model."""
        construction_sets = []
        for room in self.host.rooms:
            if room.properties.energy._construction_set is not None:
                if not self._instance_in_array(room.properties.energy._construction_set,
                                               construction_sets):
                    construction_sets.append(room.properties.energy._construction_set)
        return list(set(construction_sets))  # catch equivalent construction sets

    @property
    def global_construction_set(self):
        """A default ConstructionSet object for all unassigned objects in the Model.

        This ConstructionSet will be written in its entirety to the dictionary
        representation of ModelEnergyProperties as well as the resulting OpenStudio
        model.  This is to ensure that all objects lacking a construction specification
        always have a default.
        """
        return generic_construction_set

    @property
    def schedule_type_limits(self):
        """List of all unique schedule type limits contained within the model.

        This includes schedules across all Shades and Rooms.
        """
        type_limits = []
        for sched in self.schedules:
            t_lim = sched.schedule_type_limit
            if t_lim is not None and not self._instance_in_array(t_lim, type_limits):
                type_limits.append(t_lim)
        return list(set(type_limits))

    @property
    def schedules(self):
        """A list of all unique schedules in the model.

        This includes schedules across all ProgramTypes, Rooms, and Shades.
        """
        p_type_scheds = []
        for p_type in self.program_types:
            for sched in p_type.schedules:
                self._check_and_add_schedule(sched, p_type_scheds)
        all_scheds = p_type_scheds + self.room_schedules + self.shade_schedules
        return list(set(all_scheds))

    @property
    def shade_schedules(self):
        """A list of all unique transmittance schedules assigned to Shades in the model.
        """
        schedules = []
        for shade in self.host.orphaned_shades:
            self._check_and_add_shade_schedule(shade, schedules)
        for room in self.host.rooms:
            for shade in room.shades:
                self._check_and_add_shade_schedule(shade, schedules)
            for face in room.faces:  # check all Face schedules
                for shade in face.shades:
                    self._check_and_add_shade_schedule(shade, schedules)
                for ap in face.apertures:  # check all Aperture schedules
                    for shade in ap.shades:
                        self._check_and_add_shade_schedule(shade, schedules)
        return list(set(schedules))

    @property
    def room_schedules(self):
        """A list of all unique schedules assigned directly to Rooms in the model.

        Note that this does not include schedules from ProgramTypes assigned to the
        rooms.
        """
        scheds = []
        for room in self.host.rooms:
            people = room.properties.energy._people
            lighting = room.properties.energy._lighting
            electric_equipment = room.properties.energy._electric_equipment
            gas_equipment = room.properties.energy._gas_equipment
            infiltration = room.properties.energy._infiltration
            ventilation = room.properties.energy._ventilation
            setpoint = room.properties.energy._setpoint
            hvac = room.properties.energy._hvac
            shade_control = room.properties.energy.shade_control
            if people is not None:
                self._check_and_add_schedule(people.occupancy_schedule, scheds)
                self._check_and_add_schedule(people.activity_schedule, scheds)
            if lighting is not None:
                self._check_and_add_schedule(lighting.schedule, scheds)
            if electric_equipment is not None:
                self._check_and_add_schedule(electric_equipment.schedule, scheds)
            if gas_equipment is not None:
                self._check_and_add_schedule(gas_equipment.schedule, scheds)
            if infiltration is not None:
                self._check_and_add_schedule(infiltration.schedule, scheds)
            if ventilation is not None and ventilation.schedule is not None:
                self._check_and_add_schedule(ventilation.schedule, scheds)
            if setpoint is not None:
                self._check_and_add_schedule(setpoint.heating_schedule, scheds)
                self._check_and_add_schedule(setpoint.cooling_schedule, scheds)
                if setpoint.humidifying_schedule is not None:
                    self._check_and_add_schedule(
                        setpoint.humidifying_schedule, scheds)
                    self._check_and_add_schedule(
                        setpoint.dehumidifying_schedule, scheds)
            if hvac is not None:
                self._check_and_add_schedule(hvac.heating_availability_schedule, scheds)
                self._check_and_add_schedule(hvac.cooling_availability_schedule, scheds)

            if shade_control is not None:
                self._check_and_add_schedule(shade_control.schedule, scheds)

        return list(set(scheds))

    @property
    def program_types(self):
        """A list of all unique ProgramTypes in the Model."""
        program_types = []
        for room in self.host.rooms:
            if room.properties.energy._program_type is not None:
                if not self._instance_in_array(room.properties.energy._program_type,
                                               program_types):
                    program_types.append(room.properties.energy._program_type)
        return list(set(program_types))  # catch equivalent program types

    def building_idf(self, solar_distribution='FullInteriorAndExteriorWithReflections'):
        """Get an IDF string for Building that this model represents.

        Args:
            solar_distribution: Text desribing how EnergyPlus should treat beam solar
                radiation reflected from surfaces. Default:
                FullInteriorAndExteriorWithReflections. Choose from the following:
                    * MinimalShadowing
                    * FullExterior
                    * FullInteriorAndExterior
                    * FullExteriorWithReflections
                    * FullInteriorAndExteriorWithReflections
        """
        values = (self.host.name,
                  self.host.north_angle,
                  self.terrain_type,
                  '',
                  '',
                  solar_distribution)
        comments = ('name',
                    'north axis',
                    'terrain',
                    'loads convergence tolerance',
                    'temperature convergence tolerance',
                    'solar distribution')
        return generate_idf_string('Building', values, comments)

    def check_duplicate_material_names(self, raise_exception=True):
        """Check that there are no duplicate Material names in the model."""
        material_names = set()
        duplicate_names = set()
        for mat in self.materials:
            if mat.name not in material_names:
                material_names.add(mat.name)
            else:
                duplicate_names.add(mat.name)
        if len(duplicate_names) != 0:
            if raise_exception:
                raise ValueError(
                    'The model has the following duplicated Material '
                    'names:\n{}'.format('\n'.join(duplicate_names)))
            return False
        return True

    def check_duplicate_construction_names(self, raise_exception=True):
        """Check that there are no duplicate Construction names in the model."""
        cnstr_names = set()
        duplicate_names = set()
        for cnstr in self.constructions:
            if cnstr.name not in cnstr_names:
                cnstr_names.add(cnstr.name)
            else:
                duplicate_names.add(cnstr.name)
        if len(duplicate_names) != 0:
            if raise_exception:
                raise ValueError(
                    'The model has the following duplicated Construction '
                    'names:\n{}'.format('\n'.join(duplicate_names)))
            return False
        return True

    def check_duplicate_construction_set_names(self, raise_exception=True):
        """Check that there are no duplicate ConstructionSet names in the model."""
        con_set_names = set()
        duplicate_names = set()
        for con_set in self.construction_sets + [self.global_construction_set]:
            if con_set.name not in con_set_names:
                con_set_names.add(con_set.name)
            else:
                duplicate_names.add(con_set.name)
        if len(duplicate_names) != 0:
            if raise_exception:
                raise ValueError(
                    'The model has the following duplicated ConstructionSet '
                    'names:\n{}'.format('\n'.join(duplicate_names)))
            return False
        return True

    def check_duplicate_schedule_type_limit_names(self, raise_exception=True):
        """Check that there are no duplicate ScheduleTypeLimit names in the model."""
        sched_type_limit_names = set()
        duplicate_names = set()
        for t_lim in self.schedule_type_limits:
            if t_lim.name not in sched_type_limit_names:
                sched_type_limit_names.add(t_lim.name)
            else:
                duplicate_names.add(t_lim.name)
        if len(duplicate_names) != 0:
            if raise_exception:
                raise ValueError(
                    'The model has the following duplicated ScheduleTypeLimit '
                    'names:\n{}'.format('\n'.join(duplicate_names)))
            return False
        return True

    def check_duplicate_schedule_names(self, raise_exception=True):
        """Check that there are no duplicate Schedule names in the model."""
        sched_names = set()
        duplicate_names = set()
        for sched in self.schedules:
            if sched.name not in sched_names:
                sched_names.add(sched.name)
            else:
                duplicate_names.add(sched.name)
        if len(duplicate_names) != 0:
            if raise_exception:
                raise ValueError(
                    'The model has the following duplicated Schedule '
                    'names:\n{}'.format('\n'.join(duplicate_names)))
            return False
        return True

    def check_duplicate_program_type_names(self, raise_exception=True):
        """Check that there are no duplicate ProgramType names in the model."""
        p_type_names = set()
        duplicate_names = set()
        for p_type in self.program_types:
            if p_type.name not in p_type_names:
                p_type_names.add(p_type.name)
            else:
                duplicate_names.add(p_type.name)
        if len(duplicate_names) != 0:
            if raise_exception:
                raise ValueError(
                    'The model has the following duplicated ProgramType '
                    'names:\n{}'.format('\n'.join(duplicate_names)))
            return False
        return True

    def apply_properties_from_dict(self, data):
        """Apply the energy properties of a dictionary to the host Model of this object.

        Args:
            data: A dictionary representation of an entire honeybee-core Model.
                Note that this dictionary must have ModelEnergyProperties in order
                for this method to successfully apply the energy properties.
        """
        assert 'energy' in data['properties'], \
            'Dictionary possesses no ModelEnergyProperties.'

        # set the terrain
        if 'terrain_type' in data['properties']['energy']:
            self.terrain_type = data['properties']['energy']['terrain_type']

        # process all materials in the ModelEnergyProperties dictionary
        materials = {}
        for mat in data['properties']['energy']['materials']:
            if mat['type'] == 'EnergyMaterial':
                materials[mat['name']] = EnergyMaterial.from_dict(mat)
            elif mat['type'] == 'EnergyMaterialNoMass':
                materials[mat['name']] = EnergyMaterialNoMass.from_dict(mat)
            elif mat['type'] == 'EnergyWindowMaterialSimpleGlazSys':
                materials[mat['name']] = EnergyWindowMaterialSimpleGlazSys.from_dict(mat)
            elif mat['type'] == 'EnergyWindowMaterialGlazing':
                materials[mat['name']] = EnergyWindowMaterialGlazing.from_dict(mat)
            elif mat['type'] == 'EnergyWindowMaterialGas':
                materials[mat['name']] = EnergyWindowMaterialGas.from_dict(mat)
            elif mat['type'] == 'EnergyWindowMaterialGasMixture':
                materials[mat['name']] = EnergyWindowMaterialGasMixture.from_dict(mat)
            elif mat['type'] == 'EnergyWindowMaterialGasCustom':
                materials[mat['name']] = EnergyWindowMaterialGasCustom.from_dict(mat)
            elif mat['type'] == 'EnergyWindowMaterialShade':
                materials[mat['name']] = EnergyWindowMaterialShade.from_dict(mat)
            elif mat['type'] == 'EnergyWindowMaterialBlind':
                materials[mat['name']] = EnergyWindowMaterialBlind.from_dict(mat)
            else:
                raise NotImplementedError(
                    'Material {} is not supported.'.format(mat['type']))

        # process all constructions in the ModelEnergyProperties dictionary
        constructions = {}
        for cnstr in data['properties']['energy']['constructions']:
            if cnstr['type'] == 'OpaqueConstructionAbridged':
                mat_layers = [materials[mat_name] for mat_name in cnstr['layers']]
                constructions[cnstr['name']] = \
                    OpaqueConstruction(cnstr['name'], mat_layers)
            elif cnstr['type'] == 'WindowConstructionAbridged':
                mat_layers = [materials[mat_name] for mat_name in cnstr['layers']]
                constructions[cnstr['name']] = \
                    WindowConstruction(cnstr['name'], mat_layers)
            elif cnstr['type'] == 'ShadeConstruction':
                constructions[cnstr['name']] = ShadeConstruction.from_dict(cnstr)
            else:
                raise NotImplementedError(
                    'Construction {} is not supported.'.format(cnstr['type']))

        # process all construction sets in the ModelEnergyProperties dictionary
        construction_sets = {}
        for c_set in data['properties']['energy']['construction_sets']:
            construction_sets[c_set['name']] = \
                ConstructionSet.from_dict_abridged(c_set, constructions)

        # process all schedule type limits in the ModelEnergyProperties dictionary
        schedule_type_limits = {}
        for t_lim in data['properties']['energy']['schedule_type_limits']:
            schedule_type_limits[t_lim['name']] = ScheduleTypeLimit.from_dict(t_lim)

        # process all schedules in the ModelEnergyProperties dictionary
        schedules = {}
        for sched in data['properties']['energy']['schedules']:
            sched = sched.copy()  # copy the original dictionary so that we don't edit it
            # process the schedule type limits
            typ_lim = None
            if 'schedule_type_limit' in sched:
                typ_lim = sched['schedule_type_limit']
                sched['schedule_type_limit'] = None
            # create the schedule objects
            if sched['type'] == 'ScheduleRulesetAbridged':
                sched['type'] = 'ScheduleRuleset'
                schedules[sched['name']] = ScheduleRuleset.from_dict(sched)
            elif sched['type'] == 'ScheduleFixedIntervalAbridged':
                sched['type'] = 'ScheduleFixedInterval'
                schedules[sched['name']] = ScheduleFixedInterval.from_dict(sched)
            else:
                raise NotImplementedError(
                    'Schedule {} is not supported.'.format(sched['type']))
            # asign the schedule type limits
            schedules[sched['name']].schedule_type_limit = \
                schedule_type_limits[typ_lim] if typ_lim is not None else None

        # process all ProgramType in the ModelEnergyProperties dictionary
        program_types = {}
        if 'program_types' in data['properties']['energy']:
            for p_typ in data['properties']['energy']['program_types']:
                program_types[p_typ['name']] = \
                    ProgramType.from_dict_abridged(p_typ, schedules)

        # collect lists of energy property dictionaries
        room_e_dicts, face_e_dicts, shd_e_dicts, ap_e_dicts, dr_e_dicts = \
            model_extension_dicts(data, 'energy')

        # apply energy properties to objects uwing the energy property dictionaries
        for room, r_dict in zip(self.host.rooms, room_e_dicts):
            room.properties.energy.apply_properties_from_dict(
                r_dict, construction_sets, program_types, schedules)
        for face, f_dict in zip(self.host.faces, face_e_dicts):
            face.properties.energy.apply_properties_from_dict(f_dict, constructions)
        for shade, s_dict in zip(self.host.shades, shd_e_dicts):
            shade.properties.energy.apply_properties_from_dict(
                s_dict, constructions, schedules)
        for aperture, a_dict in zip(self.host.apertures, ap_e_dicts):
            aperture.properties.energy.apply_properties_from_dict(a_dict, constructions)
        for aperture, a_dict in zip(self.host.apertures, ap_e_dicts):
            aperture.properties.energy.apply_properties_from_dict(a_dict, constructions)

    def to_dict(self, include_global_construction_set=True):
        """Return Model energy properties as a dictionary.

        include_global_construction_set: Boolean to note whether the
            global_construction_set should be included within the dictionary. This
            will ensure that all objects lacking a construction specification always
            have a default construction. Default: True.
        """
        base = {'energy': {'type': 'ModelEnergyProperties'}}

        # add the terrain
        base['energy']['terrain_type'] = self.terrain_type

        # add all ConstructionSets to the dictionary
        base['energy']['construction_sets'] = []
        if include_global_construction_set:
            base['energy']['global_construction_set'] = self.global_construction_set.name
            base['energy']['construction_sets'].append(
                self.global_construction_set.to_dict(abridged=True,
                                                     none_for_defaults=False))
        construction_sets = self.construction_sets
        for cnstr_set in construction_sets:
            base['energy']['construction_sets'].append(cnstr_set.to_dict(abridged=True))

        # add all unique Constructions to the dictionary
        room_constrs = []
        for cnstr_set in construction_sets:
            room_constrs.extend(cnstr_set.modified_constructions_unique)
        all_constrs = room_constrs + self.face_constructions + self.shade_constructions
        if include_global_construction_set:
            all_constrs.extend(self.global_construction_set.constructions_unique)
        constructions = list(set(all_constrs))
        base['energy']['constructions'] = []
        for cnst in constructions:
            try:
                base['energy']['constructions'].append(cnst.to_dict(abridged=True))
            except TypeError:  # ShadeConstruction
                base['energy']['constructions'].append(cnst.to_dict())

        # add all unique Materials to the dictionary
        materials = []
        for cnstr in constructions:
            try:
                materials.extend(cnstr.materials)
            except AttributeError:
                pass  # ShadeConstruction
        base['energy']['materials'] = [mat.to_dict() for mat in set(materials)]

        # add all unique program types to the dictionary
        program_types = self.program_types
        base['energy']['program_types'] = []
        for p_type in program_types:
            base['energy']['program_types'].append(p_type.to_dict(abridged=True))

        # add all unique Schedules to the dictionary
        p_type_scheds = []
        for p_type in program_types:
            for sched in p_type.schedules:
                self._check_and_add_schedule(sched, p_type_scheds)
        all_scheds = p_type_scheds + self.room_schedules + self.shade_schedules
        schedules = list(set(all_scheds))
        base['energy']['schedules'] = []
        for sched in schedules:
            base['energy']['schedules'].append(sched.to_dict(abridged=True))

        # add all unique ScheduleTypeLimits to the dictionary
        type_limits = []
        for sched in schedules:
            t_lim = sched.schedule_type_limit
            if t_lim is not None and not self._instance_in_array(t_lim, type_limits):
                type_limits.append(t_lim)
        base['energy']['schedule_type_limits'] = \
            [s_typ.to_dict() for s_typ in set(type_limits)]

        return base

    def duplicate(self, new_host=None):
        """Get a copy of this object.

        new_host: A new Model object that hosts these properties.
            If None, the properties will be duplicated with the same host.
        """
        _host = new_host or self._host
        return ModelEnergyProperties(_host, self.terrain_type)

    def _check_and_add_obj_construction(self, obj, constructions):
        """Check if a construction is assigned to an object and add it to a list."""
        constr = obj.properties.energy._construction
        if constr is not None:
            if not self._instance_in_array(constr, constructions):
                constructions.append(constr)

    def _check_and_add_shade_schedule(self, obj, schedules):
        """Check if a schedule is assigned to a shade and add it to a list."""
        sched = obj.properties.energy._transmittance_schedule
        if sched is not None:
            if not self._instance_in_array(sched, schedules):
                schedules.append(sched)

    def _check_and_add_schedule(self, load_sched, schedules):
        """Check if a schedule is in a list and add it if not."""
        if not self._instance_in_array(load_sched, schedules):
            schedules.append(load_sched)

    @staticmethod
    def _instance_in_array(object_instance, object_array):
        """Check if a specific object instance is already in an array.

        This can be much faster than  `if object_instance in object_arrary`
        when you expect to be testing a lot of the same instance of an object for
        inclusion in an array since the builtin method uses an == operator to
        test inclusion.
        """
        for val in object_array:
            if val is object_instance:
                return True
        return False

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Model Energy Properties:\n host: {}'.format(self.host.name)
