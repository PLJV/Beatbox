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
import geopandas

from shapely.geometry import *

_METERS_TO_DEGREES = 111000
_DEGREES_TO_METERS = (1 / _METERS_TO_DEGREES)


class Vector:
    def __init__(self, *args, **kwargs):
        """Handles file input/output operations for shapefiles \
        using fiona and shapely built-ins and performs select \
        spatial modifications on vector datasets

        Keyword arguments:
        filename= the full path filename to a vector dataset (typically a .shp file)

        Positional arguments:
        1st= if no filname keyword argument was used, attempt to read the first positional argument
        """

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
        """Short-hand wrapper for fiona.open() that assigns class variables for \
         CRS, geometry, and schema.

        Keyword arguments:
        filename= the full path filename to a vector dataset (typically a .shp file)

        Positional arguments:
        1st = if no filename keyword argument is used, treat the first positional argument\
        as the filename
        """
        if 'filename' in list(map(str.lower, kwargs.keys())):
            self._filename = kwargs['filename']
        else:
            try:
                self._filename = args[0]
            except Exception as e:
                raise e

        shape_collection = fiona.open(self._filename)

        try:
            self._crs = shape_collection.crs
            self._crs_wkt = shape_collection.crs_wkt
            self._geometries = shape_collection
            self._schema = shape_collection.schema
        except Exception as e:
            raise e

    def write(self, *args, **kwargs):
        """ wrapper for fiona.open that will write in-class geometry data to disk

        (Optional) Keyword arguments:
        filename -- the full path filename to a vector dataset (typically a .shp file)
        (Optional) Positional arguments:
        1st -- if no keyword argument was used, attempt to .read the first pos argument
        """
        if 'filename' in list(map(str.lower, kwargs.keys())):
            self._filename = kwargs['filename']
        else:
            try:
                self._filename = args[0]
            except Exception as e:
                pass # assume we previously defined a _filename to use for our write()
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

    def copy(self):
        """ simple copy method that creates a new instance of a vector class and assigns \
        default attributes from the parent instance

        Keyword arguments: None

        Positional arguments: None
        """
        _vector_geom = Vector()
        _vector_geom._geometries = self._geometries
        _vector_geom._crs = self._crs
        _vector_geom._crs_wkt = self._crs_wkt
        _vector_geom._schema = self._schema
        return _vector_geom

    def to_collection(self):
        """ return a collection of our geometry data """
        return(self.geometries)

    def to_geopandas(self):
        """ return our spatial data as a geopandas dataframe """
        return geopandas.read_file(self._filename)

    @property
    def filename(self):
        """ decorated getter for our filename """
        return self._filename

    @filename.setter
    def filename(self, *args, **kwargs):
        """ decoratted setter for our filename """
        if 'filename' in list(map(str.lower, kwargs.keys())):
            self._filename = kwargs['filename']
        else:
            try:
                self._filename = args[0]
            except Exception as e:
                raise e

    @property
    def crs(self):
        """ decorated getter for our Coordinate Reference System """
        return(self._crs)

    @crs.setter
    def crs(self, *args):
        """ decorated setter for our Coordinate Reference System

        Keyword arguments: None

        Positional arguments:
        1st = first positional argument is used to assign our class CRS value
        """
        try:
          self._crs = args[0]
        except Exception as e:
          raise e

    @property
    def schema(self):
        """ decorated getter for our schema """
        return(self._schema)

    @schema.setter
    def schema(self, *args):
        """ decorated setter for our schema

        Keyword arguments: None

        Positional arguments:
        1st = first positional argument is used to assign our class schema value
        """
        try:
            self._schema = args[0]
        except Exception:
            self._schema = self._geometries.schema

    @property
    def geometries(self):
        """ decorated getter for our fiona geometries collection """
        return(self._geometries)

    @geometries.setter
    def geometries(self, *args):
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

    def buffer(self, *args, **kwargs):
        """Buffer a shapely geometry collection (or the focal Vector class) by some user-specified \
        distance

        Keyword arguments:
        vector= a Vector object with spatial data
        width= a width value to use for our buffering (in projected units of a given geometry \
        -- typically meters or degrees)

        Positional arguments:
        1st= if no width keyword is provided, the first positional argument is treated as the \
        width parameter
        """
        if 'vector' in list(map(str.lower, kwargs.keys())):
            _vector_geom = kwargs[['vector']]
        else:
            _vector_geom = self.copy()  # spec out a new class to store our buffering results
        if 'width' in list(map(str.lower, kwargs.keys())):
            _width = int(kwargs['width'])
        else:
            try:
                _width = int(args[0])
            except Exception as e:
                raise e
        # check and see if we are working in unit meters or degrees
        if _vector_geom._crs_wkt.find('Degree') > 0:
            _width = _DEGREES_TO_METERS * _width
        # build a schema for our buffering operations
        target_schema = _vector_geom.schema
        target_schema['geometry'] = 'MultiPolygon'
        # iterate our feature geometries and cast the output geometry as
        # a MultiPolygon geometry
        _vector_geom.schema = target_schema
        _vector_geom.geometries = MultiPolygon(
            [shape(ft['geometry']).buffer(_width)
             for ft in _vector_geom.geometries])

        return (_vector_geom)

    @staticmethod
    def convex_hull(vector=None, *args, **kwargs):
        '''
        accepts geopandas gdf as file
        Buffers points, dissolves buffers, assigns unique ids,and...
        Returns convex hull GeoDataFrame
        '''

        #Format for assigning buffers to geometry of a manipulable geodataframe
        windbuff=windsubs
        windbuff['geometry']=windbuff.geometry.buffer(1000,resolution=16)

        #dissolve buffers by explode()
        windbuff.loc[:,"group"] = 1
        dissolved = windbuff.dissolve(by="group")
        gs = dissolved.explode()
        gdf2 = gs.reset_index().rename(columns={0: 'geometry'})
        gdf_out = gdf2.merge(dissolved.drop('geometry', axis=1), left_on='level_0', right_index=True)
        gdf_out = gdf_out.set_index(['level_0', 'level_1']).set_geometry('geometry')
        gdf_out.crs = windbuff.crs
        buff_diss = gdf_out.reset_index()

        #assign unique windfarm ID field to each wind turbine and group them into multi-points based on that

            # 'level_1' is the unique windfarm id in this case
        windsubset_wID = gpd.sjoin(windsubset,buff_diss,how='inner',op='intersects')

        #create convex hulls around the windturbines based on wind farm windsubset, dissolve--> convex hull
        windsubset_farms = windsubset_wID.dissolve(by='level_1')
        hulls = windsubset_farms.convex_hull
        hulls_gdf = gpd.GeoDataFrame(gpd.GeoSeries(hulls))
        hulls_gdf['geometry']=hulls_gdf[0]
        hulls_gdf.crs = {'init': 'epsg:32614'}
        del hulls_gdf[0] #Clean up that weird column in the hulls
        return hulls_gdf

    @staticmethod
    def intersection(vector=None, *args, **kwargs):
        """ Returns the intersection of our focal Vector class with another Vector class """
        pass

    @staticmethod
    def over(vector=None, *args, **kwargs):
        """ Returns a boolean vector of overlapping features of our focal Vector class with another Vector class """
        pass
