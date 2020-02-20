#!/usr/bin/env python3
import os
import glob
import requests
from dateutil import parser
import datetime
import zipfile
import shutil
import subprocess
ADDRESSES = {
    "nelsonMandelaBay": {"url": "http://nelsonmandelabay.gov.za/DataRepository/Documents/address-points.zip", "addr:street": "StreetName", "addr:housenumber": "StreetNo", "addr:suburb": "Suburb", "alt_addr:street": "StreetNa_1", "alt_addr:housenumber": "StreetNoSe"},
    #"capeTown": {"url": "https://opendata.arcgis.com/datasets/c2101858187f424298f85e60f9706533_54.zip"},
    "ethekwini": {"url": "http://gis.durban.gov.za/datadownloads/Street_Address.zip"}, # Also has building footprints
    "countrywide": {"url": "https://data.openaddresses.io/cache/uploads/sergiyprotsiv/a76ed3/za-countrywide.csv.zip"}
}


def unzipFile(filename):
    ext = os.path.splitext(filename)[1]
    address = os.path.splitext(filename)[0]
    if "zip" in ext:
        if os.path.isdir(address):
            shutil.rmtree(address)
        os.mkdir(address)
        with zipfile.ZipFile(filename, 'r') as zfile:
            zfile.extractall(path=address)

def translate_file(filename, translation=None):
    # TODO add automatic translations
    filenamesplit = os.path.splitext(filename)
    if len(filenamesplit) >= 2 and "csv" in filenamesplit[1]:
        print("You need to convert {} to another format".format(filename))
        return
    cmd = ["./ogr2osm/ogr2osm.py"]
    if translation:
        cmd.append("--translation=" + translation)
    cmd.append("--output=" + filenamesplit[0] + ".osm")
    cmd.append(filename)
    subprocess.check_output(cmd)

def find_ogr_file(directory):
    extensions = ["shp", "kml", "osm", "csv"]
    for ext in extensions:
        files = glob.glob("**/*." + ext)
        if len(files) > 0:
            return files[0]

def download_file(url, filename):
    with requests.get(url, stream=True) as response:
        response.raise_for_status()
        with open(filename, 'wb') as save_file:
            for chunk in response.iter_content(chunk_size=8192):
                save_file.write(chunk)

def check_if_download_required(url, saveName):
    headers = {}
    fileModified = None
    if os.path.isfile(saveName):
        print("Found file", saveName)
        fileModified = datetime.datetime.fromtimestamp(os.path.getmtime(saveName), tz=datetime.timezone.utc)
        headers = {"If-Modified-Since": fileModified.strftime("%a, %d %b %Y %H:%M:%S GMT")}
    resp = requests.head(url, headers=headers)
    serverModified = parser.parse(resp.headers['last-modified'])
    download = True
    if fileModified:
        if (fileModified > serverModified):
            download = False
    return download

def getData(addresses):
    for address in addresses:
        url = addresses[address]["url"]
        ext = os.path.splitext(url)[1]
        saveName = address + ext
        print(saveName)
        download = check_if_download_required(url, saveName)
        # Save the file for comparisons (i.e., if the old file was fully imported, we can just do a diff and focus on those)
        if download and os.path.isfile(saveName):
            os.rename(saveName, address + '.' + str(fileModified) + ext)
        if download:
            download_file(url, saveName)
        # TODO indent following once done testing
            unzipFile(saveName)
        ogr_file = find_ogr_file(os.path.splitext(saveName)[0])
        if "translation" in addresses[address]:
            translate_file(ogr_file, translation = addresses[address]["translation"])
        else:
            translate_file(ogr_file)
        # End TODO indent

if __name__ == "__main__":
    getData(ADDRESSES)
