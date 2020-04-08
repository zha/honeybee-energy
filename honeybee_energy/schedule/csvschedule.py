
from honeybee._lockable import lockable

@lockable
class CSVSchedule(object):
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
    __slots__ = ('_name', '_path', '_schedule_type_limit', '_locked')


    def __init__(self, name, path, schedule_type_limit):
        self.name = name
        self.path = path
        self.schedule_type_limit = schedule_type_limit

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, value):
        self._path = value

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
        length = max(len(self.schedule_type_limit.name), len(self.path), len(self.name))
        string = f"""Schedule:File,
           {self.name + ',':<{length}}!- Name
           {self.schedule_type_limit.name + ',':<{length}}!- ScheduleType
           {self.path + ',':<{length}}!- Name of File
           {'1' + ',':<{length}}!- Column Number
           {'0' + ',':<{length}}!- Rows to Skip at Top
           {'8760' + ',':<{length}}!- Number of Hours of Data
           {',' + ';':<{length}}!- Column Separator"""
        return string, None
