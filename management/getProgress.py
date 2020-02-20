#!/usr/bin/env python3
import sys
import os
if sys.platform == "darwin":
    sys.path = sys.path + ['/Library/Frameworks/SQLite3.framework/Versions/E/Python/3.6', '/Library/Frameworks/Python.framework/Versions/3.6/lib/python36.zip', '/Library/Frameworks/Python.framework/Versions/3.6/lib/python3.6', '/Library/Frameworks/Python.framework/Versions/3.6/lib/python3.6/lib-dynload', '/Library/Frameworks/Python.framework/Versions/3.6/lib/python3.6/site-packages']
import json
import tempfile
import datetime
import string
import ssl
try:
    import uno
    DEBUG = 0
except ImportError:
    import doctest
    DEBUG = 1
import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache

MAXSIZE = 1000

USERAGENT = {'User-agent': 'LibreofficeProjectMacro/0.1 (taylor.smock@kaartgroup.com)'}

CACHE_DIRECTORY = os.path.join(tempfile.gettempdir(), 'LibreofficeProjectMacro')

CURRENT_INFORMATION_ROW = 1

CACHED_SESSION = CacheControl(requests.session(), cache=FileCache(CACHE_DIRECTORY))
CACHED_SESSION.headers.update(USERAGENT)

def setDefaults(sheet):
    VARIABLES['variable'] = 'value'
    VARIABLES['Projects'] = 'Projects'
    VARIABLES['Information'] = 'Information'
    VARIABLES['Wikipedia'] = 'Wikipedia'
    VARIABLES['URL'] = 'URL'
    writeConfig(sheet, VARIABLES)

def writeConfig(sheet, variables):
    index = 1
    for key in variables:
        if (key == "time_read"):
            continue
        keyCell = sheet.getCellRangeByName("A" + str(index))
        valueCell = sheet.getCellRangeByName("B" + str(index))
        keyCell.setString(key)
        valueCell.setString(variables[key])
        index += 1

def readConfig(sheet):
    returnVariables = {}
    index = 2
    configCellKey = sheet.getCellRangeByName("A" + str(index))
    while (configCellKey.getType().value != "EMPTY"):
        configCellKey = sheet.getCellRangeByName("A" + str(index))
        configCellValue = sheet.getCellRangeByName("B" + str(index))
        returnVariables[configCellKey.getString()] = configCellValue.getString()
        index += 1
    return returnVariables

VARIABLES = None
def config(variable, sheet=None):
    desktop = XSCRIPTCONTEXT.getDesktop()
    model = desktop.getCurrentComponent()
    if sheet is None:
        sheet = "configuration"
    try:
        if (datetime.datetime.utcnow() - VARIABLES['time_read']).total_seconds() < 60:
            return VARIABLES[variable]
    except (NameError, KeyError, TypeError):
        global VARIABLES
        VARIABLES = {}

    if not model.Sheets.hasByName(sheet):
        model.Sheets.insertNewByName(sheet, model.Sheets.getCount() + 1)
        setDefaults(model.Sheets.getByName(sheet))
    sheet = model.Sheets.getByName(sheet)
    VARIABLES = readConfig(sheet)
    VARIABLES['time_read'] = datetime.datetime.utcnow()
    try:
        return VARIABLES[variable]
    except KeyError:
        VARIABLES[variable] = variable
        writeConfig(sheet, VARIABLES)
        return VARIABLES[variable]

def writeInformation(level, information):
    desktop = XSCRIPTCONTEXT.getDesktop()
    model = desktop.getCurrentComponent()
    sheet = config('Information')
    if not model.Sheets.hasByName(sheet):
        model.Sheets.insertNewByName(sheet, model.Sheets.getCount() + 1)
    sheet = model.Sheets.getByName(sheet)
    try:
        index = CURRENT_INFORMATION_ROW
    except NameError:
        global CURRENT_INFORMATION_ROW
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

WIKILOGINS = {}
def loginToWiki(wiki):
    if wiki in WIKILOGINS:
        return WIKILOGINS[wiki]
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
    session = CacheControl(requests.session())
    session.headers.update(USERAGENT)
    logintokens = session.get(url = wiki, params = {"action": "query", "meta": "tokens", "type": "login", "maxlag": 5, "format": "json"}).json()["query"]["tokens"]["logintoken"]
    session.post(wiki, data = { "action": "login", "lgname": username, "lgpassword": password, "lgtoken": logintokens})
    CSRF = session.get(url=wiki, params = { "action": "query", "meta": "tokens", "maxlag": 5, "format": "json"}).json()["query"]["tokens"]["csrftoken"]
    WIKILOGINS = {wiki: CSRF}
    return CSRF

