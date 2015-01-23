"""
running average time series for a given wind, tide, or 
generic time series
"""

import datetime
import os
import copy

import numpy
np = numpy

from colander import (SchemaNode, drop, OneOf,
                      Float, String, Range)
from hazpy import unit_conversion as uc

from gnome.cy_gnome.cy_ossm_time import CyOSSMTime, CyTimeseries
from gnome import basic_types
from gnome.utilities.time_utils import date_to_sec
from gnome.utilities.serializable import Serializable, Field
from gnome.utilities.convert import (to_time_value_pair,
                                     tsformat,
                                     to_datetime_value_2d)
from gnome.persist.extend_colander import (DefaultTupleSchema,
                                           LocalDateTime,
                                           DatetimeValue2dArraySchema)
from gnome.persist import validators, base_schema

from .environment import Environment
from gnome.environment import Wind, WindSchema
from .. import _valid_units


class UVTuple(DefaultTupleSchema):
    'Tide object schema'
    u = SchemaNode(Float())
    v = SchemaNode(Float())


class TimeSeriesTuple(DefaultTupleSchema):
    'Tide object schema'
    '''
    Schema for each tuple in running average Time Series
    '''
    datetime = SchemaNode(LocalDateTime(default_tzinfo=None),
                          default=base_schema.now,
                          validator=validators.convertible_to_seconds)
    uv = UVTuple()


class TimeSeriesSchema(DatetimeValue2dArraySchema):
    'Tide object schema'
    '''
    Schema for list of running average tuples, to make the timeseries
    '''
    value = TimeSeriesTuple(default=(datetime.datetime.now(), 0, 0))

    def validator(self, node, cstruct):
         '''
         validate running average timeseries numpy array
         '''
         validators.no_duplicate_datetime(node, cstruct)
         validators.ascending_datetime(node, cstruct)
         


class RunningAverageSchema(base_schema.ObjType):
    'Time series object schema'

    timeseries = TimeSeriesSchema(missing=drop)
    name = 'running average'
    past_hours_to_average = SchemaNode(Float(), missing=drop)



class RunningAverage(Environment, Serializable):
    '''
    Defines a running average time series for a wind or tide
    '''

    _update = []

    # used to create new obj or as readonly parameter
    _create = []
    _create.extend(_update)

    _state = copy.deepcopy(Environment._state)
    _state += [Field('wind', save=True, update=True, save_reference=True)]
    _state.add(save=_create, update=_update)
    _schema = RunningAverageSchema

#     _state.add_field([serializable.Field('timeseries', save=True,
#                                          update=True)
#                       ])
   # _state['name'].test_for_eq = False

    # list of valid velocity units for timeseries
    #valid_vel_units = _valid_units('Velocity')

    def __init__(self, wind=None, timeseries=None, past_hours_to_average = 3,
                 **kwargs):
        """
        Initializes a running average object from a wind and past hours to average

        If no wind is given, timeseries gets initialized as: # probably should be an error

            timeseries = np.zeros((1,), dtype=basic_types.datetime_value_2d)
            units = 'mps'

        All other keywords are optional. Optional parameters (kwargs):

        :param past_hours_to_average: default is 3

        """
        self.units = 'mps'
        self.format = 'uv'
        self._past_hours_to_average = past_hours_to_average
        self.wind = wind

        if (wind is None and timeseries is None):	
            mvg_timeseries = np.zeros((1,), dtype=basic_types.datetime_value_2d)
            moving_timeseries = self._convert_to_time_value_pair(mvg_timeseries)

        else:
            if wind is not None:
                moving_timeseries = wind.ossm.create_running_average(self._past_hours_to_average)
            else:
                self.wind = Wind(timeseries, units='mps', format = 'uv')
                #time_value_pair = self._convert_to_time_value_pair(timeseries)
                #self.wind.ossm = CyTimeseries(timeseries=time_value_pair)
                moving_timeseries = self.wind.ossm.create_running_average(self._past_hours_to_average)

        #print "moving_timeseries"
        #print moving_timeseries

        #self.ossm = CyOSSMTime(timeseries=moving_timeseries)
        self.ossm = CyTimeseries(timeseries=moving_timeseries)

        super(RunningAverage, self).__init__(**kwargs)



    def __repr__(self):
        self_ts = self.timeseries.__repr__()
        return ('{0.__class__.__module__}.{0.__class__.__name__}('
                'timeseries={1}'
                ')').format(self, self_ts)

    def __str__(self):
        return "Running Average ( timeseries=RunningAverage.get_timeseries('uv'), format='uv')"

    def __eq__(self, other):
        '''
        call super to test for equality of objects for all attributes
        except 'units' and 'timeseries' - test 'timeseries' here by converting
        to consistent units
        '''
        # since this has numpy array - need to compare that as well
        # By default, tolerance for comparison is atol=1e-10, rtol=0
        # persisting data requires unit conversions and finite precision,
        # both of which will introduce a difference between two objects

        check = super(RunningAverage, self).__eq__(other)

        if check:
            sts = self.get_timeseries(units=self.units)
            ots = other.get_timeseries(units=self.units)

            if (sts['time'] != ots['time']).all():
                return False
            else:
                return np.allclose(sts['value'], ots['value'], 0, 1e-2)

        return check

    def __ne__(self, other):
        return not self == other

    @property
    def past_hours_to_average(self):
        return self._past_hours_to_average

    @past_hours_to_average.setter
    def past_hours_to_average(self, value):
        """
        How many hours for running average 

        """
        # may want a check on value
        self._past_hours_to_average = value
        
    @property
    def timeseries(self):
        return self.get_timeseries()

    def _convert_to_time_value_pair(self, datetime_value_2d):
        '''
        fmt datetime_value_2d so it is a numpy array with
        dtype=basic_types.time_value_pair as the C++ code expects
        '''
        # following fails for 0-d objects so make sure we have a 1-D array
        # to work with
        datetime_value_2d = np.asarray(datetime_value_2d,
                                       dtype=basic_types.datetime_value_2d)
        if datetime_value_2d.shape == ():
            datetime_value_2d = np.asarray([datetime_value_2d],
                                           dtype=basic_types.datetime_value_2d)

        #self._check_units(units)
        #self._check_timeseries(datetime_value_2d, units)
