from osgeo import osr,ogr,gdal
import pandas
import numpy
import os
import math

def getValuesAtPoint(indir, rasterfileList, pos, lon, lat, sp):
    #gt(2) and gt(4) coefficients are zero, and the gt(1) is pixel width, and gt(5) is pixel height.
    #The (gt(0),gt(3)) position is the top left corner of the top left pixel of the raster.
    for i, rs in enumerate(rasterfileList):
        print('processing {}'.format(rs))
        presValues = []
        gdata = gdal.Open('{}/{}.tif'.format(indir,rs))
        gt = gdata.GetGeoTransform()
        band = gdata.GetRasterBand(1)
        nodata = band.GetNoDataValue()

        x0, y0 , w , h = gt[0], gt[3], abs(gt[1]), abs(gt[5])
        
        xmin, xmax, ymin, ymax = min(pos[lon]), max(pos[lon]), min(pos[lat]), max(pos[lat])

        # Specify offset and rows and columns to read
        xoff = int((xmin - x0)/w)
        yoff = int((y0 - ymax)/h)
        xcount = int(math.ceil((xmax - xmin)/w)+1)
        ycount = int(math.ceil((ymax - ymin)/h)+1)

        data = band.ReadAsArray(xoff, yoff, xcount, ycount).astype(numpy.float)
        #free memory
        del gdata
        
        if i == 0:
            #iterate through the points
            for p in pos.iterrows():
                x = int((p[1][lon] - x0)/w) - xoff
                Xc = x0 + int((p[1][lon] - x0)/w)*w + w/2 #the cell center x
                y = int((y0 - p[1][lat])/h) - yoff
                Yc = y0 - int((y0 - p[1][lat])/h)*h - h/2 #the cell center y
                try:
                    if data[y,x] != nodata:
                        value = data[y,x]
                    else:
                        value = numpy.nan
                    presVAL = [p[1][sp],p[1][lon],p[1][lat], '{:.6f}'.format(Xc), '{:.6f}'.format(Yc), value]
                    presValues.append(presVAL)
                except:
                    pass
            df = pandas.DataFrame(presValues, columns=['sp', 'x', 'y', 'Xc', 'Yc', rs])
        else:
            #iterate through the points
            for p in pos.iterrows():
                x = int((p[1][lon] - x0)/w) - xoff
                y = int((y0 - p[1][lat])/h) - yoff
                try:
                    if data[y,x] != nodata:
                        presValues.append(data[y,x])
                    else:
                        presValues.append(numpy.nan)
                except:
                    pass
            df[rs] = pandas.Series(presValues)
    del data, band
    print('extracted values written in dataframe')
    return df


#### function to get all pixel center coordinates and corresponding values from rasters
def getRasterValues(indir, rasterfileList, skipNoData = True):
    
    for i, rs in enumerate(rasterfileList):

        print('processing {}'.format(rs))
        
        if i == 0:
            vList = []
            gdata = gdal.Open('{}/{}.tif'.format(indir,rs))
            gt = gdata.GetGeoTransform()
            band = gdata.GetRasterBand(1)
            nodata = band.GetNoDataValue()
            if not nodata: #if there's no data defined, assign a very small number
                nodata = -3.402823e+38 
            data = band.ReadAsArray().astype(numpy.float)
            #free memory
            del gdata

            x0, y0 , w , h = gt[0], gt[3], gt[1], gt[5]

            for r, row in enumerate(data):
                x = 0
                for c, column in enumerate(row):
                    if skipNoData == True:
                        if '{:0.3e}'.format(column) == '{:0.3e}'.format(nodata): #if value is no data (I reduced it to three digits to avoid conflicts)
                            pass
                        else:
                            x = x0 + c*w + w/2
                            y = y0 + r*h + h/2
                            vList.append(['{:.6f}'.format(x),'{:.6f}'.format(y),column])
                    elif skipNoData == False:
                        if '{:0.3e}'.format(column) == '{:0.3e}'.format(nodata):
                            column = numpy.nan
                        x = x0 + c*w + w/2
                        y = y0 + r*h + h/2
                        vList.append(['{:.6f}'.format(x),'{:.6f}'.format(y),column])
                        
            df = pandas.DataFrame(vList, columns=['Xc', 'Yc', rs])
            
        else:
            gdata = gdal.Open('{}/{}.tif'.format(indir,rs))
            gt = gdata.GetGeoTransform()
            band = gdata.GetRasterBand(1)
            nodata = band.GetNoDataValue()
            if not nodata: #if there's no data defined, assign a very small number
                nodata = -3.402823e+38
            data = band.ReadAsArray().astype(numpy.float)
            #free memory
            del gdata
            if skipNoData == True: 
                vList = [c for r in data for c in r if '{:0.3e}'.format(c) == '{:0.3e}'.format(nodata)]
            elif skipNoData == False:
                vList = [c if '{:0.3e}'.format(c) != '{:0.3e}'.format(nodata) else numpy.nan for r in data for c in r]
                
            df[rs] = pandas.Series(vList)
    
    del data, band
    
    print('extracted values written in dataframe')   
    return(df)


