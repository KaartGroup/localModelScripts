#!/usr/bin/env python3
import subprocess
import json
import requests
import time
import os
from tqdm import tqdm
name = "bucharest"
#url = """curl '' -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:70.0) Gecko/20100101 Firefox/70.0' -H 'Accept: */*' -H 'Accept-Language: en-US,en;q=0.5' --compressed -H 'Content-Type: application/xml' -H 'X-Requested-With: XMLHttpRequest' -H 'Origin: http://urbanism.pmb.ro' -H 'DNT: 1' -H 'Connection: keep-alive' -H 'Referer: http://urbanism.pmb.ro/' -H 'Cookie: _ga=GA1.2.1779618557.1565878179; ASP.NET_SessionId=rrimniqbuqv2131bdm5fbcsy' --data '<wfs:GetFeature xmlns:wfs="http://www.opengis.net/wfs" service="WFS" version="1.1.0" outputFormat="JSON" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><wfs:Query typeName="pmb:V_PMB_ADRESE" srsName="EPSG:4317" xmlns:pmb="pmb.ro"><ogc:Filter xmlns:ogc="http://www.opengis.net/ogc"><ogc:BBOX><ogc:PropertyName>GEOMETRY1</ogc:PropertyName><gml:Envelope xmlns:gml="http://www.opengis.net/gml" srsName="EPSG:4317"><gml:lowerCorner>{minx} {miny}</gml:lowerCorner><gml:upperCorner>{maxx} {maxy}</gml:upperCorner></gml:Envelope></ogc:BBOX></ogc:Filter></wfs:Query></wfs:GetFeature>'"""
#await fetch(, {
#    "credentials": "include",
#
#    "referrer": "http://urbanism.pmb.ro/",
#    "body": "<wfs:GetFeature xmlns:wfs=\"http://www.opengis.net/wfs\" service=\"WFS\" version=\"1.1.0\" outputFormat=\"JSON\" xsi:schemaLocation=\"http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"><wfs:Query typeName=\"pmb:V_PMB_ADRESE\" srsName=\"EPSG:4317\" xmlns:pmb=\"pmb.ro\"><ogc:Filter xmlns:ogc=\"http://www.opengis.net/ogc\"><ogc:BBOX><ogc:PropertyName>GEOMETRY1</ogc:PropertyName><gml:Envelope xmlns:gml=\"http://www.opengis.net/gml\" srsName=\"EPSG:4317\"><gml:lowerCorner>578946.44361242 326474.72833772</gml:lowerCorner><gml:upperCorner>579591.81816758 326623.06606228</gml:upperCorner></gml:Envelope></ogc:BBOX></ogc:Filter></wfs:Query></wfs:GetFeature>",
#    "mode": "cors"
#});
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:70.0) Gecko/20100101 Firefox/70.0",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Content-Type": "application/xml",
    "X-Requested-With": "XMLHttpRequest"
}
minx = 576298.56088549
miny = 315425.54911521
maxx = 598332.63804522
maxy = 338733.71218472

splits = 100

def get_data():
    stepx = (maxx - minx) / splits
    stepy = (maxy - miny) / splits

    if not os.path.exists(name):
        os.mkdir(name)
    elif not os.path.isdir(name):
        raise ValueError("{} needs to be a directory".format(name))

    data = "<wfs:GetFeature xmlns:wfs=\"http://www.opengis.net/wfs\" service=\"WFS\" version=\"1.1.0\" outputFormat=\"JSON\" xsi:schemaLocation=\"http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.1.0/wfs.xsd\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"><wfs:Query typeName=\"pmb:V_PMB_ADRESE\" srsName=\"EPSG:4317\" xmlns:pmb=\"pmb.ro\"><ogc:Filter xmlns:ogc=\"http://www.opengis.net/ogc\"><ogc:BBOX><ogc:PropertyName>GEOMETRY1</ogc:PropertyName><gml:Envelope xmlns:gml=\"http://www.opengis.net/gml\" srsName=\"EPSG:4317\"><gml:lowerCorner>{minx} {miny}</gml:lowerCorner><gml:upperCorner>{maxx} {maxy}</gml:upperCorner></gml:Envelope></ogc:BBOX></ogc:Filter></wfs:Query></wfs:GetFeature>"
    real_name = name + "_{x}_{y}.geojson"
    for x in tqdm(list(range(0, splits))):
        for y in tqdm(list(range(0, splits))):
            filename = os.path.join(name, real_name.format(x=x, y=y))
            if os.path.exists(filename):
                if check_validity(filename):
                    continue
                tqdm.write("Bad file: {}".format(filename))
                os.remove(filename)
            tqdm.write("Getting {}".format(filename))
            try:
                r = requests.post("http://urbanism.pmb.ro/Proxy.aspx?xz_zx=0&", headers=headers, data=data.format(minx=minx + stepx * x, maxx=minx + stepx * (x + 1), miny=miny + stepy * y, maxy=miny + stepy * (y + 1)))
                with open(filename, 'wb') as fd:
                    for chunk in r.iter_content(chunk_size=128):
                        fd.write(chunk)
                time.sleep(30)
            except requests.exceptions.ConnectionError:
                time.sleep(360)

def check_validity(fileName):
    try:
        with open(fileName) as fh:
            json.load(fh)
        return True
    except json.decoder.JSONDecodeError as e:
        return False

get_data()
