
from ..writer import generate_idf_string


class WindowShadeControl(object):

    __slots__ = ('_parent', '_name', '_zone_name', '_shade_type', '_construction',
                 '_schedule')


    def __init__(self, name, shade_type, construction, schedule, ):
        self._parent = None
        self.name = name
        self.shade_type = shade_type
        self.construction = construction
        self.schedule = schedule

    @property
    def name(self):
        return self._name
    @name.setter
    def name(self, value):
        self._name = value

    @property
    def zone_name(self):
        return self._parent.name


    @property
    def shade_type(self):
        return self._shade_type
    @shade_type.setter
    def shade_type(self, value):
        if not((value == 'Exterior') or (value == 'Interior')):
            raise('shade_type not undersootd')
        self._shade_type = value + 'Shade'

    @property
    def construction(self):
        return self._construction
    @construction.setter
    def construction(self, value):
        self._construction = value

    @property
    def schedule(self):
        return self._schedule
    @schedule.setter
    def schedule(self, value):
        self._schedule = value


    def to_idf(self):

        values = [self.name, self.zone_name, 1, self.shade_type, self.construction.name,
         'OnIfScheduleAllows', self.schedule.name, '', 'Yes', 'No', '', '', '', '', '',
        'Sequential', ]


        comments = ['Name', 'Zone Name', 'Shading Control Sequence Number',
                    'Shading Type', 'Name of shaded construction', 'Shading Control Type',
                    'Schedule name', 'Setpoint {W/m2}', 'Shading Control Is Scheduled',
                    'Glare Control Is Active',  'Material Name of Shading Device',
                    'Type of Slat Angle Control for Blinds', 'Slat Angle Schedule Name',
                    'Setpoint 2 {W/m2 or deg C}', 'Daylighting Control Object Name',
                    'Multiple Surface Control Type',]


        for face in  self._parent.faces:
            for aperture in face.apertures:
                values.append(aperture.name)
                comments.append('Fenestration Surface Name')






        idf = generate_idf_string('WindowShadingControl', values, comments) + r'\n' +\
                self.construction.to_idf()


        return generate_idf_string('WindowShadingControl', values, comments)