# geo raster to numpy array    
def raster2array(rasterfn):
    raster = gdal.Open(rasterfn)
    band = raster.GetRasterBand(1)
    nodata = band.GetNoDataValue()
    array = band.ReadAsArray()
    
    proj = raster.GetProjection()
    inproj = osr.SpatialReference()
    inproj.ImportFromWkt(proj)
    
    geoTransform = raster.GetGeoTransform()
    minx = geoTransform[0]
    maxy = geoTransform[3]
    maxx = minx + geoTransform[1]*raster.RasterXSize
    miny = maxy + geoTransform[5]*raster.RasterYSize
    extent =  [minx, maxx, miny, maxy]
    pixelSizeXY = [geoTransform[1], geoTransform[5]]
    del raster, band
    return [array, nodata, extent, inproj, pixelSizeXY]

#clip a raster by vector
def clipRaster(raster, newRaster, vector):
    raster = gdal.Open(raster)
    
    vect = ogr.Open(vector)
    lyr = vect.GetLayer()
    ext = lyr.GetExtent()
    
    gTrans = raster.GetGeoTransform()
    #get the x start of the left most pixel
    xlP = int((ext[0] - gTrans[0])/gTrans[1])*gTrans[1] - abs(gTrans[0])
    #get the x end of the right most pixel
    xrP = math.ceil((ext[1] - gTrans[0])/gTrans[1])*gTrans[1] - abs(gTrans[0])
    #get the y start of the upper most pixel
    yuP = abs(gTrans[3]) - int((gTrans[3] - ext[3])/gTrans[5])*gTrans[5]
    #get the y end of the lower most pixel
    ylP = abs(gTrans[3]) - math.floor((gTrans[3] - ext[2])/gTrans[5])*gTrans[5]
        
    gdal.Translate('tmp.tif', raster, projWin = [xlP, yuP, xrP, ylP])
    del raster
    tRas = gdal.Open('tmp.tif')
    band = tRas.GetRasterBand(1)
    noDat = band.GetNoDataValue()
    # store a copy before rasterize
    fullRas = band.ReadAsArray().astype(numpy.float)
    
    gdal.RasterizeLayer(tRas, [1], lyr, None, None, [-9999], ['ALL_TOUCHED=TRUE']) # now tRas is modified
    
    finRas = tRas.GetRasterBand(1).ReadAsArray().astype(numpy.float)

    for i, row in enumerate(finRas):
        for j, col in enumerate(row):
            if col == -9999.:
                finRas[i, j] = fullRas[i, j]
            else:
                finRas[i, j] = noDat

    array2raster(newRaster, 'tmp.tif', finRas, noDat, "float32")
    os.remove('tmp.tif')
    del fullRas, finRas, band, tRas