def writeToWiki(wiki, page, tableHeader, informationJson):
    CSRF = loginToWiki(wiki)
    writeInformation(config("Information"), session.post(url, data={"action": "edit", "title": page, "format": "json", "maxlag": 5, "token": CSRF}))


STORED_COLUMNS = {}
def getColumn(columnHeader, sheet_name = None):
    desktop = XSCRIPTCONTEXT.getDesktop()
    model = desktop.getCurrentComponent()
    if sheet_name is None:
        sheet = model.CurrentController.ActiveSheet
    elif isinstance(sheet_name, str):
        sheet = model.Sheets.getByName(sheet_name)
    else:
        sheet = sheet_name
    active_sheet_name = sheet.AbsoluteName
    if active_sheet_name + columnHeader in STORED_COLUMNS:
        return STORED_COLUMNS[active_sheet_name + columnHeader]
    if not hasattr(model, "Sheets"):
        model = desktop.loadComponentFromURL(
            "private:factory/scalc","_blank", 0, () )
    emptyLetter = None
    for letter in string.ascii_uppercase:
        tCell = sheet.getCellRangeByName("{}1".format(letter))
        if (tCell.String == columnHeader):
            STORED_COLUMNS[active_sheet_name + columnHeader] = letter
            return letter
        elif (emptyLetter is None and tCell.getType().value == "EMPTY"):
            emptyLetter = letter
    if emptyLetter is not None:
        tCell = sheet.getCellRangeByName("{}1".format(letter))
        tCell.setValue(columnHeader)
        STORED_COLUMNS[active_sheet_name + columnHeader] = emptyLetter
        return emptyLetter
    else:
        return 'Z'

def getDataUrl(url):
    if "maproulette" in url:
        return "https://maproulette.org/api/v2/challenge/{pid}"
    else:
        return url[:url.index('/project/')] + "/api/v1/stats/project/{pid}"

def getProjectId(url):
    return url[url.rfind('/'):].strip('/')

def countTasks(task_data):
    count = 0
    if 'features' in task_data:
        for i in task_data['features']:
            count += 1
    return count

def getTaskUrl(url):
    if "maproulette" in url:
        return "https://maproulette.org/api/v2/challenge/{pid}/tasks?limit=0"
        #return "https://maproulette.org/api/v2/data/challenge/{pid}" Gets status without any calculation
    else:
        return url[:url.index('/project')] + '/api/v1/project/{pid}/tasks?as_file=false'

def parse_maproulette(task_data):
    created = 0
    fixed = 0
    false_positive = 0
    skipped = 0
    deleted = 0
    already_fixed = 0
    too_hard = 0
    disabled = 0

    review_needed = 0
    review_approved = 0
    review_rejected = 0
    review_approved_with_fixes = 0
    review_disputed = 0
    review_not_set = 0

    for task in task_data:
        if "status" in task:
            status = task["status"]
            if status == 0:
                created += 1
            elif status == 1:
                fixed += 1
            elif status == 2:
                false_positive += 1
            elif status == 3:
                skipped += 1
            elif status == 4:
                deleted += 1
            elif status == 5:
                already_fixed += 1
            elif status == 6:
                too_hard += 1
            elif status == 9:
                disabled += 1
        if "reviewStatus" in task_data:
            status = task_data["reviewStatus"]
            if status == 0:
                review_needed += 1
            elif status == 1:
                review_approved += 1
            elif status == 2:
                review_rejected += 1
            elif status == 3:
                review_approved_with_fixes += 1
            elif status == 4:
                review_disputed += 1
            elif status == -1:
                review_not_set += 1
    return {"tasks": {"created": created, "fixed": fixed, "false_positive": false_positive, "skipped": skipped, "deleted": deleted, "already_fixed": already_fixed, "too_hard": too_hard, "disabled": disabled}, "review": {"review_needed": review_needed, "review_approved": review_approved, "review_rejected": review_rejected, "review_approved_with_fixes": review_approved_with_fixes, "review_disputed": review_disputed, "review_not_set": review_not_set}}

