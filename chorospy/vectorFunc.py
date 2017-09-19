import os
from osgeo import ogr, osr
import pandas
import random
import math

# for higher accuracy the functions below define a UTM projection based on the lon lat of a point, they are used in the pointToGeo function
def utmGetZone(longitude):
    return (int(1+(longitude+180.0)/6.0))

def utmIsNorthern(latitude):
    if (latitude < 0.0):
        return 0;
    else:
        return 1;

def makeUtmCS(lon, lat):
    utmZone = utmGetZone(lon)
    isNorthern = utmIsNorthern(lat)
    # set utm coordinate system
    utmCs = osr.SpatialReference()
    utmCs.SetWellKnownGeogCS('WGS84')
    utmCs.SetUTM(utmZone,isNorthern)
    return utmCs

#########################################
# function to produce polygons from points
# inPoints is a list of lists e.g. [[[x1,y1], [x2,y2]], [[x3,y3], [x4,y4]]]
# each list of points is saved as a seperate feauture in the final file
#########################################
def pointToGeo(inProj, inPoints, outFile, fields, buffer = False, bufferZone = 50000, convexHull = False, outFormat = 'json'):
    #define projections for the transformation
    inSpatialRef = osr.SpatialReference()
    inSpatialRef.ImportFromEPSG(inProj)
    
    #hierarchy of geo file creation: Driver -> Datasource -> Layer -> Feature -> Geometry ->Polygone
    if outFormat == 'json':
        driver = ogr.GetDriverByName('GeoJSON')
    elif outFormat == 'shp':
        driver = ogr.GetDriverByName('ESRI Shapefile')

    outShape = '{}.{}'.format(outFile, outFormat)

    if os.path.exists(outShape):
        driver.DeleteDataSource(outShape)
    shapeData = driver.CreateDataSource(outShape)

    #Create layer
    layer = shapeData.CreateLayer('clipExtent', inSpatialRef, ogr.wkbMultiPolygon)
    layerDefinition = layer.GetLayerDefn()
    #create fields/properties of features
    for prop in fields.keys():
        fieldName = prop
        fieldType = ogr.OFTString
        propField = ogr.FieldDefn(fieldName, fieldType)
        layer.CreateField(propField)
        
    for i, feat in enumerate(inPoints):
        # create feature
        featureIndex = i
        feature = ogr.Feature(layerDefinition)
        # create geometries
        if buffer == True:
            #create multipolygone to store buffer zones
            outPoly = ogr.Geometry(ogr.wkbMultiPolygon)
            for point in feat:
                coordTransform = osr.CoordinateTransformation(inSpatialRef, makeUtmCS(point[0], point[1])) # transform to UTM
                gps_point = ogr.Geometry(ogr.wkbPoint)
                gps_point.AddPoint(point[0],point[1])
                gps_point.Transform(coordTransform)
                buffPoint = gps_point.Buffer(bufferZone)
                coordTransformReverse = osr.CoordinateTransformation(makeUtmCS(point[0], point[1]), inSpatialRef) # back to WGS84
                buffPoint.Transform(coordTransformReverse)
                outPoly.AddGeometry(buffPoint)
            
            #join overlapping polygones
            outPoly = outPoly.UnionCascaded()
            if convexHull == True:
                # Calculate convex hull
                outPoly = outPoly.ConvexHull()

            # geometry in feature
            feature.SetGeometry(outPoly)
            
            for f in range(layerDefinition.GetFieldCount()):
                proper = layerDefinition.GetFieldDefn(f).GetName()
                feature.SetField(proper, fields[proper][featureIndex])
            
            # feature in layer
            layer.CreateFeature(feature)

        else: #simple polygone from points
            outPoly = ogr.Geometry(ogr.wkbPolygon)
            ring = ogr.Geometry(ogr.wkbLinearRing)

            for point in feat:
                gps_point = ogr.Geometry(ogr.wkbPoint)
                gps_point.AddPoint(point[0],point[1])
                ring.AddPoint(gps_point.GetX(), gps_point.GetY()) #or directly ring.AddPoint(point[0], point[1])

            outPoly.AddGeometry(ring)
            # geometry in feature
            feature.SetGeometry(outPoly)
            # add the defined properties
            for f in range(layerDefinition.GetFieldCount()):
                proper = layerDefinition.GetFieldDefn(f).GetName()
                feature.SetField(proper, fields[proper][featureIndex])

            # feature in layer
            layer.CreateFeature(feature)
            
        #Clean
        outPoly.Destroy()
        feature.Destroy()
    shapeData.Destroy()
        
    print('Geometry file created!')
        
#function for disaggregating occurence points
# distance in degrees
# 100m = 0.001189387868; 1km = 0.008333333333333; 10km = 0.08333333333333
def disaggregate(df,Lon, Lat, dist): 
    train = df.drop_duplicates() #drop dublicates
    finalDF = pandas.DataFrame(columns=[Lon, Lat])
    removedDF = pandas.DataFrame(columns=[Lon, Lat])
    kept = 0
    excl = 0
    
    while len(train) > 1:
        points = len(train)
        #pick a random point in the dataset
        i = random.randrange(0, points, 1)
        #calculate euclidean distance between the random point and all other points (including itself)
        eucl = ((train[Lon] - train[Lon].iloc[i])**2 + (train[Lat] - train[Lat].iloc[i])**2).apply(math.sqrt) 
        #if there exists points with smaller distance, exclude point
        if eucl[eucl <= dist].count() > 1:
            excl+=1
            exclRow = train.loc[i,]
            removedDF = removedDF.append(exclRow, ignore_index=True)
        else:
            kept+=1
            keptRow = train.loc[i,]
            finalDF = finalDF.append(keptRow, ignore_index=True)


        train = train.drop(train.index[i]).reset_index(drop=True)
        
    print('Occurences removed: %s, Occurences kept: %s' %(excl, kept))
    return(finalDF, removedDF)