#         datetime_value_2d['value'] = \
#             self._convert_units(datetime_value_2d['value'],
#                                 fmt, units, 'meter per second')

        timeval = to_time_value_pair(datetime_value_2d, "uv")
        return timeval

    def get_timeseries(self, datetime=None):
        """
        Returns the timeseries in the requested format. If datetime=None,
        then the original timeseries that was entered is returned.
        If datetime is a list containing datetime objects, then the wind value
        for each of those date times is determined by the underlying
        CyOSSMTime object and the timeseries is returned.

        The output format is defined by the strings 'r-theta', 'uv'

        :param datetime: [optional] datetime object or list of datetime
                         objects for which the value is desired
        :type datetime: datetime object

        :returns: numpy array containing dtype=basic_types.datetime_value_2d.
                  Contains user specified datetime and the corresponding
                  values in 'm/s' and 'uv' format
        """
        if datetime is None:
            datetimeval = to_datetime_value_2d(self.ossm.timeseries, 'uv')
        else:
            datetime = np.asarray(datetime, dtype='datetime64[s]').reshape(-1)
            timeval = np.zeros((len(datetime), ),
                               dtype=basic_types.time_value_pair)
            timeval['time'] = date_to_sec(datetime)
            timeval['value'] = self.ossm.get_time_value(timeval['time'])
            datetimeval = to_datetime_value_2d(timeval, 'uv')

        return datetimeval



    def prepare_for_model_run(self, model_time):
        """
        Make sure we are up to date with the referenced time series
        """
        if self.wind is None:
            err = -1 # raise error here?
            
        model_time = date_to_sec(model_time)
	    
        self.create_running_average_timeseries(self._past_hours_to_average, model_time)

    def prepare_for_model_step(self, model_time):
        """
        Make sure we are up to date with the referenced time series
        """
        model_time = date_to_sec(model_time)
        if self.ossm.check_time_in_range(model_time):
           return
        else: 
            if self.wind.ossm.check_time_in_range(model_time):
                # there is wind data for this time so create a new running average
                self.create_running_average_timeseries(self._past_hours_to_average, model_time)
            
        self.create_running_average_timeseries(self._past_hours_to_average, model_time)

    def create_running_average_timeseries(self, past_hours_to_average, model_time = 0):
        """
        Creates the timeseries of the RunningAverage object

        :param past_hours_to_average: amount of data to use in the averaging
        """
# first get the time series from the C++ function 
        #self.timeseries = wind.ossm.create_running_average(past_hours)
        #do we need to dispose of old one here?
        moving_timeseries = self.wind.ossm.create_running_average(past_hours_to_average, model_time)
        # here should set the timeseries since the CyOSSMTime should already exist
        self.ossm.timeseries=moving_timeseries
        #self.ossm = CyOSSMTime(timeseries=moving_timeseries)


    def get_value(self, time):
        '''
        Return the value at specified time and location. Timeseries are
        independent of location; however, a gridded datafile may require
        location so this interface may get refactored if it needs to support
        different types of data. It assumes the data in SI units (m/s) and 'uv' format

        .. note:: It invokes get_timeseries(..) function
        '''
        if self.ossm.timeseries is None:
            self.create_running_average_timeseries(self.past_hours_to_average)
        #if check on time range here:
            #self.create_running_average_timeseries(self.past_hours, 'm/s', 'uv')
        data = self.get_timeseries(time)
        return tuple(data[0]['value'])

    def serialize(self, json_='webapi'):
        """
        Since 'wind' property is saved as references in save file
        need to add appropriate node to WindMover schema for 'webapi'
        """
        toserial = self.to_serialize(json_)
        schema = self.__class__._schema()
        if json_ == 'webapi':
            if self.wind:
                # add wind schema
                schema.add(WindSchema(name='wind'))

        serial = schema.serialize(toserial)

        return serial

    @classmethod
    def deserialize(cls, json_):
        """
        append correct schema for wind object
        """
        schema = cls._schema()
        if 'wind' in json_:
            schema.add(WindSchema(name='wind'))

        _to_dict = schema.deserialize(json_)

        return _to_dict
        
