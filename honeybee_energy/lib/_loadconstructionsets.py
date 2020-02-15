"""Load all construction sets from the JSON libraries."""
from honeybee_energy.config import folders
from honeybee_energy.constructionset import ConstructionSet

from ._loadconstructions import _opaque_constructions, _window_constructions, \
    _shade_constructions

import os
import json


# empty dictionaries to hold json-loaded construction sets
_all_constructions = _opaque_constructions.copy()  # start with opaque constructions
_all_constructions.update(_window_constructions)  # add window constructions
_all_constructions.update(_shade_constructions)  # add shade constructions

_construction_sets = {}


# load construction sets from the default and user-supplied files
for f in os.listdir(folders.constructionset_lib):
    f_path = os.path.join(folders.constructionset_lib, f)
    if os.path.isfile(f_path) and f_path.endswith('.json'):
        with open(f_path, 'r') as json_file:
            c_dict = json.load(json_file)
        for c_name in c_dict:
            try:
                constructionset = ConstructionSet.from_dict_abridged(
                    c_dict[c_name], _all_constructions)
                constructionset.lock()
                _construction_sets[constructionset.name] = constructionset
            except ValueError:
                pass  # failed to find the construction in the construction library
