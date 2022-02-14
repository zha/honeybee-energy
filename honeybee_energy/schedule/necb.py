from honeybee._lockable import lockable
import json
from pathlib import Path
import os
@lockable
class NECB(object):
    """Schedule for a single day.

    Note that a ScheduleDay cannot be assigned to Rooms, Shades, etc.  The ScheduleDay
    must be added to a ScheduleRuleset or a ScheduleRule and then the ScheduleRuleset
    can be applied to such objects.

    Properties:
        name
        times
        values
        interpolate
        is_constant
    """
    __slots__ = ('_name', '_zone_type', '_schedule_keyword', '_schedule_type_limit', '_locked')


    def __init__(self, name, zone_type, schedule_keyword, schedule_type_limit):
        self.name = name
        self.zone_type = zone_type
        self.schedule_keyword = schedule_keyword
        self.schedule_type_limit = schedule_type_limit

    @property
    def schedule_keyword(self):
        return self._schedule_keyword

    @schedule_keyword.setter
    def schedule_keyword(self, value):
        self._schedule_keyword = value

    @property
    def zone_type(self):
        return self._zone_type

    @zone_type.setter
    def zone_type(self, value):
        self._zone_type = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def schedule_type_limit(self):
        return self._schedule_type_limit

    @schedule_type_limit.setter
    def schedule_type_limit(self, value):
        self._schedule_type_limit = value

    def to_idf(self):

        with open(os.path.join(Path(__file__).parent, "necb.json"), 'r') as f:
            necb_dictionary = json.load(f)
        return necb_dictionary[self.zone_type][self.schedule_keyword], None


        pass
        # length = max(len(self.schedule_type_limit.name), len(self.path), len(self.name))
        # string = f"""Schedule:File,
        #    {self.name + ',':<{length}}!- Name
        #    {self.schedule_type_limit.name + ',':<{length}}!- ScheduleType
        #    {self.path + ',':<{length}}!- Name of File
        #    {'1' + ',':<{length}}!- Column Number
        #    {'0' + ',':<{length}}!- Rows to Skip at Top
        #    {'8760' + ',':<{length}}!- Number of Hours of Data
        #    {',' + ';':<{length}}!- Column Separator"""
        # return string, None
