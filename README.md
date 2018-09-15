### Beatbox
A simple Python wrapper interface for GDAL, GeoRasters, Shapely, and GeoPandas. Beatbox is designed to be a portable interface for working with large spatial datasets on cloud platforms like AWS and Google App Engine / Earth Engine. You install it's standard dependencies with anaconda and/or pip in seconds and produce datasets that can be integrated into common frameworks and distributed computing workflows. PLJV uses beatbox downstream for cloud computing.

*This is still a young project. If you are not a collaborator and just happened onto this repository while looking for ways to crunch geospatial data with Python, **this is probably not your tool**. For vector data, consider [GeoPandas](https://developers.google.com/earth-engine/python_install_manual). For raster data, consider [GeoRasters](https://github.com/ozak/georasters). For spatial workflows and distributed computing, consider [GeoTrellis](https://github.com/locationtech/geotrellis).*  

For an overview of installing the Earth Engine Python API ([RTM](https://developers.google.com/earth-engine/python_install_manual)).

We maintain beatbox and make it publically available (GPLv3) so that our collaborators can check our math. It is still very much under active development and not production ready. For the curious earth systems modeller experimenting with spatial data on Earth Engine or AWS that would like to get their hands dirty, dive in.

### Installation
From a direct download:
```python setup.py install```

From conda / pip:
```bash
conda install pyCrypto GDAL numpy pandas fiona shapely geopandas scikit-learn 

pip install google-api-python-client
pip install earthengine-api

pip uninstall Beatbox
pip install git+git://github.com/PLJV/Beatbox.git
```

### Quickstart
##### using ipython
```python
from beatbox import Do, Vector, Raster, fuzzy_convex_hulls

water_raster = Raster("/path/to/water_raster.tif")
spatial_points = Vector("/path/to/spatialpoints.shp")
convex_hulls = fuzzy_convex_hulls(spatial_points, width=1033)

result = Do({
  'what': extract,
  'with': [ convex_hulls, water_raster ]
})

```
