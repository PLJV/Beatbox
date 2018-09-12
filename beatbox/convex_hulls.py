#!/usr/bin/python3
"""
__author__ = ["Kyle Taylor", "Stephen Chang"]
__copyright__ = "Copyright 2017, Playa Lakes Joint Venture"
__credits__ = ["Stephen Chang", "Kyle Taylor"]
__license__ = "GPL"
__version__ = "3"
__maintainer__ = "Kyle Taylor"
__email__ = "kyle.taylor@pljv.org"
__status__ = "Testing"
"""
import logging
import numpy as np
import geopandas as gp

from beatbox import Vector
from copy import copy
from scipy.sparse.csgraph import connected_components

_DEFAULT_BUFFER_WIDTH: int = 1000  # default width (in meters) of a geometry for various buffer operations
_METERS_TO_DEGREES: float = 111000
_DEGREES_TO_METERS: float = (1 / _METERS_TO_DEGREES)
_ARRAY_MAX: int = 1000 # maximum array length to attempt numpy operations on before chunking

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _chunks(*args):
    """
    hidden function
    :param args:
    :return:
    """
    _array = args[0]
    _n_chunks = args[1]
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(_array), _n_chunks):
        yield _array[i:i + _n_chunks]


def _dissolve_overlapping_geometries(*args, **kwargs):
    """
    hidden function
    :param args:
    :param kwargs:
    :return:
    """
    _buffers = kwargs.get('buffers', args[0]) if \
        (kwargs.get('buffers', args[0]) is not None) \
        else None
    # force casting as a GeoDataFrame
    try:
        _buffers = gp.GeoDataFrame({
            'geometry': _buffers
        })
    except ValueError as e:
        if isinstance(_buffers, gp.GeoDataFrame):
            pass
        else:
            raise e
    except Exception as e:
        raise e
    # determine appropriate groupings for our overlapping buffers
    if len(_buffers) > _ARRAY_MAX:
        logger.warning("Attempting dissolve operation on a large vector dataset -- processing in %s chunks, "
                       "which may lead to artifacts at boundaries", split)
        split = round(_buffers.size / _ARRAY_MAX) + 1
        chunks = list(_chunks(_buffers, split))
        chunks = [_buffers.geometry.overlaps(x).values.astype(int) for i, d in enumerate(chunks) for x in d]
        overlap_matrix = np.concatenate(chunks)
        overlap_matrix.shape = (len(_buffers), len(_buffers))
    else:
        overlap_matrix = np.concatenate(
            [_buffers.geometry.overlaps(x).values.astype(int) for x in _buffers]
        )
        overlap_matrix.shape = (len(_buffers), len(_buffers))
    # merge attributes
    n, ids = connected_components(overlap_matrix)
    dissolved_buffers = gp.GeoDataFrame({
        'geometry': _buffers.geometry,
        'group': ids
    })
    # call geopandas dissolve with our 'ids' column and
    dissolved_buffers = dissolved_buffers.dissolve(by='group')
    dissolved_buffers.crs = _buffers.crs
    return dissolved_buffers


def _attribute_by_overlap(*args, **kwargs):
    """
    hidden function that will use the group attribute from polygon features to classify
    point geometries -- this is intended to be used as a 'fuzzy' point
    classifier for point features entering a convex hull
    :param args:
    :param kwargs:
    :return:
    """
    _buffers = kwargs.get('buffers', args[0]) if \
        (kwargs.get('buffers', args[0]) is not None)\
        else None
    _points = kwargs.get('points', args[1]) if \
        (kwargs.get('points', args[1]) is not None)\
        else None
    # dissolve-by explode
    gdf_out = _dissolve_overlapping_geometries(_buffers)
    # return the right-sided spatial join
    return gp.\
        sjoin(_points, gdf_out, how='inner', op='intersects').\
        dissolve(by='level_1')

def convex_hull(*args, **kwargs):
    """
    accepts point features as a GeoDataFrame and uses geopandas to
    calulate a convex hull from the geometries
    :param args:
    :param kwargs:
    :return: GeoDataFrame
    """
    # try and handle our lone 'points' argument
    attr_err_msg = "points= input is invalid. try passing" \
                   " a GeoDataFrame or Vector object."
    try:
        _points = kwargs.get('points', args[0])
        if isinstance(_points, gp.GeoDataFrame):
            pass
        elif isinstance(_points, Vector):
            _points = _points.to_geodataframe()
        else:
            raise AttributeError(attr_err_msg)
    except AttributeError:
        raise AttributeError(attr_err_msg)
    except Exception as e:
        raise e

    return _points.convex_hull()

def fuzzy_convex_hulls(*args, **kwargs):
    """
    accepts geopandas datatframe as SpatialPoints, buffers the point geometries by some distance,
    and than builds a convex hull feature collection from clusters of points
    :param args:
    :param kwargs:
    :return:
    """
    _points = kwargs.get('points', args[0]) if (kwargs.get('points', args[0]) is not None)\
        else None
    _width = kwargs.get('width', args[1]) if (kwargs.get('width', args[1]) is not None) \
        else _DEFAULT_BUFFER_WIDTH
    # generate circular point buffers around our SpatialPoints features
    try:
        _point_buffers = copy(_points)
        if _point_buffers.crs['units'].find('meter') > 0:
            _point_buffers = _point_buffers.buffer(_width)
        else:
            _point_buffers = _point_buffers.buffer(_width / _METERS_TO_DEGREES)
    # assume AttributeErrors are due to args[0] not being a GeoPandas object
    except AttributeError as e:
        # if this is a string, assume that it is a path
        # and try and open it -- otherwise raise an error
        if isinstance(_points, str):
            _points = Vector(_points).to_geodataframe()
            _point_buffers = copy(_points)
            if _point_buffers.crs['units'].find('meter') > 0:
                _point_buffers = _point_buffers.buffer(_width)
            else:
                _point_buffers = _point_buffers.buffer(_width/_METERS_TO_DEGREES)
        else:
            raise e
    except Exception as e:
        raise e
    # dissolve our buffered geometries
    point_clusters = _attribute_by_overlap(_point_buffers, _points)

    # build a GeoDataFrame from our dissolved buffers
    gdf = point_clusters.merge(
        _point_buffers.drop('geometry', axis=1),
        left_on='level_0',
        right_index=True
    )
    # 'level_1' is the unique cluster id of points within our buffer geometries
    gdf = gdf.set_index(['level_0', 'level_1']).set_geometry('geometry')
    gdf.crs = _point_buffers.crs
    gdf = gdf.reset_index()
    # assign unique windfarm ID field to each wind turbine and group them into multi-points
    windsubset_wID = gp.sjoin(
        _points,
        gdf,
        how='inner',
        op='intersects'
    )
    #create convex hulls around the windturbines based on wind farm windsubset, dissolve--> convex hull
    windsubset_farms = windsubset_wID.dissolve(by='level_1')
    hulls = windsubset_farms.convex_hull
    hulls_gdf = gpd.GeoDataFrame(gpd.GeoSeries(hulls))
    hulls_gdf['geometry']=hulls_gdf[0]
    hulls_gdf.crs = {'init': 'epsg:32614'}
    del hulls_gdf[0] #Clean up that weird column in the hulls
    return hulls_gdf


if __name__ == "__main__":
    pass
