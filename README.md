# geospatial-tools

The geospatial-tools.py privides a set a functions for creating and manipulating vector and raster data useful in a variety of research fields such as spatial ecology, physical geography etc. 

## Prerequisites
The functions are written in Python 3 and are based on GDAL 2. Ideally the user should run the functions in an isolated python environment (see https://docs.python.org/3/library/venv.html) 
The following python packages should be installed:
osgeo, pandas, numpy


## Examples

The function below creates a geojson file with two features. Each feature is a multipolygone that consists of three buffer zones (50km is the default value) created from the input points
The id's of the two features are geom_1 and geom_2 respectively
```python
inPoints = [[[0, 10],[0, 20], [10,20], \
            [[30,40],[30, 45],[35, 30]]]
pointToGeo(inProj = 4326, inPoints = inPoints, outFile = 'test', fields = {'id': ['geom_1','geom_2']}, buffer = True)
```

The function below creates a shp file with two features. Each feature is a polygone with edges corresponding to the provided points
```python
pointToGeo(inProj = 4326, inPoints = inPoints, outFile = 'test', fields = {'id': ['geom_1','geom_2']}, outFormat = 'shp')
```

The function below disaggregates points closer than one kilometer (0.008333333333333 degrees). 'x' and 'y' are the name of the columns with Longitude and Latitude data
```python
inPoints = pandas.read_csv('myPointFile.csv')
filteredPoints, removedPoints = geo_functions.disaggregate(inPoints, 'x', 'y', 0.008333333333333)
```

The function below extracts values of rasters for the given points. The function takes a set of rasters and a point pandas dataframe as inputs and returns a new pandas data frame with the point coordinates
(the centroids of the cells are also calculated) and the values of the rasters for each point. Raster format should be geotif. The first argument defines the directory where the rasters are located. The names in the inRaster list correspond to the raster names, e.g. bio3.tif and bio6.tif.
```python
inRasters = ['bio3', 'bio6']
rsValues = getValuesAtPoint('.', inRasters, filteredPoints, 'x', 'y')
rsValues.to_csv('rsValues.csv', index=False)
```

The function below extracts all values of rasters and provides the centroid of each cell.
```python
inRasters = ['bio3', 'bio6']
rsValues = getValuesAtPoint('.', inRasters)
rsValues.to_csv('rsValues.csv', index=False)
```