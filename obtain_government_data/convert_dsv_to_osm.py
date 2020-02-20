#!/usr/bin/env python3
import os
import sys
import csv
import argparse
from tqdm import tqdm
sys.path.insert(1, 'serve_osm_files') # clone git@gitlab.com:smocktaylor/serve_osm_files.git
import osm_backend as osm
class ConversionInformation:
    """ Class for conversion information """

    def __init__(self, latitude_header, longitude_header, mappings):
        self.latitude_header = latitude_header
        self.longitude_header = longitude_header
        self.mappings = mappings

def convert_dsv(filename, conversion_information):
    """ Convert a dsv to an OSM DataSet """
    elements = []
    minlat = 90
    maxlat = -90
    maxlon = -180
    minlon = 180
    with open(filename) as csvfile:
        reader = csv.DictReader(csvfile, delimiter="|")
        falseid = -1

        for row in tqdm(reader):
            tags = {}
            lat = None
            lon = None
            for column in row:
                if not row[column]:
                    continue
                if column in conversion_information.mappings:
                    tags[conversion_information.mappings[column]] = row[column]
                elif column == conversion_information.latitude_header:
                    lat = float(row[column].replace(",", "."))
                elif column == conversion_information.longitude_header:
                    lon = float(row[column].replace(",", "."))
                else:
                    tags[column] = row[column]
            elements.append(osm.Node(falseid, osm.LatLon(lat, lon), tags))
            falseid -= 1
            if lat and lat > maxlat:
                maxlat = lat
            if lat and lat < minlat:
                minlat = lat
            if lon and lon > maxlon:
                maxlon = lon
            if lon and lon < minlon:
                minlon = lon
    return osm.DataSet(osm.BBox([minlon, minlat, maxlon, maxlat]), elements)

def write_dataset(filename, dataset):
    with open(filename, 'w') as output:
        output.write(dataset.convert_to_xml().decode("utf-8"))

def mappings_to_dict(mappings):
    returnDict = {}
    if mappings:
        for item in mappings:
            split = item.split("=")
            if split[0] not in returnDict:
                returnDict[split[0]] = "=".join(split[1:])
            else:
                if isinstance(returnDict[split[0]], list):
                    tDict = returnDict[split[0]]
                else:
                    tDict = [returnDict[split[0]]]
                tDict.append("=".join(split[1:]))
                returnDict[split[0]] = tDict
    return returnDict

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", help="The file to convert to osm xml")
    parser.add_argument("--latitude", help="The latitude column")
    parser.add_argument("--longitude", help="The longitude column")
    parser.add_argument("--mappings", help="Column to key mappings", action="append")
    args = parser.parse_args()
    conversion_information = ConversionInformation(args.latitude, args.longitude, mappings_to_dict(args.mappings))
    dataset = convert_dsv(args.filename, conversion_information)
    write_dataset(os.path.splitext(args.filename)[0] + ".osm", dataset)
