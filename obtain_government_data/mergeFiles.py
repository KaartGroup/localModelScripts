#!/usr/bin/env python3
import json
import os
import glob
import sys

def merge_json(files, save_file):
    if (len(files) == 0):
        return
    json_data = {}
    for fh in files:
        with open(fh) as fd:
            try:
                data = json.load(fd)
                for item in data:
                    if item in json_data and type(data[item]) == type(json_data[item]) and type(data[item]) == list:
                        for entry in data[item]:
                            json_data[item].append(entry)
                    else:
                        json_data[item] = data[item]
            except json.decoder.JSONDecodeError as e:
                print("Bad json file: {}".format(fh))
    with open(save_file, 'w') as save:
        print(save_file)
        json.dump(json_data, save, indent="  ")


def main(directory):
    json_files = sorted(glob.glob(os.path.join(directory, '*.json')))
    geojson_files = sorted(glob.glob(os.path.join(directory, '*.geojson')))
    merge_json(json_files, os.path.normpath(directory) + '.json')
    merge_json(geojson_files, os.path.normpath(directory) + '.geojson')


if __name__ == "__main__":
    if (len(sys.argv) == 1):
        print("We need a directory or set of directories")
    for directory in sys.argv[1:]:
        main(directory)
