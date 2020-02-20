#!/usr/bin/env python3

import json
import glob
import osm2geojson
import os

def convert(osmFile):
    with open(osmFile) as data:
        xml = data.read()

    geojson = osm2geojson.xml2geojson(xml)

    writeFile = os.path.splitext(osmFile)[0] + '.geojson'
    with open(writeFile, 'w') as write:
        json.dump(geojson, write, indent=4, sort_keys=True)

if __name__ == "__main__":
    files = glob.glob('../**/*.osm', recursive=True)
    for osmFile in files:
        print("Converting {} to geojson".format(osmFile))
        convert(osmFile)
