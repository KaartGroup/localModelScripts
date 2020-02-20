#!/usr/bin/env python3
import os
import requests
from cachecontrol import CacheControl
import json
import geojson
from tqdm import tqdm
import time
from defusedxml import ElementTree as ElementTree
# This is for ElementTree.ElementTree
import xml.etree.ElementTree as ET

# Do NOT commit the following information
mapillary_client_id = None

USER_AGENT = "trackDownload/0.1 (taylor.smock@kaartgroup.com)"

def save_json(area, name, gjson):
    if 'type' in gjson:
        ext = '.geojson'
    else:
        ext = '.json'
    with open(os.path.join(area, name + ext), 'w') as wfile:
        #wfile.write(gjson)
        json.dump(gjson, wfile, indent=4, sort_keys=True)

def save_xml(area, name, xml_tree):
    root = xml_tree.getroot()
    if root.tag == "osm" or root.find("osm") is not None:
        ext = '.osm'
    else:
        ext = '.xml'
    xml_tree.write(os.path.join(area, name + ext), xml_declaration=True)

def save(area, name, save_object):
    if not os.path.exists(area):
        os.makedirs(area)
    elif not os.path.isdir(area):
        raise ValueError('{0} is not a directory', area)
    obj_type = type(save_object)
    if obj_type is geojson.feature.FeatureCollection or obj_type is dict:
        save_json(area, name, save_object)
    elif obj_type is ET.ElementTree:
        save_xml(area, name, save_object)
    else:
        raise ValueError("We do not support saving {}".format(obj_type))

def nominatim_query(area):
    polygon=1
    session = requests.session()
    session.headers.update({'User-Agent': USER_AGENT})
    cached_session = CacheControl(session)
    url = "https://nominatim.openstreetmap.org/search/{AREA}?format=geojson&polygon_geojson={polygon}".format(AREA=area, polygon=polygon)
    print(url)
    response = cached_session.get(requests.utils.requote_uri(url))
    try:
        areaJson = response.json()
    except json.decoder.JSONDecodeError as e:
        raise ValueError("Query for {} resulted in an error ({}) and the response was:\r\n{}".format(area, e, response.text))
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
    return {"name": "mapillary", "api" : "https://a.mapillary.com/v3", "tracks": "/sequences", 'params': {'bbox': '{minx},{miny},{maxx},{maxy}', 'start_time':'2019-04-14T00:00:00Z', 'end_time': '2019-04-23T00:00:00Z', "client_id": str(mapillary_client_id)}}

def getApis():
    return [openstreetcam(), mapillary()]

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
    session.headers.update({'User-Agent': USER_AGENT})
    cached_session = CacheControl(session)
    for api in apis:
        if 'data' in api:
            data = api['data']
            if 'bbTopLeft' in data:
                data['bbTopLeft'] = '{lat},{lon}'.format(lat=bboxInformation[3], lon=bboxInformation[0])
            if 'bbBottomRight' in data:
                data['bbBottomRight'] = '{lat},{lon}'.format(lat=bboxInformation[1], lon=bboxInformation[2])
            response = cached_session.post(api['api'] + api['tracks'], data=data)
            tJson = response.json()
        else:
            turl = api['api'] + api['tracks']
            params = api['params']
            params['bbox'] = params['bbox'].format(minx=bboxInformation[0], miny=bboxInformation[1], maxx=bboxInformation[2], maxy=bboxInformation[3])
            response = cached_session.get(turl, params=params)
            tJson = response.json()
            while 'next' in response.links:
                response = cached_session.get(response.links['next']['url'])
                tJson['features'] = tJson['features'] + response.json()['features']
        if (response.status_code != requests.codes.ok):
            raise ValueError("{} gave us a status code of {}".format(response.url, response.status_code))
        if api['name'] == 'openstreetcam':
            tJson = convertJson(tJson)
        save(area, api['name'], tJson)

def overpass_query(query):
    session = requests.session()
    session.headers.update({'User-Agent': USER_AGENT})
    cached_session = CacheControl(session)
    response = cached_session.get("http://overpass-api.de/api/interpreter", params={'data': query})
    while (response.status_code == requests.codes.too_many_requests):
        time.sleep(10)
        response = cached_session.get("http://overpass-api.de/api/interpreter", params={'data': query})

    xml = response.text

    if (response.status_code != requests.codes.ok):
        raise ValueError("We got a bad response code of {} for {} which resulted in:\r\n{}".format(response.status_code, query, xml))
    content_type = response.headers.get('content-type')
    if content_type == 'application/osm3s+xml':
        return ET.ElementTree(ElementTree.fromstring(xml))
    else:
        raise ValueError("Unexpected content type ({}) from the query: {}".format(content_type, query))


def main(area):
    areas = nominatim_query(area)
    nodes = {}
    for feature in areas['features']:
        if 'type' in feature and feature['type'] == 'Point':
            nodes[str(feature['id'])] = feature
    feature = areas['features'][0]
    if 'bbox' in feature:
        bboxInformation = feature['bbox']
        getTracks(area, bboxInformation)
        save(area, 'boundary', feature)

    area_id = feature['properties']['osm_id']
    if feature['properties']['osm_type'] == 'relation':
        area_id += 3600000000
    elif feature['properties']['osm_type'] == 'way':
        area_id += 2400000000


if __name__ == "__main__":
    import sys
    for item in sys.argv[1:]:
        main(item)
