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
