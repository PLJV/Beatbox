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

import geopandas as gp
from scipy.sparse.csgraph import connected_components

from beatbox import Vector

_DEFAULT_BUFFER_WIDTH = 1000 # default width (in meters) of a geometry for various buffer operations

def _dissolve_by_explode(buffers):
    # assign an arbitrary group to all of our
    # input polygons and dissolve
    buffers.loc[:, "group"] = 1
    dissolved_buffers = buffers.dissolve(by="group")
    # now explode the dissolve from a multipart geometry into
    # individual Polygons
    dissolved_buffers = dissolved_buffers.\
        explode().\
        reset_index().rename(columns={0: 'geometry'})
    # merge attributes
    gdf_out = dissolved_buffers.merge(buffers.drop('geometry', axis=1), left_on='level_0', right_index=True)
    gdf_out = gdf_out.set_index(['level_0', 'level_1']).set_geometry('geometry')
    gdf_out.crs = buffers.crs
    gdf_out = gdf_out.reset_index()
    return gdf_out

def _attribute_by_overlap(buffers, points):
    # dissolve-by explode
    gdf_out = _dissolve_by_explode(buffers)
    # return the right-sided spatial join
    return gp.\
        sjoin(points, gdf_out, how='inner', op='intersects').\
        dissolve(by='level_1')


def fuzzy_convex_hulls(*args, **kwargs):
    """accepts geopandas datatframe as SpatialPoints, buffers the point geometries by some distance,
    and than builds a convex hull feature collection from clusters of points
    """
    _points = kwargs.get('points', args[0])
    _width = kwargs.get('width', args[1]) if (kwargs.get('width', args[1]) is not None) else _DEFAULT_BUFFER_WIDTH
    # generate circular point buffers around our SpatialPoints features
    try:
        _point_buffers = _points
        _point_buffers['geometry'] = _points.geometry.buffer(_width)
    # assume AttributeErrors are due to args[0] not being a GeoPandas object
    except AttributeError as e:
        # if this is a string, assume that it is a path
        # and try and open it -- otherwise raise an error
        if isinstance(_points, str):
            _points = Vector(_points).to_geopandas()
            _point_buffers = _points
            _point_buffers = _point_buffers.geometry.buffer(_width)
        else:
            raise e
    except Exception as e:
        raise e
    # dissolve our buffered geometries
    #_point_buffers.loc[:,"group"] = 1
    # unary union of overlapping buffer geometries
    point_clusters = _attribute_by_overlap(_point_buffers, _points)

    # build a GeoDataFrame from our dissolved buffers
    gdf = clusters.merge(
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
