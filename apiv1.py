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
import calendar
import datetime
import json
import logging

import webapp2
from google.appengine.api import memcache
from google.appengine.ext import db

import dbmodel


def setprops(item, props):
    for p in props:
        if not item.has_key(p):
            item[p] = ''
        elif type(item[p]) != type('') and type(item[p]) != type(u''):
            item[p] = str(item[p])


@db.transactional(xg=True)
def addPostInTx(rst):
    setprops(rst, ['setid', 'uid', 'ostype', 'osversion', 'clrversion', 'appname', 'appversion', 'assembly'])

    dbr = dbmodel.ReportSet(
        setid=rst['setid'],
        uid=rst['uid'],
        ostype=rst['ostype'],
        osversion=rst['osversion'],
        clrversion=rst['clrversion'],
        appname=rst['appname'],
        appversion=rst['appversion'],
        assembly=rst['assembly']
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
            reportset=dbr,
            timestamp=ts,
            eventtype=n['type'],
            count=c,
            name=n['name'],
            data=n['data']
        ).put()


class ReportHandler(webapp2.RequestHandler):
    def post(self):
        try:
            if len(self.request.body) > 0:
                rst = json.loads(self.request.body)
                if rst['items'] != None and type(rst['items']) == type([]) and len(rst['items']) > 0:
                    addPostInTx(rst)
        except:
            logging.info('Failed to load: %s', self.request.body)
            raise


class ViewHandler(webapp2.RequestHandler):
    def write_input_error(message):
        self.response.set_status(400, message)
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(json.dumps({'error': message}))

    def get(self):
        starttime = self.request.get('fromtime', None)
        rangetype = self.request.get('rangetype', None)
        page_size = self.request.get('page_size', None)
        page_offset = self.request.get('page_offset', None)

        try:
            starttime = int(starttime)
        except:
            starttime = None

        try:
            page_size = int(page_size)
        except:
            page_size = None

        try:
            page_offset = int(page_offset)
        except:
            page_offset = None

        if starttime == None:
            ts = datetime.datetime.utcnow()
            starttime = calendar.timegm((ts.year, ts.month, ts.day, 0, 0, 0))

        if rangetype == None:
            rangetype = 'day'

        rangetype = rangetype.lower()
        if not rangetype in ['day', 'week', 'month', 'year']:
            self.write_input_error('No rangetype supplied')
            return

        if page_offset == None:
            page_offset = 0
        if page_size == None:
            page_size = 5

        if page_offset < 0:
            self.write_input_error('Invalid page_offset supplied')
            return
        if page_size < 0 or page_size > 500:
            self.write_input_error('Invalid page_size supplied')
            return

        ix = memcache.get('aggregate-' + rangetype)
        if ix == None or type(ix) != type(1):
            ix = 0

        cacheurl = '%s:/view?fromtime=%s&rangetype=%s&page_size=%s&page_offset=%s' % (
        ix, starttime, rangetype, page_size, page_offset)
        res = memcache.get(cacheurl)

        if res == None:
            remains = page_size
            prevtime = None
            items = []

            for x in dbmodel.AggregateItem.all().filter('timestamp <=', starttime).filter('rangetype', rangetype).order(
                    '-timestamp').run(offset=page_offset):
                if prevtime != x.timestamp:
                    prevtime = x.timestamp
                    if remains == 0:
                        break
                    remains -= 1

                items.append(
                    {'name': x.name, 'value': x.value, 'ostype': x.ostype, 'sum': x.value_sum, 'count': x.entry_count,
                     'lastupdated': x.lastupdated, 'timestamp': x.timestamp})

            res = json.dumps({'kind': 'aggregate-' + rangetype, 'page_size': page_size, 'offset': page_offset,
                              'next_offset': page_offset + len(items), 'count': len(items), 'fromtime': starttime,
                              'rangetype': rangetype, 'items': items,
                              'fetched': calendar.timegm(datetime.datetime.utcnow().timetuple())})

            memcache.add(cacheurl, res)

        self.response.status = 200
        self.response.headers['Content-Type'] = 'application/json'
        self.response.write(res)


app = webapp2.WSGIApplication([
    ('/api/v1/report', ReportHandler),
    ('/api/v1/view', ViewHandler)
], debug=True)
