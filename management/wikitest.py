#!/usr/bin/env python3
import sys
if sys.platform == "darwin":
    sys.path = sys.path + ['/Library/Frameworks/SQLite3.framework/Versions/E/Python/3.6', '/Library/Frameworks/Python.framework/Versions/3.6/lib/python36.zip', '/Library/Frameworks/Python.framework/Versions/3.6/lib/python3.6', '/Library/Frameworks/Python.framework/Versions/3.6/lib/python3.6/lib-dynload', '/Library/Frameworks/Python.framework/Versions/3.6/lib/python3.6/site-packages']
import json
import requests
import string
try:
    import uno
    DEBUG = 0
except ImportError:
    import doctest
    DEBUG = 1
import ssl
import datetime
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache
import tempfile
import os

USERAGENT = {'User-agent': 'LibreofficeProjectMacro/0.1 (taylor.smock@kaartgroup.com)'}

CACHE_DIRECTORY = os.path.join(tempfile.gettempdir(), 'LibreofficeProjectMacro')
WIKILOGINS = {}
cached_session = CacheControl(requests.session(), cache = FileCache(CACHE_DIRECTORY))
cached_session.headers.update(USERAGENT)

def writeInformation(level, information):
    try:
        global CURRENT_INFORMATION_ROW
        desktop = XSCRIPTCONTEXT.getDesktop()
        model = desktop.getCurrentComponent()
        sheet = config('Information')
        if not model.Sheets.hasByName(sheet):
            model.Sheets.insertNewByName(sheet, model.Sheets.getCount() + 1)
        sheet = model.Sheets.getByName(sheet)
        try:
            index = CURRENT_INFORMATION_ROW
        except NameError:
            index = 1
        levelCell = sheet.getCellRangeByName("A" + str(index))
        informationCell = sheet.getCellRangeByName("B" + str(index))
        datetimeCell = sheet.getCellRangeByName("C" + str(index))
        if index <= 1:
            levelCell.setString("Level")
            informationCell.setString("Message")
            datetimeCell.setString("Date and Time")
        while (levelCell.getType().value != "EMPTY"):
            index = index + 1
            levelCell = sheet.getCellRangeByName("A" + str(index))
        levelCell = sheet.getCellRangeByName("A" + str(index))
        informationCell = sheet.getCellRangeByName("B" + str(index))
        datetimeCell = sheet.getCellRangeByName("C" + str(index))
        levelCell.setString(level)
        informationCell.setString(str(information))
        datetimeCell.setString(str(datetime.datetime.now()))
        CURRENT_INFORMATION_ROW = index
    except Exception as e:
        print(type(e))
        print(information)

def loginToWiki(wiki, username = None, password = None):
    """ login to a wiki
    >>> token = loginToWiki("https://wiki.openstreetmap.org/w/api.php", username = "Vorpalblade77-kaart@testbot", password = "mp7bdbmuq4vs4p9aj6tt8s7f302kh5pl")
    >>> token2 = loginToWiki("https://wiki.openstreetmap.org/w/api.php", username = "Vorpalblade77-kaart@testbot", password = "mp7bdbmuq4vs4p9aj6tt8s7f302kh5pl")
    >>> token == token2
    True
    """
    global WIKILOGINS
    if wiki in WIKILOGINS:
        return WIKILOGINS[wiki]
    if (username is None or password is None):
        desktop = XSCRIPTCONTEXT.getDesktop()
        model = desktop.getCurrentComponent()
        sheet = config("Wikipedia")
        if not model.Sheets.hasByName(sheet):
            model.Sheets.insertNewByName(sheet, model.Sheets.getCount() + 1)
            sheet = model.Sheets.getByName(sheet)
            sheet.getCellRangeByName("A1").setString("URL")
            sheet.getCellRangeByName("A2").setString("Username")
            sheet.getCellRangeByName("A3").setString("Password")
        else:
            sheet = model.Sheets.getByName(sheet)
        urlColumn = getColumn("URL")
        userColumn = getColumn("Username")
        passwordColumn = getColumn("Password")
        index = 2
        levelCell = sheet.getCellRangeByName(urlColumn + str(index))
        while (levelCell.getType().value != "EMPTY"):
            if (levelCell.String == wiki):
                break
            index = index + 1
            levelCell = sheet.getCellRangeByName(urlColumn + str(index))
        username = sheet.getCellRangeByName(userColumn + str(index))
        password = sheet.getCellRangeByName(passwordColumn + str(index))
    logintokens = cached_session.get(url = wiki, params = {"action": "query", "meta": "tokens", "type": "login", "maxlag": 5, "format": "json"}).json()["query"]["tokens"]["logintoken"]
    cached_session.post(wiki, data = { "action": "login", "lgname": username, "lgpassword": password, "lgtoken": logintokens})
    CSRF = cached_session.get(url=wiki, params = { "action": "query", "meta": "tokens", "maxlag": 5, "format": "json"}).json()["query"]["tokens"]["csrftoken"]
    WIKILOGINS = {wiki: CSRF}
    return CSRF

def readFromWiki(wiki, page, username = None, password = None):
    """
    Get data from wiki
    >>> readFromWiki("https://wiki.openstreetmap.org/w/api.php", "Sandbox", username = "Vorpalblade77-kaart@testbot", password = "mp7bdbmuq4vs4p9aj6tt8s7f302kh5pl")['title']
    'Sandbox'
    """
    if (username is None or password is None):
        CSRF = loginToWiki(wiki)
    else:
        CSRF = loginToWiki(wiki, username = username, password = password)

    response = cached_session.post(wiki, data={"action": "parse", "page": page, "prop": "wikitext", "format": "json"})
    return response.json()['parse']

def writeToWiki(wiki, page, informationJson, username = None, password = None):
    if (username is None or password is None):
        CSRF = loginToWiki(wiki)
    else:
        CSRF = loginToWiki(wiki, username = username, password = password)
    data = readFromWiki(wiki, page)
    wikitext = data['wikitext']['*']
    oldwikitext = wikitext
    table_header = informationJson['table_text'].split("|")[2][1:]
    table_locations = []
    table_location = wikitext.find(table_header)
    while (table_location > 0):
        table_locations.append(table_location)
        table_location = wikitext.find(table_header, table_location + 1)
    if len(table_locations) == 0:
        wikitext += table_text
    if (oldwikitext != wikitext):
        writeInformation(config("Information"), cached_session.post(wiki, data={"action": "edit", "title": page, "format": "json", "maxlag": 5, "text": wikitext, "token": CSRF}))
    else:
        writeInformation(config("Information"), "Don't need to write tables for {}".format(page))

if __name__ == "__main__":
    doctest.testmod()
