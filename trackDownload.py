#!/usr/bin/env python3
import os
import requests
from cachecontrol import CacheControl
import json
import geojson
from tqdm import tqdm

# Do NOT commit the following information
#mapillary_client_id =

def save_json(area, name, gjson):
    if not os.path.exists(area):
        os.makedirs(area)
    elif not os.path.isdir(area):
        raise ValueError('{0} is not a directory', area)
    if 'type' in gjson:
        ext = '.geojson'
    else:
        ext = '.json'
    with open(os.path.join(area, name + ext), 'w') as wfile:
        #wfile.write(gjson)
        json.dump(gjson, wfile, indent=4, sort_keys=True)

def overpass_query(area):
    session = requests.session()
    cached_session = CacheControl(session)
    url = "https://nominatim.openstreetmap.org/search/{AREA}?format=geojson".format(AREA=area)
    response = cached_session.get(requests.utils.requote_uri(url))
    areaJson = response.json()
    return areaJson

def build_bbox(coordinates):
    minLat = 90
    maxLat = -90
    minLon = 180
    maxLon = -180
    for coords in coordinates:
        lat = coords[1]
        lon = coords[0]
        if lat > maxLat:
            maxLat = lat
        elif lat < minLat:
            minLat = lat
        if lon > maxLon:
            maxLon = lon
        elif lon < minLon:
            minLon = lon
    return [minLat, minLon, maxLat, maxLon]

def openstreetcam():
    return {"name": "openstreetcam", "api": "http://openstreetcam.org", "tracks": "/1.0/tracks/", "data": {"bbTopLeft": 0, "bbBottomRight": 0}}
def mapillary():
    if mapillary_client_id is None:
        print("We need a mapillary client id (https://www.mapillary.com/app/settings/developers)")
        exit(-1)
    return {"name": "mapillary", "api" : "https://a.mapillary.com/v3", "tracks": "/sequences?bbox={minx},{miny},{maxx},{maxy}&start_time={twoyears}&client_id={mapillary_client_id}".format(mapillary_client_id=mapillary_client_id)}

def getApis():
    return [openstreetcam()]

def convertJson(cJson):
    features = []
    if 'currentPageItems' in cJson:
        for item in cJson['currentPageItems']:
            properties = {}
            if 'element_id' in item:
                properties['id'] = item['element_id']
            pointList = []
            if 'track' in item:
                for coordinates in item['track']:
                    pointList.append((float(coordinates[1]), float(coordinates[0])))
            lineString = geojson.LineString(pointList)
            features.append(geojson.Feature(geometry=lineString, properties=properties))
    return geojson.FeatureCollection(features)

def getTracks(area, bboxInformation):
    apis = getApis()
    session = requests.session()
    cached_session = CacheControl(session)
    for api in apis:
        if 'data' in api:
            data = api['data']
            if 'bbTopLeft' in data:
                data['bbTopLeft'] = '{lat},{lon}'.format(lat=bboxInformation[3], lon=bboxInformation[0])
            if 'bbBottomRight' in data:
                data['bbBottomRight'] = '{lat},{lon}'.format(lat=bboxInformation[1], lon=bboxInformation[2])
            response = cached_session.post(api['api'] + api['tracks'], data=data)
        else:
            response = cached_session.post(api['api'] + api['tracks'].format(minx=bbox[0], miny=bbox[1], maxx=bbox[2], maxy=bbox[3], twoyears="2017-01-01T00:00:00Z"))
        tJson = response.json()
        tJson = convertJson(tJson)
        save_json(area, api['name'], tJson)

def main(area):
    areas = overpass_query(area)
    nodes = {}
    for feature in areas['features']:
        if 'type' in feature and feature['type'] == 'Point':
            nodes[str(feature['id'])] = feature
    tid = 0
    for feature in tqdm(areas['features'], position=0):
        if 'bbox' in feature:
            bboxInformation = feature['bbox']
            getTracks(area + str(tid), bboxInformation)
            save_json(area + str(tid), 'boundary', feature)
            tid += 1

#main("Grand Junction")
main("Brașov")
