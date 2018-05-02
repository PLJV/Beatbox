#!/usr/bin/python3
"""
__author__ = "Kyle Taylor"
__copyright__ = "Copyright 2018, Playa Lakes Joint Venture"
__credits__ = ["Kyle Taylor", "Alex Daniels", "Meghan Bogaerts", "Stephen Chang"]
__license__ = "GPL"
__version__ = "3"
__maintainer__ = "Kyle Taylor"
__email__ = "kyle.taylor@pljv.org"
__status__ = "Testing"
"""

import fiona

from shapely.geometry import *
from copy import copy

_METERS_TO_DEGREES = 111000
_DEGREES_TO_METERS = (1 / _METERS_TO_DEGREES)


class Vector:
    def __init__(self, *args, **kwargs):
        """Handles file input/output operations for shapefiles
        using fiona and shapely built-ins"""

        self._geometries = []
        self._filename = []
        self._schema = []
        self._crs = []
        self._crs_wkt = []

        if 'filename' in list(map(str.lower, kwargs.keys())):
            self.read(kwargs['filename'])
        else:
            try:
                self.read(args[0])
            # user doesn't really have to initialize with a filename
            # they can use our setter later
            except Exception:
                pass

    def read(self, *args, **kwargs):
        """Short-hand wrapper for fiona.open()."""
        if 'filename' in list(map(str.lower, kwargs.keys())):
            self.filename = kwargs['filename']
        else:
            try:
                self.filename = args[0]
            except Exception:
                pass

        shape_collection = fiona.open(self._filename)

        try:
            self.crs = shape_collection.crs
            self._crs_wkt = shape_collection.crs_wkt
            self.geometries = shape_collection
            self.schema = shape_collection.schema
        except Exception as e:
            raise e

    def write(self):
        try:
            # call fiona to write our geometry to disk
            with fiona.open(
                    self._filename,
                    'w',
                    'ESRI Shapefile',
                    crs=self._crs,
                    schema=self._schema) as shape:
                # If there are multiple geometries, put the "for" loop here
                shape.write({
                    'geometry': mapping(self._geometries),
                    'properties': {'id': 123},
                })
        except Exception as e:
            raise e

    def to_collection(self):
      return(self.geometries)

    def to_geopandas(self):
        pass

    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, *args, **kwargs):
        if 'filename' in list(map(str.lower, kwargs.keys())):
            self._filename = kwargs['filename']
        else:
            try:
                self._filename = args[0]
            except Exception as e:
                raise e

    @property
    def crs(self):
        return(self._crs)

    @crs.setter
    def crs(self, *args, **kwargs):
        if 'crs' in list(map(str.lower, kwargs.keys())):
            self._crs = kwargs['crs']
        else:
            # assume the schema is the first positional arg
            try:
                self._crs = args[0]
            # no positional arg? try to extract a schema from _geometries
            except Exception as e:
                raise e

    @property
    def schema(self):
        return(self._schema)

    @schema.setter
    def schema(self, *args, **kwargs):
        # by default, use the feature geometry schema passed by the user -- if
        # there wasn't one passed, use what we pull from our input geometry
        if 'schema' in list(map(str.lower, kwargs.keys())):
            self._schema = kwargs['schema']
        else:
            # assume the schema is the third positional arg
            try:
                self._schema = args[0]
            # no positional arg? try to extract a schema from _geometries
            except Exception:
                self._schema = self._geometries.schema

    @property
    def geometries(self):
        return(self._geometries)

    @geometries.setter
    def geometries(self, *args, **kwargs):
        if 'geometries' in list(map(str.lower, kwargs.keys())):
            self._geometries = kwargs['geometries']
        else:
            try:
                self._geometries = args[0]
            except Exception as e:
                raise e
        # default behavior is to accept shapely geometry as input, but a
        # user may pass a string path to a shapefile and we will handle the input
        # and write it to output -- this is essentially a file copy operation
        try:
            self.read(self._geometries)
        # did you pass an incorrect filename?
        except OSError as e:
            raise e
        # it can't be a string path -- assume is a Collection or Geometry object
        # and pass it on
        except Exception:
            pass
        # is this a full Collection that we need to extract geometries from?
        try:
            self._geometries = [Shape(ft['geometry'])
                for ft in self._geometries]
            if self._schema['geometry'] == 'Polygon':
                self._geometries = MultiPolygon(self._geometries)
                self._schema['geometry'] = 'MultiPolygon'
            elif self._schema['geometry'] == 'Point':
                self._geometries = MultiPoint(self._geometries)
                self._schema['geometry'] = 'MultiPoint'
            elif self._schema['geometry'] == 'Line':
                self._geometries = MultiLine(self._geometries)
                self._schema['geometry'] = 'MultiLine'
        # can't read()? assume this is a Geometry and pass it on
        except Exception:
            pass

    @classmethod
    def buffer(vector, *args, **kwargs):
        """Buffer a shapely geometry collection by some user-specified
        distance"""
        if 'width' in list(map(str.lower, kwargs.keys())):
            _width = int(kwargs['width'])
        else:
            try:
                _width = int(args[1])
            except Exception as e:
                raise e
        # check and see if we are working in unit meters or degrees
        if vector._crs_wkt.find('Degree') > 0:
            _width = _DEGREES_TO_METERS * _width
        # build a schema for our buffering operations
        target_schema = vector.schema
        target_schema['geometry'] = 'MultiPolygon'
        # iterate our feature geometries and cast the output geometry as
        # a MultiPolygon geometry
        vector.schema = target_schema
        vector.geometries = MultiPolygon(
            [shape(ft['geometry']).buffer(_width)
             for ft in vector.geometries])

        return (vector)
    @classmethod
    def convex_hull(vector, *args, **kwargs): 
        pass
