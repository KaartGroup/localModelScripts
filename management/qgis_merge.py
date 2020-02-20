#!/usr/bin/env python
import sys
if sys.platform == "linux" or sys.platform == "linux2":
    sys.path.append('/usr/share/qgis/python/plugins')
elif sys.platform == "darwin":
    sys.path.append('/Applications/QGIS3.8.app/Contents/Resources/python/plugins/')
import qgis
from qgis.core import *

app = QgsApplication([],True, None)
app.setPrefixPath("/usr", True)
app.initQgis()

from processing.core.Processing import Processing
Processing.initialize()
from processing.tools import *

Processing.initialize()

