import webapp2
import dbmodel
import json
import logging
import datetime
import calendar
import os

from google.appengine.ext import db

TESTING = os.environ.get('SERVER_SOFTWARE','').startswith('Development')


class ResetHandler(webapp2.RequestHandler):
    def get(self):
        timestamp = calendar.timegm(datetime.datetime.utcnow().timetuple())
        self.response.write('<html><body><form method="POST"><input type="text" value="' + str(timestamp) + '" name="day"><input type="submit"></form></body></html>')

    def post(self):

        timestamp = int(self.request.get('day', None))

        entry_day = datetime.datetime.utcfromtimestamp(timestamp).date()
        logging.info('Processing day %s', entry_day)

        starttimestamp = calendar.timegm((entry_day.year, entry_day.month, entry_day.day, 0, 0, 0))
        endtimestamp = starttimestamp + 24*60*60

        logging.info('starttimestamp, endtimestamp: (%s, %s)', starttimestamp, endtimestamp)

        count = 0
        for item in dbmodel.ReportItem.all().filter('counted', 0).filter('eventtype =', 'Information').filter('timestamp <', endtimestamp).filter('timestamp >=', starttimestamp).order('timestamp'):
            item.counted = None
            item.put()
            count += 1

        for item in dbmodel.ReportItem.all().filter('counted', 1).filter('eventtype =', 'Information').filter('timestamp <', endtimestamp).filter('timestamp >=', starttimestamp).order('timestamp'):
            item.counted = None
            item.put()
            count += 1

        logging.info('Reset for %s items', count)
        for item in dbmodel.AggregateItem.all().filter('timestamp =', starttimestamp).filter('rangetype =', 'day'):
            item.delete()


app = webapp2.WSGIApplication([
    ('/tasks/admin/reset', ResetHandler)
], debug=TESTING)
