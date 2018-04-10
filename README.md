# chorospy

The chorospy (choros = space, place, location) package contains a set a functions for creating and manipulating vector and raster data, common tasks in research fields like spatial ecology, biodiversity conservation etc.

## Prerequisites
The modules are written in Python 3 and are based on GDAL v2. It is preferred to run the modules in an isolated python environment (see https://docs.python.org/3/library/venv.html).
Apart from a system-wide installation of GDAL (http://www.gdal.org/), the following python packages should also be already installed:
osgeo, pandas, numpy

## Examples

Download the chorospy package and define it's directory
```python
import sys 
sys.path.append('pathTochorospyFolder/')

import chorospy
```

### Points to polygone(s)
The function below creates a geojson file (see http://geojson.org/) with two features. Each feature is a multipolygone
that consists of three buffer zones (50km is the default value) created from the input points.
The id's of the two features are geom_1 and geom_2 respectively.
```python
inPoints = [[[0, 10],[0, 20], [10,20]], 
            [[30,40],[30, 45],[35, 30]]]
chorospy.pointToGeo(inProj = 4326, inPoints = inPoints, outFile = 'test', fields = {'id': ['geom_1','geom_2']}, buffer = True)
```
If both the buffer and the convexHull arguments are set to True the function will create a convex hull of the buffer zones.
```python
chorospy.pointToGeo(inProj = 4326, inPoints = inPoints, outFile = 'test', fields = {'id': ['geom_1','geom_2']}, buffer = True, convexHull = True)
```

When the buffer argument buffer is left to the default value (false) the same function creates polygones with edges corresponding to the provided points. Using the same dataset as above
the function below will create two simple polygones.
```python
chorospy.pointToGeo(inProj = 4326, inPoints = inPoints, outFile = 'test', fields = {'id': ['geom_1','geom_2']}, outFormat = 'shp')
```

### Filter points
The following function disaggregates points closer than one kilometer (0.008333333333333 degrees). 'x' and 'y' are the name of the columns with Longitude and Latitude data.
```python
import pandas
inPoints = pandas.read_csv('myPointFile.csv')
filteredPoints, removedPoints = chorospy.disaggregate(inPoints, 'x', 'y', 0.008333333333333)
```

### Create polygon grid (fishnet)
Creating a regularly-spaced grid (fishnet) is a common task in physical geography. The following function creates a vector file
with polygons representing the cells of the grid. We can define the spatial extent of the grid, the cell edge size and the projection (in proj4 format).
Additionally, we can let the function readjust the cell dimensions so that the grid fits precisely to the defined extent. The function supports two vector formats,
json and shp. For this example, we create a grid of approximately 500 by 500 km cells at the Lambert cylindrical equal-area projection. The four numbers after the 
file name define xmin, ymin, xmax, ymax. When the spherical argument is set to true, the features are represented with spherical coordinates in the final vector file.
```python
proj4 = '+proj=laea +lat_0=45.5 +lon_0=-114.125 +x_0=0 +y_0=0 +a=6371007.181 +b=6371007.181 +units=km +no_defs'

chorospy.createFishNet('lambert.json', -17367.500000, -7332.944361, 17367.499600, 7332.944359, 500, 500, proj4, adjustGrid=True, spherical = False)
```


### Get raster values
The function below extracts values of rasters for the provided coordinates. The function takes a set of rasters and a set of points 
(i.e. a pandas dataframe with the point coordinates) as inputs and returns a new pandas data frame with the same point coordinates
(the centroids of the cells are also calculated and printed) and the values of the rasters for each point. Raster format should be 
geotif. The first argument defines the directory where the rasters are located. The names in the inRaster list correspond to the 
raster names, e.g. bio3.tif and bio6.tif.
```python
inRasters = ['bio3', 'bio6']
rsValues = chorospy.getValuesAtPoint('.', inRasters, filteredPoints, 'x', 'y')
rsValues.to_csv('rsValues.csv', index=False)
```

The function below extracts all values of rasters and provides the centroid of each cell.
```python
inRasters = ['bio3', 'bio6']
rsValues = chorospy.getRasterValues('.', inRasters)
rsValues.to_csv('rsValues.csv', index=False)
```

### Create reference raster
Assessing the spatial aspects of biodiversity usually requires the definition of a grid on which spatial calculations will be conducted.
The following function can create a raster file of any size and extent. The user can define the extent both in spherical and in cartesian coordinates.
The user can additionally define the projection and a clip vector for the final raster. 
In this example, we create a raster file (refRaster.tif) with 350km cell resolution at the standard parallels (i.e cell area is 122.5 square kilometers)
at a cylindrical equal-area projection projection (Behrmann) and at global extent. The properties of this family of projections (i.e. north-south compression is precisely the reciprocal of east-west stretching)
allow us to define a grid that consists of cells of equal area. The cells have random values (cellValues = 'random') that range from 0 to 1000 (default).
For the clipping (inVector), we first have to reproject the 10m natural earth land file at the Behrmann projection (ne_10m_land_Behrmann.shp).
```bash
ogr2ogr -t_srs '+proj=cea +lon_0=0 +lat_ts=30 +x_0=0 +y_0=0 +datum=WGS84 +ellps=WGS84 +units=m +no_defs' ne_10m_land_Berhmann.shp ne_10m_land.shp
```
and then in python
```python
chorospy.createRaster('refRaster.tif',
                      xmin = -180, ymin = -90, 
                      xmax = 180, ymax = 90,
                       pixelSize = 350000, coordinates = 'spherical',
                      proj = '+proj=cea +lon_0=0 +lat_ts=30 +x_0=0 +y_0=0 +datum=WGS84 +ellps=WGS84 +units=m +no_defs',
                      cellValues = 'random',
                      inVector = 'ne_10m_land_Berhmann.shp',
                      rasterizeOptions = ['ALL_TOUCHED=FALSE'])
```


### Filter raster file
In some cases, a researcher may want to exclude some cells from downstream spatial analyses, based on the coverage of these cells
by some natural features (e.g. water). The function below modifies a raster file based on the coverage by water. The water bodies are
given as features (geojson file) and the cells of the raster file that are covered by more than 50% (arbitrary number) of water are
assigned a nan value. The function returns an array that is subsequently saved as a new raster.
```python
#first, let's create a raster that covers the specified extent at the specified resolution (0.00833333). By default the cells of the rasters are random numbers in [0,1].
#if the inVector optional argument is defined (e.g. inVector = 'test.shp'), the raster will be clipped by the features of the input vector file.
chorospy.createRaster('cells.tif', [10, 55, 20, 60], 0.0833333, inVector = None)
#then run the function
filteredArray = chorospy.filterByCoverage('output.json', 'cells.tif', 50)
#and finally export the array to a raster file. 
chorospy.array2raster('cellsFiltered.tif', 'cells.tif', filteredArray, -9999, 'float32')
```

### Create raster of species richness / occurrence density
Given a list of species and their occurrences, one can create a species richness map at the desirable resolution. The following function
takes a data frame with species occurrences and a vector file defining the extent and boarders of the map, and creates a raster file whose cell values
represent the number of species in the respective cell. Only the occurrences that fall within the extent of the vector file will be considered.
Occurrences that fall outside the boarders (the coastline in our example) will be printed in the screen.
```python
#first, let's create a pseudo data set using 10000 random species occurrences for 10 species. In this case the center of diversity is located at 15N, 60E somewhere in Sweden
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
    df1, rem = chorospy.disaggregate(df, 'species', 'x', 'y', 0.08333333)
    DF = pandas.concat([DF, df1])
DF.reset_index(drop = True, inplace = True)

#now let's create the raster ('test.tif'). The last argument is the no data value
chorospy.makeDensityRaster(DF, 'sweden.json', 0.08333333, 'test.tif', -9999)
```

Note: The same function  can be used to create an occurrence density map (e.g. for a single species) without disaggregating the occurrences.
