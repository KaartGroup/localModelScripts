#!/usr/bin/env python3
# Written by Taylor Smock (taylor.smock@kaartgroup.com)

import os
import time
import requests
import argparse
from cachecontrol import CacheControl
import json
import geojson
from tqdm import tqdm
from defusedxml import ElementTree as ElementTree
# This is for ElementTree.ElementTree
import xml.etree.ElementTree as ET

# Do NOT commit the following information
def read_config(config = '.config'):
    with open(config) as fp:
        jsonData = json.load(fp)
    if 'mapillary_client_id' in jsonData:
        global mapillary_client_id
        mapillary_client_id = jsonData['mapillary_client_id']

USER_AGENT = "trackDownload/0.1 (taylor.smock@kaartgroup.com)"

def save_json(directory, name, gjson):
    """Save a json file as either geojson or json depending upon tags"""
    if 'type' in gjson:
        ext = '.geojson'
    else:
        ext = '.json'
    with open(os.path.join(directory, name + ext), 'w') as wfile:
        json.dump(gjson, wfile, indent=4, sort_keys=True)

def save_xml(directory, name, xml_tree):
    """Save an xml file as .osm or .xml, depending upon tags"""
    root = xml_tree.getroot()
    if root.tag == "osm" or root.find("osm") is not None:
        ext = '.osm'
    else:
        ext = '.xml'
    xml_tree.write(os.path.join(directory, name + ext), xml_declaration=True)

def save(directory, name, save_object):
    """Save a file, automatically detecting the type"""
    if not os.path.exists(directory):
        os.makedirs(directory)
    elif not os.path.isdir(directory):
        raise ValueError('{0} is not a directory', directory)
    obj_type = type(save_object)
    if obj_type is geojson.feature.FeatureCollection or obj_type is dict:
        save_json(directory, name, save_object)
    elif obj_type is ET.ElementTree:
        save_xml(directory, name, save_object)
    else:
        raise ValueError("We do not support saving {}".format(obj_type))

def overpass_status(api_status_url = "https://overpass-api.de/api/status"):
    """Get the overpass status -- this returns an int with the time to wait"""
    session = requests.session()
    session.headers.update({'User-Agent': USER_AGENT})
    cached_session = CacheControl(session)
    response = cached_session.get(api_status_url)
    if (response.status_code != requests.codes.ok):
        raise ValueError("Bad Request: {}".format(api_status_url))
    parsed_response = {'wait_time': []}
    for i in response.text.splitlines():
        if "Connected as" in i:
            parsed_response['connected_as'] = i.split(":")[1].strip()
        elif "Current time" in i:
            parsed_response['current_time'] = i.split(":")[1].strip()
        elif "Rate limit" in i:
            parsed_response['rate_limit'] = int(i.split(":")[1].strip())
        elif "slots available now" in i:
            parsed_response['slots_available'] = int(i.split(" ")[0].strip())
        elif "Slot available after" in i:
            parsed_response['wait_time'].append(int(i.split(" ")[5]))
    if 'slots_available' not in parsed_response:
        parsed_response['slots_available'] = 0
    wait_time = 0
    if parsed_response['rate_limit'] - parsed_response['slots_available'] >= 2 and len(parsed_response['wait_time']) > 0:
        return max(parsed_response['wait_time'])
    return wait_time

def nominatim_query(area):
    polygon=1
    session = requests.session()
    session.headers.update({'User-Agent': USER_AGENT})
    cached_session = CacheControl(session)
    url = "https://nominatim.openstreetmap.org/search/{AREA}?format=geojson&polygon_geojson={polygon}".format(AREA=area, polygon=polygon)
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