def getProgress(url, row, validatedColumn, completedColumn, taskCountColumn):
    desktop = XSCRIPTCONTEXT.getDesktop()
    model = desktop.getCurrentComponent()
    sheet = model.Sheets.getByIndex(0)

    dataUrl = getDataUrl(url)
    projectId = getProjectId(url)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    session = CacheControl(requests.session())
    session.headers.update(USERAGENT)
    with session.get(dataUrl.format(pid=projectId)) as response:
        if (response.status_code == 200):
            json_data = response.json()
        else:
            writeInformation("ERROR", "{} had a {} response ({})".format(response.url, response.status_code, response.text))
            return None
    tComplete = sheet.getCellRangeByName(completedColumn + str(row))
    tValidated = sheet.getCellRangeByName(validatedColumn + str(row))
    tTask = sheet.getCellRangeByName(taskCountColumn + str(row))

    taskUrl = getTaskUrl(url)
    with CACHED_SESSION.get(taskUrl.format(pid=projectId)) as response:
        if (response.status_code == 200):
            task_data = response.json()
        else:
            writeInformation("ERROR", "{} had a {} response ({})".format(response.url, response.status_code, response.text))
            return None

    tCreated = sheet.getCellRangeByName(getColumn(config('Created')) + str(row))
    tDone = sheet.getCellRangeByName(getColumn(config('Done')) + str(row))
    if tCreated.getType().value == "EMPTY":
        tCreated.setString(json_data['created'][:10])

    if 'percentMapped' in json_data and 'percentValidated' in json_data:
        complete = json_data['percentMapped'] / 100
        validated = json_data['percentValidated'] / 100
        if tTask.getType().value == "EMPTY":
            totalTasks = countTasks(task_data)
            tTask.setValue(totalTasks)
        tComplete.setValue(complete)
        tValidated.setValue(validated)
        if 'projectStatus' in json_data and json_data['projectStatus'] == "ARCHIVED" and tDone.getType().value == "EMPTY":
            tDone.setString(json_data['lastUpdated'][:10])
    elif len(task_data) > 0 and "id" in task_data[0] and "status" in task_data[0]:
        maproulette_parse = parse_maproulette(task_data)
        totalTasks = 0
        writeInformation("Information", "{}: {}".format(response.url, maproulette_parse))
        for item in maproulette_parse["tasks"]:
            totalTasks += maproulette_parse["tasks"][item]
        totalReview = 0
        for item in maproulette_parse["review"]:
            totalReview += maproulette_parse["review"][item]
        tTask.setValue(totalTasks)
        tComplete.setValue((totalTasks - maproulette_parse["tasks"]["created"]) / totalTasks)
        if (totalReview != 0):
            tValidated.setValue((maproulette_parse["review"]["review_approved"] + maproulette_parse["review"]["review_approved_with_fixes"]) / totalReview)

    elif len(task_data) > 0 and 'actions' in task_data[0] and 'total' in task_data[0]['actions'] and 'available' in task_data[0]['actions']:
        total = task_data[0]['actions']['total']
        available = task_data[0]['actions']['available']
        if available == 0 and 'modified' in json_data and tDone.getType().value == "EMPTY":
            tDone.setString(json_data['modified'][:10])
        tComplete.setValue(1 - float(available) / total)
        tTask.setValue(total)
    else:
        print(dataUrl.format(pid=projectId))
        print(json_data)
    return None

def run(*args):
    desktop = XSCRIPTCONTEXT.getDesktop()
    model = desktop.getCurrentComponent()
    if model.Sheets.hasByName(config("Information")):
        model.Sheets.removeByName(config("Information"))
        writeInformation("Information", "Recreated information sheet")
    CURRENT_INFORMATION_ROW = 1
    sheet = model.Sheets.getByName((config('Projects')))

    validatedColumn = getColumn('Percent Validated', sheet_name = sheet)
    completedColumn = getColumn('Percent Complete', sheet_name = sheet)
    taskCountColumn = getColumn('Total Tasks', sheet_name = sheet)
    doneColumn = getColumn('Done', sheet_name = sheet)
    urlColumn = getColumn('URL', sheet_name = sheet)
    index = 2
    projectColumn = getColumn('Project', sheet_name = sheet)
    tCell = sheet.getCellRangeByName(projectColumn + str(index))
    while (tCell.String != None and tCell.String != ""):
        urlCell = sheet.getCellRangeByName(urlColumn + str(index))
        doneCell = sheet.getCellRangeByName(doneColumn + str(index))
        if ("http" in urlCell.getString()) and (doneCell.getType().value != "VALUE"):
            writeInformation("Information", "{} is being processed".format(urlCell.getString()))
            getProgress(urlCell.getString(), index, validatedColumn, completedColumn, taskCountColumn)
        else:
            writeInformation("Information", "{} was skipped".format(tCell.getString()))

        index += 1
        tCell = sheet.getCellRangeByName(projectColumn + str(index))

if __name__ == "__main__":
    localContext = uno.getComponentContext()
    resolver = localContext.ServiceManager.createInstanceWithContext("com.sun.star.bridge.UnoUrlResolver", localContext)
    ctx = resolver.resolve( "uno:socket,host=localhost,port=2002;urp;StarOffice.ComponentContext" )
    smgr = ctx.ServiceManager
    desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
    model = desktop.getCurrentComponent()
    run()
