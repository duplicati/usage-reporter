#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
import dbmodel
import json

from google.appengine.ext import db

class MainHandler(webapp2.RequestHandler):
    def get(self):
        return self.redirect('https://github.com/duplicati/usage-reporter')


def setprops(item, props):
    for p in props:
        if not item.has_key(p):
            item[p] = ''
        elif type(item[p]) != type(''):
            item[p] = str(item[p])


@db.transactional(xg=True)
def addPostInTx(rst):

    setprops(rst, ['setid', 'uid', 'ostype', 'osversion', 'clrversion', 'appname', 'appversion', 'assembly'])

    dbr = dbmodel.ReportSet(
        setid = rst['setid'],
        uid = rst['uid'],
        ostype = rst['ostype'],
        osversion = rst['osversion'],
        clrversion = rst['clrversion'],
        appname = rst['appname'],
        appversion = rst['appversion'],
        assembly = rst['assembly']
    )

    dbr.put()

    for n in rst['items']:

        setprops(n, ['type', 'name', 'data'])

        ts = 0
        c = 0
        data = None


        try:
            if (n.has_key('timestamp')):
                ts = long(n['timestamp'])
        except:
            pass

        try:
            if (n.has_key('count')):
                c = long(n['count'])
        except:
            pass

        ri = dbmodel.ReportItem(
            reportset = dbr, 
            timestamp = ts,
            eventtype = n['type'],
            count = c,
            name = n['name'],
            data = n['data']
        ).put()



class ReportHandler(webapp2.RequestHandler):
    def post(self):
        rst = json.loads(self.request.body)
        if rst['items'] != None and type(rst['items']) == type([]) and len(rst['items']) > 0:
            addPostInTx(rst)



app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/api/v1/report', ReportHandler)
], debug=True)
