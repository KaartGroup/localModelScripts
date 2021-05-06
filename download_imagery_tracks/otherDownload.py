#!/usr/bin/env python3


import requests

import geojson

import json


bbox = "22.8744007137,37.4580785688,24.2452455547,38.4786181989"
bbox = "21.3,-17.3,35.9468874,-1.0052545"

user_name = "kaartcam"


url = "https://a.mapillary.com/v3/sequences?bbox={}&usernames=kaartcam&client_id=b0xndnlwSEhNaGNteG13bVZnLU81QTo3YmM0ZWZhYTQ1NTc5NzUy".format(
    bbox
)


url2 = "https://a.mapillary.com/v3/sequences?usernames=kaartcam&client_id=b0xndnlwSEhNaGNteG13bVZnLU81QTo3YmM0ZWZhYTQ1NTc5NzUy"


user_bbox_url = "https://a.mapillary.com/v3/sequences?usernames={}&bbox={}&client_id=b0xndnlwSEhNaGNteG13bVZnLU81QTo3YmM0ZWZhYTQ1NTc5NzUy".format(
    user_name, bbox
)

request = requests.get(user_bbox_url, timeout=600)
first_page = ""
try:
    first_page = request.json()
except json.decoder.JSONDecodeError as e:
    print(request.text)
    raise e

if "next" in requests.head(user_bbox_url).links:
    next_url = requests.head(user_bbox_url).links["next"]["url"]
else:
    next_url = None

result = first_page


features = first_page["features"]

# geoms = features['geometries']

# print(features)


# image_keys = first_page['features']['properties']['image_keys']

# cas = first_page['features']['properties']['cas']

# images = zip(image_keys, cas)


while next_url:

    features.extend(requests.get(next_url).json()["features"])

    #    result = requests.get(next_url).json()['features']['properties']

    #   images.update(zip(result['image_keys'], result['cas']))

    try:

        next_url = requests.head(next_url).links["next"]["url"]

    except KeyError:

        next_url = None


# for image_key, cas in images.items():


with open("test.geojson", "w") as f:

    geojson.dump(geojson.FeatureCollection(features), f)
