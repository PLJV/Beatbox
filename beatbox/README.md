### Beatbox Core
This contains most of the core functionality for beatbox, including : Raster  and Vector I/O and conversion, as well as 
backend task handlers like convex hull generation, feature dissolving, and raster extraction. We use classes sparingly 
and (hidden) functions liberally. Our design goal is to make a framework that's simple and robust to changes 
in upstream dependencies like Earth Engine and GeoPandas. 
