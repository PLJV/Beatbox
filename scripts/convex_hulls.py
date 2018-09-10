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

from beatbox import Vector

_DEFAULT_BUFFER_WIDTH = 1000 # default width (in meters) of a geometry for various buffer operations

def fuzzy_convex_hulls(*args, **kwargs):
    """accepts geopandas gdf as SpatialPoints, buffers the point geometries by some distance,
    and than builds a convex hull feature collection from clusters of points within a buffer
    distance
    """
    _point_buffers = kwargs.get('points', args[0])
    _width = kwargs.get('width', args[1]) if (kwargs.get('width', args[1]) is None) else _DEFAULT_BUFFER_WIDTH
    # generate circular point buffers around our SpatialPoints features
    try:
        _point_buffers['geometry'] = _point_buffers.geometry.buffer(
            _width,
            resolution=16
        )
    # assume AttributeErrors are due to args[0] not being a GeoPandas object
    except AttributeError as e:
        # if this is a string, assume that it is a path
        # and try and open it -- otherwise raise an error
        if isinstance(_point_buffers, str):
            _point_buffers = Vector(_point_buffers).to_geopandas()
            _point_buffers['geometry'] = _point_buffers.geometry.buffer(
                _width,
                resolution=16
            )
        else:
            raise e
    except Exception as e:
        raise e
    # dissolve our buffered geometries
    _point_buffers.loc[:,"group"] = 1
    gs = _point_buffers.dissolve(by="group").explode()
    # build a GeoDataFrame from our dissolved buffers
    gdf = gs.reset_index().rename(
        columns={0: 'geometry'}
    )
    gdf = gdf.merge(
        gs.drop('geometry', axis=1),
        left_on='level_0',
        right_index=True
    )
    # 'level_1' is the unique cluster id of points within our buffer geometries
    gdf = gdf.set_index(['level_0', 'level_1']).set_geometry('geometry')
    gdf.crs = _point_buffers.crs
    gdf = gdf.reset_index()
    # assign unique windfarm ID field to each wind turbine and group them into multi-points
    windsubset_wID = gdf.sjoin(
        _point_buffers,
        gs,
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

def affected_playas(hulls_lyr=None,playa_lyr=None):

    '''
    accepts geopandas geodataframe (hulls_lyr) and a .shp (playa_lyr) as inputs
    returns GeoDataFrame of playas with field 'knock_date' updated to date of wind dataset
    release, if playa had not been previously affected. Also writes _copy of original layer
    '''

    playas = gpd.read_file(playa_lyr)
    playas = playas.to_crs({'init': 'epsg:32614'})

    #Find playas that intersect with 'hulls_gdf' and update a date column with the dataset's release IF affected
    playas['knock_date']='null' #add knock_date field, populate w 'null'
    polygons = hulls_lyr.geometry
    polygons = hulls_lyr.loc[hulls['geometry'].geom_type=='Polygon'] #this works officially to trim lines and points
    sj_playas = gpd.sjoin(playas,polygons,how='inner',op='intersects')
    aff_playas = playas.geom_almost_equals(sj_playas)
    aff_playas = aff_playas[~aff_playas.index.duplicated()]
    playas['knock_date'][aff_playas]=playa_lyr[-11:-4] #way to selet only affected playas. seems to work.

    #import

    playas.to_file(playa_lyr[0:-4]+'_copy.shp'))
    return playas

if __name__ == "__main__":
