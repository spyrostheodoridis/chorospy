from osgeo import gdal, osr, ogr
import numpy
import subprocess
import re

def rasterToJSON (infile, outfile):
    #get projection of input file
    inProj = subprocess.Popen(['gdalsrsinfo', infile, '-o', 'proj4'], stdout=subprocess.PIPE, encoding='utf8').stdout.read().strip().replace('\'','')
    #get info of input file
    inFo = subprocess.Popen(['gdalinfo', infile], stdout=subprocess.PIPE, encoding='utf8').stdout.read().split('\n')
    coordDic = {}

    for i in ['Upper Left', 'Lower Left', 'Upper Right', 'Lower Right', 'Center']:
        pp = [x for x in inFo if i in x]
        PP = re.split(r'\(|\)', pp[0])[1].strip().replace(' ', '').split(',')
        #transform to wgs84
        p = subprocess.Popen(['gdaltransform', '-s_srs', inProj, '-t_srs', 'EPSG:4326'], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf8')
        pointCoord = p.communicate('{} {}'.format(PP[0], PP[1]))[0].rstrip().split()
        
        try:
            x, y = float(pointCoord[0]), float(pointCoord[1])
            coordDic[i] = [x,y]
        except:
            coordDic[i] = []

        

    inRas = gdal.Open(infile)
    
    nrows = inRas.RasterYSize
    ncols = inRas.RasterXSize
    
    band1 = inRas.GetRasterBand(1)
    nodata = band1.GetNoDataValue()
    gdata = band1.ReadAsArray()
    
    dataType = gdal.GetDataTypeName(band1.DataType)
    #convert to float
    if dataType.startswith('Int'):
        gdata = gdata.astype(numpy.float32, copy=False)
    # new nodata value
    gdata[gdata == nodata] = -9999
    gdata[numpy.isnan(gdata)]= -9999

    #gdata = numpy.concatenate(gdata)
    #gdata = gdata.tolist()
    #write to json
    
    with open(outfile, 'w') as fp:
        fp.write('{\n')
        fp.write('"upLeft": {}'.format(coordDic['Upper Left']) + ',\n')
        fp.write('"loLeft": {}'.format(coordDic['Lower Left']) + ',\n')
        fp.write('"upRight": {}'.format(coordDic['Upper Right']) + ',\n')
        fp.write('"loRight": {}'.format(coordDic['Lower Right']) + ',\n')
        fp.write('"center": {}'.format(coordDic['Center']) + ',\n')
        fp.write('"projEPSG": "{}"'.format(inProj) + ',\n')
        fp.write('"width": {}'.format(ncols) + ',\n')
        fp.write('"height": {}'.format(nrows) + ',\n')
        fp.write('"data":'+ '\n')
        for i, row in enumerate(gdata):
            if i == 0:
                fp.write('[{}'.format(row.tolist()))
            else:
                fp.write(',\n{}'.format(row.tolist()))
        
        fp.write(']\n}\n')           
        #json.dump(gdataJSON, fp, indent=4)
    fp.close()