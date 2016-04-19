import time
import json
import datetime

from google.appengine.ext import db
from google.appengine.ext.blobstore import BlobInfo
from google.appengine.ext.blobstore import BlobReferenceProperty 

class ReportSet(db.Model):
    setid = db.StringProperty(required=False)
    uid = db.StringProperty(required=False)
    ostype = db.StringProperty(required=False)
    osversion = db.StringProperty(required=False)
    clrversion = db.StringProperty(required=False)
    appname = db.StringProperty(required=False)
    appversion = db.StringProperty(required=False)
    assembly = db.StringProperty(required=False)

class ReportItem(db.Model):
    reportset = db.ReferenceProperty(required=True)
    timestamp = db.IntegerProperty(required=False)
    eventtype = db.StringProperty(required=False)
    count = db.IntegerProperty(required=False)
    name = db.StringProperty(required=False)
    data = db.TextProperty(required=False)
    counted = db.IntegerProperty(required=False)

class AggregateItem(db.Model):
    # day, month, year or week
    rangetype = db.StringProperty(required=True)

    # eg. 2016-01-01
    # or 2016-01
    # or 2016
    # or 2016-w1
    rangekey = db.StringProperty(required=True)
    timestamp = db.IntegerProperty(required=True)

    value_sum = db.IntegerProperty(required=True)
    entry_count = db.IntegerProperty(required=True)

    ostype = db.StringProperty(required=True)
    name = db.StringProperty(required=True)
    value = db.StringProperty(required=False)
    lastupdated = db.IntegerProperty(required=False)


