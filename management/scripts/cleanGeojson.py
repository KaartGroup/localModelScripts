#!/usr/bin/env python3
import geojson
import json
import glob

def loadGeojson(geojsonfile):
    with open(geojsonfile) as f:
        return json.load(f)

def saveGeojson(geojsonfile, geojson):
    with open(geojsonfile, 'w') as f:
        json.dump(geojson, f, indent=4, sort_keys=True)

def cleanGeojson(geojson):
    #print(geojson)
    #exit(-1)
    return(geojson)

if __name__ == "__main__":
    files = glob.glob('../**/*.geojson', recursive=True)
    for gfile in files:
        print(gfile)
        gjson = loadGeojson(gfile)
        gjson = cleanGeojson(gjson)
        saveGeojson(gfile, gjson)
