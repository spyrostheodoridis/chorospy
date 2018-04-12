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
# each list of points is saved as a separate feature in the final file
#########################################
def pointToGeo(inProj, inPoints, outFile, layerName, fields, buffer = False, bufferZone = 50000, convexHull = False, outFormat = 'json'):
    #define projections for the transformation
    inSpatialRef = osr.SpatialReference()
    inSpatialRef.ImportFromEPSG(inProj) #datum of the points
    
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
    layer = shapeData.CreateLayer(layerName, inSpatialRef, ogr.wkbMultiPolygon)
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
        
#function for disaggregating occurrence points
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


#function for creating fishnets with centroids
#function for creating fishnets with centroids
def createFishNet(outFile, xmin, ymin, xmax, ymax, gridHeight, gridWidth, projection, adjustGrid = True, spherical = False):
    # define projection
    out_srs = osr.SpatialReference()
    out_srs.ImportFromProj4(projection)

    # create coordinate transformation to WGS84
    sphericalSpatialRef = osr.SpatialReference()
    sphericalSpatialRef.ImportFromProj4('+proj=longlat +datum=WGS84 +no_defs +ellps=WGS84 +towgs84=0,0,0')
    coordTransform = osr.CoordinateTransformation(out_srs, sphericalSpatialRef)

    # convert numbers to float
    xmin = float(xmin)
    xmax = float(xmax)
    ymin = float(ymin)
    ymax = float(ymax)
    gridWidth = float(gridWidth)
    gridHeight = float(gridHeight)
    # n of rows
    rows = int((ymax-ymin)/gridHeight)
    # n of columns
    cols = int((xmax-xmin)/gridWidth)
    #readjust width, height
    if adjustGrid == True:
        gridWidth = (xmax-xmin) / cols
        gridHeight = (ymax-ymin) / rows
        

    ####### create output file #######
    if outFile.split('.')[1] == 'json':
        outDriver = ogr.GetDriverByName('GeoJSON')
    if outFile.split('.')[1] == 'shp':
        outDriver = ogr.GetDriverByName('ESRI Shapefile')
    if os.path.exists(outFile):
        os.remove(outFile)
    outDataSource = outDriver.CreateDataSource(outFile)
    if spherical == False:
        outLayer = outDataSource.CreateLayer(outFile, srs = out_srs, geom_type=ogr.wkbPolygon)
    elif spherical == True:
        outLayer = outDataSource.CreateLayer(outFile, srs = sphericalSpatialRef, geom_type=ogr.wkbPolygon)
    
    #create field in the features' properties
    outLayer.CreateField(ogr.FieldDefn('cellID', ogr.OFTInteger))
    outLayer.CreateField(ogr.FieldDefn('Original Centroid', ogr.OFTString))
    if spherical == True:
        outLayer.CreateField(ogr.FieldDefn('Spherical Centroid', ogr.OFTString))
    #create layer definition
    featureDefn = outLayer.GetLayerDefn()
    
    ###### create grid cells #######
    # initiate first cell
    cellLeft = xmin
    cellRight = xmin + gridWidth
    cellTop = ymax
    cellBottom = ymax - gridHeight
    cellID = 0
    for r in range(rows):
        
        for c in range(cols):
            cellID += 1
            # create geometry
            LRing = ogr.Geometry(ogr.wkbLinearRing)
            LRing.AddPoint(cellLeft, cellTop)
            LRing.AddPoint(cellRight, cellTop)
            LRing.AddPoint(cellRight, cellBottom)
            LRing.AddPoint(cellLeft, cellBottom)
            LRing.AddPoint(cellLeft, cellTop)
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(LRing)
            # calculate original centroid
            xOrigin = str(poly.Centroid().GetX())
            yOrigin = str(poly.Centroid().GetY())
            #reproject poly
            if spherical == True:
                poly.Transform(coordTransform)
                # calculate spherical centroid
                x = str(poly.Centroid().GetX())
                y = str(poly.Centroid().GetY())
            
            # add new geom to layer
            outFeature = ogr.Feature(featureDefn)
            outFeature.SetGeometry(poly)
            # add properties
            outFeature.SetField('cellID', cellID)
            outFeature.SetField('Original Centroid', '[' + str(xOrigin) + ',' + str(yOrigin) + ']')
            if spherical == True:
                outFeature.SetField('Spherical Centroid', '[' + str(x) + ',' + str(y) + ']')

            outLayer.CreateFeature(outFeature)
            outFeature.Destroy
            
            cellLeft += gridWidth
            cellRight += gridWidth
            
        # define new row start
        cellLeft = xmin
        cellRight = xmin + gridWidth
        cellTop -= gridHeight
        cellBottom -= gridHeight
                                
    # Close DataSources
    outDataSource.Destroy()

