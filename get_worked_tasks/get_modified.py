#!/usr/bin/env python3
import os
import requests
from cachecontrol import CacheControl
from cachecontrol.caches import FileCache
import tempfile

PROJECTS = [356]
USERS = ['jptolosa87']

TASK_MANAGER = "https://tasks.kaart.com"

CACHE_DIRECTORY = os.path.join(tempfile.gettempdir(), 'task_modified')
cached_session = CacheControl(requests.session(), cache = FileCache(CACHE_DIRECTORY))

def getModifiedTasksInProject(project):
    api = "api/v1/project/{pid}".format(pid=project)
    with cached_session.get("/".join([TASK_MANAGER, api])) as response:
        response.raise_for_status()
        json_data = response.json()
    tasks = json_data['tasks']['features']

    return findModifiedTasks(project, tasks)

def findModifiedTasks(project, tasks):
    api = "api/v1/project/{project}/task/{task}"
    modified_tasks = []
    for task in tasks:
        properties = task['properties']
        if properties['taskStatus'] == "READY":
            with cached_session.get("/".join([TASK_MANAGER, api.format(project = project, task = properties['taskId'])])) as response:
                response.raise_for_status()
                json_data = response.json()
            if len(json_data['taskHistory']) > 0:
                modified_tasks.append(json_data)
    return modified_tasks

def filterTasksForUsers(tasks, users):
    user_tasks = []
    for task in tasks:
        for modified in task['taskHistory']:
            if modified['actionBy'] in users:
                user_tasks.append(task['taskId'])
    return user_tasks

if __name__ == "__main__":
    URL="project/{project}?task={task}"
    for project in PROJECTS:
        modified_tasks = getModifiedTasksInProject(project)
        filtered_tasks = filterTasksForUsers(modified_tasks, USERS)
        for task in filtered_tasks:
            print("/".join([TASK_MANAGER, URL.format(project = project, task = task)]))
