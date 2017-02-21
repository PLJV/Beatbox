"""
Setup Script
"""
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
try:
    import versioneer
except ImportError as e:
    print(e)

INSTALL_REQUIRES = ['pandas', 'shapely', 'fiona', 'descartes', 'pyproj', 'geopandas', 'georasters', 'geoplot', 'seaborn']
LONG_DESCRIPTION = ""

setup(name='pljv-python-geospatial',
      version=versioneer.get_version(),
      description='The PLJV Python Spatial Swiss Army Knife',
      license='GPL v.3',
      author='pljv-python-geospatial contributors',
      author_email='kyle.taylor@pljv.org',
      url='http://pljv.org/about',
      long_description=LONG_DESCRIPTION,
      packages=['pljv-python-geospatial'],
      install_requires=INSTALL_REQUIRES,
      cmdclass=versioneer.get_cmdclass())