def overpass_query(query):
    """Query the overpass servers. This may block for extended periods of time, depending upon the query"""
    session = requests.session()
    session.headers.update({'User-Agent': USER_AGENT})
    cached_session = CacheControl(session)
    response = cached_session.post("http://overpass-api.de/api/interpreter", data={'data': query})
    wait_time = overpass_status()
    loop = 0
    while (wait_time > 0):
        time.sleep(wait_time)
        wait_time = overpass_status()
        loop += 1
    while (response.status_code == requests.codes.too_many_requests):
        time.sleep(10)
        response = cached_session.post("http://overpass-api.de/api/interpreter", data={'data': query})
    if (response.status_code != requests.codes.ok):
        print("Bad request")
        print(response.text)
        print(response.status_code)
        raise ValueError("Bad Request: {}".format(query))

    xml = response.text

    if (response.status_code != requests.codes.ok):
        raise ValueError("We got a bad response code of {} for {} which resulted in:\r\n{}".format(response.status_code, query, xml))
    content_type = response.headers.get('content-type')
    if content_type == 'application/osm3s+xml':
        return ET.ElementTree(ElementTree.fromstring(xml))
    elif content_type == 'application/json':
        return response.json()
    else:
        raise ValueError("Unexpected content type ({}) from the query: {}".format(content_type, query))

def road_tasks(area, feature):
    area_id = feature['properties']['osm_id']
    if feature['properties']['osm_type'] == 'relation':
        area_id += 3600000000
    elif feature['properties']['osm_type'] == 'way':
        area_id += 2400000000
    road_blacklist = ["track", "path", "living_street", "residential", "service", "footway", "cycleway", "steps", "proposed", "motorway_link", "pedestrian"]
    roads = overpass_query("""[out:xml];area({area_id}) -> .searchArea; ( way["highway"]["highway"!~"{road_blacklist}"](area.searchArea); ); (._;>;); out meta;""".format(osm_type=feature['properties']['osm_type'], area_id=area_id, road_blacklist = "|".join(road_blacklist)))
    save(area, 'roads', roads)

    high_priority_roads = overpass_query("""[out:xml];area({area_id}) -> .searchArea; ( way["highway"~"motorway|trunk|primary"](area.searchArea); ); (._;>;); out meta;""".format(osm_type=feature['properties']['osm_type'], area_id=area_id))
    save(area, 'high_priority_roads', high_priority_roads)

def missing_geometry_false_positives(area, feature):
    area_id = feature['properties']['osm_id']
    if feature['properties']['osm_type'] == 'relation':
        area_id += 3600000000
    elif feature['properties']['osm_type'] == 'way':
        area_id += 2400000000
    false_positive = overpass_query("""[out:xml][maxsize:1973741824][timeout:360];
area({area_id}) -> .searchArea;
(
  way["aeroway"](area.searchArea);
  relation["aeroway"](area.searchArea);
  way["waterway"](area.searchArea);
  relation["waterway"](area.searchArea);
  way["place=sea"](area.searchArea);
  relation["place=sea"](area.searchArea);
  way["place=ocean"](area.searchArea);
  relation["place=ocean"](area.searchArea);
  way["natural=bay"](area.searchArea);
  relation["natural=bay"](area.searchArea);
  way["natural=strait"](area.searchArea);
  relation["natural=strait"](area.searchArea);
  way["military"](area.searchArea);
  relation["military"](area.searchArea);
  way["landuse=military"](area.searchArea);
  relation["landuse=military"](area.searchArea);
);
(._;>;);
out meta;""".format(area_id=area_id))
    save(area, 'false_positive_geometry_areas', false_positive)

def get_water_way(area, feature):
    water = overpass_query("""[out:xml];
(
  node["place"="sea"](29.171348850951507,12.76611328125,45.01141864227728,35.947265625);
  way["place"="sea"](29.171348850951507,12.76611328125,45.01141864227728,35.947265625);
  relation["place"="sea"](29.171348850951507,12.76611328125,45.01141864227728,35.947265625);
);
(._;>;);
out meta;""")
    save(area, 'water', water)

def main(area):
    read_config()
    areas = nominatim_query(area)
    nodes = {}
    feature = areas['features'][0]
    for tfeature in areas['features']:
        if 'type' in tfeature and tfeature['type'] == 'Point':
            nodes[str(tfeature['id'])] = tfeature
        properties = tfeature['properties']
        if 'place_rank' in properties and ('place_rank' not in feature['properties'] or properties['place_rank'] < feature['properties']['place_rank']):
            feature = tfeature
    if 'bbox' in feature:
        bboxInformation = feature['bbox']
        save(area, 'boundary', feature)
    missing_geometry_false_positives(area, feature)
    #get_water_way(area, feature)
    #road_tasks(area, feature)

main("Ukraine")
