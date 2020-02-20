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

def read_config(config = '.config'):
    with open(config) as fp:
        jsonData = json.load(fp)
    if 'mapillary_client_id' in jsonData:
        global mapillary_client_id
        mapillary_client_id = jsonData['mapillary_client_id']

USER_AGENT = "initialUserCheck/0.1 (taylor.smock@kaartgroup.com)"

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


def group_elements(elements):
    """Group elements together to avoid having large overpass queries (the query being thousands of characters long)"""
    maxsize = 40
    returnDict = []
    temporaryDict = []
    returnDict.append(temporaryDict)
    for element in elements:
        temporaryDict.append(element)
        if (len(temporaryDict) >= 40):
            temporaryDict = []
            returnDict.append(temporaryDict)
    return returnDict

def check_version_1(elements, users):
    """Get the initial version of an element and compare it to a list of users, returns a list of elements that the users created"""
    returnElements = []
    groupedElements = group_elements(elements)
    for elements in tqdm(groupedElements):
        query = "[out:json][timeout:25];"
        for element in elements:
            query += "timeline({osm_type}, {osm_id}, 1); for (t['created']) {{ retro(_.val) {{ {osm_type}(id:{osm_id}); out meta;}} }}".format(osm_type = element["type"], osm_id = element["id"])
        print(query)
        query_json = overpass_query(query)
        queryElements = query_json['elements']
        for rElement in queryElements:
            if ('user' in rElement and rElement['user'] in users) or ('uid' in rElement and rElement['uid'] in users):
                returnElements.append({"type": rElement["type"], "id": rElement["id"]})
    return returnElements

def download_elements(elements):
    """Download specific elements from OSM (uses overpass)"""
    element_list = ""
    for element in elements:
        element_list += "{osm_type}({osm_id});".format(osm_type = element["type"], osm_id = element["id"])
    query = "[out:xml][timeout:25];({elements_formatted}); out body meta; >; out skel qt meta;".format(elements_formatted=element_list)
    result = overpass_query(query)
    save('output', 'bad_elements', result)

def main(query, users):
    if type(users) is str:
        users = [users]
    result = overpass_query(query)
    save('output', 'query_result', result)
    elements = result['elements']
    bad_elements = check_version_1(elements, users)
    download_elements(bad_elements)

query = """
[out:json][timeout:25];(way["building"](39.075931613372134,-108.56493651866913,39.07687902124416,-108.56352165341377);); out body; >; out skel qt;
"""
users = ['vorpalblade']
main(query, users)
#if __name__ == "__main__":
#    """Sample query: [out:json][timeout:25];(way["building"](39.075931613372134,-108.56493651866913,39.07687902124416,-108.56352165341377);); out body; >; out skel qt;, sample user: vorpalblade"""
#    import argparse
#    parser = argparse.ArgumentParser(description='Get the versions of objects from an overpass query modified by a specific set of users')
#    parser.add_argument('-q', '--query', nargs='1', help='Simple overpass query, one line, enclosed by quotes of some kind (you may need to escape interior quotes')
#    parser.add_argument('-u', '--users', nargs='+', help='List of users to filter the query for')
#    args = parser.parse_args()
#
#    print(args.query, args.users)
#    main(args.query, args.users)
