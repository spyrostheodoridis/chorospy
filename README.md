# spatiopy

The spatiopy package contains a set a functions for creating and manipulating vector and raster data, common tasks in research fields like spatial ecology, biodiversity conservation etc.

## Prerequisites
The modules are written in Python 3 and are based on GDAL 2. It is preferred to run the modules in an isolated python environment (see https://docs.python.org/3/library/venv.html).
Apart from a system-wide installation of GDAL (http://www.gdal.org/), the following python packages should also be already installed:
osgeo, pandas, numpy

## Examples

Download the spatiopy package and define local directory
```python
import sys 
sys.path.append('pathtospatiopypackage/')

import spatiopy
```

### Points to polygone(s)
The function below creates a geojson file with two features. Each feature is a multipolygone
that consists of three buffer zones (50km is the default value) created from the input points.
The id's of the two features are geom_1 and geom_2 respectively.
```python
inPoints = [[[0, 10],[0, 20], [10,20]], 
            [[30,40],[30, 45],[35, 30]]]
spatiopy.pointToGeo(inProj = 4326, inPoints = inPoints, outFile = 'test', fields = {'id': ['geom_1','geom_2']}, buffer = True)
```

The function below creates a shp file with two features. Each feature is a polygone with edges corresponding to the provided points.
```python
spatiopy.pointToGeo(inProj = 4326, inPoints = inPoints, outFile = 'test', fields = {'id': ['geom_1','geom_2']}, outFormat = 'shp')
```

### Filter points
The following function disaggregates points closer than one kilometer (0.008333333333333 degrees). 'x' and 'y' are the name of the columns with Longitude and Latitude data
```python
import pandas
inPoints = pandas.read_csv('myPointFile.csv')
filteredPoints, removedPoints = spatiopy.disaggregate(inPoints, 'x', 'y', 0.008333333333333)
```

### Get raster values
The function below extracts values of rasters for the given points. The function takes a set of rasters and a set of points 
(i.e. a pandas dataframe with the point coordinates) as inputs and returns a new pandas data frame with the same point coordinates
(the centroids of the cells are also calculated and printed) and the values of the rasters for each point. Raster format should be 
geotif. The first argument defines the directory where the rasters are located. The names in the inRaster list correspond to the 
raster names, e.g. bio3.tif and bio6.tif.
```python
inRasters = ['bio3', 'bio6']
rsValues = spatiopy.getValuesAtPoint('.', inRasters, filteredPoints, 'x', 'y')
rsValues.to_csv('rsValues.csv', index=False)
```

The function below extracts all values of rasters and provides the centroid of each cell.
```python
inRasters = ['bio3', 'bio6']
rsValues = spatiopy.getRasterValues('.', inRasters)
rsValues.to_csv('rsValues.csv', index=False)
```

### Create raster of species richness / occurrence density
Given a list of species and their occurrences, one can create a species richness map the desirable resolution. The following function
takes a data frame with species occurrences and a vector file defining the extent of the map, and creates a raster file whose cell values
represent the number of species in the respective cell.
```python
#let's create first a pseudo data set using random species - points pairs. In this case the center of diversity is located at 15N, 60E somewhere in Sweden
import random
import pandas
spOcc = []
for i in range(10000):
    spOcc.append({'species': 'sp_{}'.format(random.randint(1,10)), 'x': random.normalvariate(15, 1), 'y': random.normalvariate(60, 1)})

sp = pandas.DataFrame(spOcc)

#disaggregate the points for each species. We use a 10km distance (0.08333333). The same number will be used to define the raster resolution 
DF = pandas.DataFrame()
for species in sp.species.unique():
    df = sp[sp.species == species]
    df.reset_index(drop = True, inplace = True)
    df1, rem = spatiopy.disaggregate(df, 'species', 'x', 'y', 0.08333333)
    DF = pandas.concat([DF, df1])
DF.reset_index(drop = True, inplace = True)

#now let's create the raster ('test.tif'). The last argument is the no data value
spatiopy.makeDensityRaster(DF, 'full_north.json', 0.08333333, 'test.tif', -9999)