# create a reference raster with random values    
# create a reference raster with random values    
def createRaster(outRas, xmin, ymin, xmax, ymax, pixelSize, coordinates = 'spherical', 
                 proj = '+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs', 
                 cellValues = 'random', dataType = "float32", noData = -9999, 
                 inVector = None, rasterizeOptions = ['ALL_TOUCHED=FALSE']):
    
    NP2GDAL_CONVERSION = { "uint8": 1, "uint16": 2, "int16": 3, 
                          "uint32": 4, "int32": 5, "float32": 6, "float64": 7,
                          "complex64": 10, "complex128": 11,
                         }
    if os.path.exists(outRas):
        print('Raster file already excists!')
        return
    
    if coordinates == 'spherical':
        # create coordinate transformation
        inRef = osr.SpatialReference()
        inRef.ImportFromProj4('+proj=longlat +datum=WGS84 +no_defs +ellps=WGS84 +towgs84=0,0,0')
        outRef = osr.SpatialReference()
        outRef.ImportFromProj4(proj)

        coordTransform = osr.CoordinateTransformation(inRef, outRef)

        LLpoint = ogr.Geometry(ogr.wkbPoint)
        LLpoint.AddPoint(float(xmin), float(ymin))
        LLpoint.Transform(coordTransform)
        URpoint = ogr.Geometry(ogr.wkbPoint)
        URpoint.AddPoint(float(xmax), float(ymax))
        URpoint.Transform(coordTransform)
        xmin, ymin, xmax, ymax = LLpoint.GetX(), LLpoint.GetY(), URpoint.GetX(), URpoint.GetY(),
        
    # Create the destination data source        
    xRes = int(numpy.int((xmax - xmin) / pixelSize))
    yRes = int(numpy.int((ymax - ymin) / pixelSize))
    
    targetRas = gdal.GetDriverByName('GTiff').Create(outRas, xRes, yRes, 1, NP2GDAL_CONVERSION[dataType])
    targetRas.SetGeoTransform((xmin, pixelSize, 0, ymax, 0, -pixelSize))
    band = targetRas.GetRasterBand(1)
    band.SetNoDataValue(noData)

    if inVector != None:
        srcVector = ogr.Open(inVector)
        srcLayer = srcVector.GetLayer()
        
        # Rasterize clips the raster band
        gdal.RasterizeLayer(targetRas, [1], srcLayer, None, None, [0], rasterizeOptions)

        g = band.ReadAsArray()

    else:
        g = numpy.zeros((yRes,xRes), eval('numpy.{}'.format(dataType)))

    #populate matrix with numbers
    for i in range(yRes):
        for j in range(xRes):
            if g[i,j] != noData:
                if cellValues == 'lat':
                    g[i,j] = i
                elif cellValues == 'lon':
                    g[i,j] = j
                elif cellValues == 'random':
                    g[i,j] = numpy.random.randint(1000)
                elif cellValues == 'index':
                    g[i,j] = i*xRes + j

    band.WriteArray(g)
    targetRasSRS = osr.SpatialReference()
    targetRasSRS.ImportFromProj4(proj)
    targetRas.SetProjection(targetRasSRS.ExportToWkt())
    band.FlushCache()
    print('raster file created!')

#function to filter raster cells based on the coverage by some vector features
def filterByCoverage(vectorFile, rasterFile, covPerc):
    
    srcVector = ogr.Open(vectorFile)
    srcLayer = srcVector.GetLayer()
    # merge all features in one geometry (multi polygone)
    multi  = ogr.Geometry(ogr.wkbMultiPolygon)
    for feature in srcLayer:
        geom = feature.GetGeometryRef()
        multi.AddGeometry(geom)
    
    #attributes of raster file
    rasList = raster2array(rasterFile)

    xsize = rasList[4][0]
    ysize = abs(rasList[4][1])

    pixel_area = xsize*ysize

    rows = rasList[0].shape[0]
    cols = rasList[0].shape[1]

    x1 = rasList[2][0]
    y1 = rasList[2][3]
    
    #iterate over raster cells
    for i in range(rows):
        for j in range(cols):
            ring = ogr.Geometry(ogr.wkbLinearRing)

            ring.AddPoint(x1, y1)
            ring.AddPoint(x1 + xsize, y1)
            ring.AddPoint(x1 + xsize, y1 - ysize)
            ring.AddPoint(x1, y1 - ysize)
            ring.AddPoint(x1, y1)

            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(ring)

            intersect = multi.Intersection(poly)

            if intersect.ExportToWkt() != 'GEOMETRYCOLLECTION EMPTY':
                perc = (intersect.GetArea()/pixel_area)*100
                if perc > covPerc:
                    rasList[0][i][j] = numpy.nan     
            x1 += xsize
        x1 = rasList[2][0]
        y1 -= ysize
    
    return(rasList[0]) #return the filtered array


# numpy array to geo raster
def array2raster(newRaster, RefRaster, array, noData, dataType):
    #data type conversion
    NP2GDAL_CONVERSION = { "uint8": 1, "int8": 1, "uint16": 2, "int16": 3, 
                          "uint32": 4, "int32": 5, "float32": 6, "float64": 7,
                          "complex64": 10, "complex128": 11,
                         }
    #get info from reference raster
    rfRaster = gdal.Open(RefRaster)
    geotransform = rfRaster.GetGeoTransform()
    originX = geotransform[0]
    originY = geotransform[3]
    pixelWidth = geotransform[1]
    pixelHeight = geotransform[5]
    cols = array.shape[1]
    rows = array.shape[0]
    #create new raster
    outRaster = gdal.GetDriverByName('GTiff').Create(newRaster, cols, rows,1, NP2GDAL_CONVERSION[dataType])
    outRaster.SetGeoTransform((originX, pixelWidth, 0, originY, 0, pixelHeight))
    #write array to band
    outband = outRaster.GetRasterBand(1)
    outband.SetNoDataValue(noData)
    outband.WriteArray(array)
    #define new raster projection
    outRasterSRS = osr.SpatialReference()
    outRasterSRS.ImportFromWkt(rfRaster.GetProjectionRef())
    outRaster.SetProjection(outRasterSRS.ExportToWkt())
    #write raster
    outband.FlushCache()
    del rfRaster
    

    
 