#!/usr/bin/env python3

import urllib.parse
import urllib.request
import json


def getPolygon(area):
    if "," in area:
        splitArea = area.split(",")
        area = splitArea[0]
    query = "[out:json][timeout:25];(relation[\"type\"=\"boundary\"][\"name\"=\"{area}\"];); out body; >; out skel qt;".format(area=area)
    overpassUrl = "https://overpass-api.de/api/interpreter?data=" + urllib.parse.quote(query)
    return json.loads(urllib.request.urlopen(overpassUrl).read())

def buildBBox(json):
    if "elements" in json:
        json = json["elements"]
    bbox = []
    print(json)
    for member in json:
        if member["type"] != "node":
            continue
        lat = member['lat']
        lon = member['lon']
        if len(bbox) < 1:
            bbox.append([lat, lon])
        elif len(bbox) < 2:
            bbox.append([lat, lon])
            if bbox[0][0] > lat:
                tLat = bbox[0][0]
                bbox[0][0] = lat
                bbox[1][0] = tLat
            if bbox[0][1] > lon:
                tLon = bbox[0][1]
                bbox[0][1] = lon
                bbox[1][1] = tLon
        else:
            if lat < bbox[0][0]:
                bbox[0][0] = lat
            elif lat > bbox[1][0]:
                bbox[1][0] = lat
            if lon < bbox[0][1]:
                bbox[0][1] = lon
            elif lon > bbox[1][1]:
                bbox[1][1] = lon
    return bbox


def getIssues(bbox, issue):
    osmoseUrl = "http://osmose.openstreetmap.fr/en/map/markers?item={issue}&bbox={bbox}"
    url = osmoseUrl.format(bbox=bbox, issue=issue)
    #http://osmose.openstreetmap.fr/en/map/markers?zoom=8&item=8360&level=1%2C2%2C3&tags=&fixable=&limit=500&bbox=-108.5651457309723%2C39.068046812481974%2C-108.55645537376405%2C39.07185344987507

if __name__ == "__main__":
    area = "Grand Junction, Colorado"
    issue = 8360
    polygon = getPolygon(area)
    bbox = buildBBox(polygon)
    print(bbox)
    exit(-1)
    getIssues(bbox, issue)
