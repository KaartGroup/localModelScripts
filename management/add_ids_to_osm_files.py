#!/usr/bin/env python3
import os
import glob
from tqdm import tqdm
import xml.etree.ElementTree as ET

def add_versions_to_file(filename):
    tree = ET.parse(filename)
    root = tree.getroot()
    if 'version' in root.attrib and float(root.attrib['version']) >= 0.6 and 'generator' in root.attrib and root.attrib['generator'] == "JOSM":
        for child in tqdm(root, position=0):
            if 'version' not in child.attrib:
                child.set('version', '0')
    filename_parts = os.path.splitext(filename)
    temporary_filename = "{}.versions.{}".format(filename_parts[0], filename_parts[1])
    tree.write(temporary_filename, xml_declaration=True, encoding="UTF-8")
    os.rename(temporary_filename, filename)


if __name__ == "__main__":
    exts = ['.osm']
    filenames = []
    for ext in exts:
        filenames.extend(glob.glob("*.{}".format(ext.strip('.'))))
    for filename in tqdm(filenames, position=1):
        add_versions_to_file(filename)
