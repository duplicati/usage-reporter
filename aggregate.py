import webapp2
import dbmodel
import json
import logging
import datetime
import calendar
import os

from google.appengine.ext import db
from google.appengine.api import memcache
from google.appengine.api import taskqueue

TESTING = os.environ.get('SERVER_SOFTWARE','').startswith('Development')


class AggregateHandler(webapp2.RequestHandler):
    def post(self):
        self.get()

    def get(self):
        today_ts = None

        try:
            today_ts = int(self.request.get('timestamp', None))
        except:
            pass

        if today_ts == None:
            min_day_entry = dbmodel.ReportItem.all().filter('counted =', None).filter('eventtype =', 'Information').order('timestamp').get()
            if min_day_entry == None:
                logging.info('No unprocessed entries, choosing today')
                today_ts = calendar.timegm(datetime.datetime.utcnow().timetuple())
            else:
                today_ts = min_day_entry.timestamp

        today = datetime.datetime.utcfromtimestamp(today_ts).date()
        # This will retry the request a few times before giving up, making a kind of flexible processing time
        if self.request.get('put-in-queue', None) == "1":
            taskqueue.add(queue_name='initial-cron-updates', url='/tasks/cron/aggregate', params={'timestamp': str(today_ts), 'rangekey': 'day'})
            return

        logging.info('Handling date %s', today.isoformat())

        rangekey = self.request.get('rangekey', 'day')
        if rangekey == 'week':
            self.process_range(today, 'week')
        elif rangekey == 'month':
            if self.process_range(today, 'month'):
                # If new entries were discovered, schedule yearly updates
                taskqueue.add(queue_name='process-cron-updates', url='/tasks/cron/aggregate', params={'timestamp': str(today_ts), 'rangekey': 'year'}, eta=datetime.datetime.utcnow() + datetime.timedelta(minutes=10))
        elif rangekey == 'year':
            self.process_range(today, 'year')
        else:
            while True:
                if self.process_days(today) > 0:
                    # If new entries were discovered, schedule weekly and mothly updates
                    taskqueue.add(queue_name='process-cron-updates', url='/tasks/cron/aggregate', params={'timestamp': str(today_ts), 'rangekey': 'week'}, eta=datetime.datetime.utcnow() + datetime.timedelta(minutes=10))
                    taskqueue.add(queue_name='process-cron-updates', url='/tasks/cron/aggregate', params={'timestamp': str(today_ts), 'rangekey': 'month'}, eta=datetime.datetime.utcnow() + datetime.timedelta(minutes=15))

                next_entry = dbmodel.ReportItem.all().filter('counted =', None).filter('eventtype =', 'Information').order('timestamp').get()
                
                if next_entry == None or next_entry.timestamp == today_ts:
                    logging.info('No more stuff to do, quitting')
                    break

                today_ts = next_entry.timestamp
                today = datetime.datetime.utcfromtimestamp(next_entry.timestamp).date()
                logging.info('Rerun, handling date %s', today.isoformat())



    def update_day_record(self, rangekey, timestamp, item):

        @db.transactional(xg=True)
        def increment_record(rangekey, ostype, name, value, recordkey):
            key = '%s@%s:%s:%s' % (rangekey, ostype, name, value)

            #logging.info('Key is %s, recordkey is %s', key, recordkey)

            record = db.get(recordkey)

            entry = dbmodel.AggregateItem.get_by_key_name(key)
            if entry == None:
                entry = dbmodel.AggregateItem(key_name=key, rangetype='day', rangekey=rangekey, timestamp=timestamp, ostype=ostype, name=name, value=value, value_sum=0, entry_count=0, counted=0, counted_week=0)
            entry.value_sum += record.count
            entry.entry_count += 1
            entry.lastupdated = calendar.timegm(datetime.datetime.utcnow().timetuple())

            record.counted = 1
            entry.put()
            record.put()

        osname = item.reportset.ostype
        if osname not in ['Windows', 'Linux', 'OSX']:
            osname = 'Other'

        name = item.name.replace(':', '_')
        value = None

        if name[:4] == 'USE_':
            value = item.data

        if value != None:
            value = value.replace(':', '_')

        increment_record(rangekey, osname, name, value, item.key())


    def process_range(self, today, span):

        logging.info('Processing %s %s', span, today.isoformat())

        startdate = None
        enddate = None
        base_key = None

        if span == 'week':
            iso_year, iso_week, iso_day = today.isocalendar()
            startdate = today + datetime.timedelta(days=iso_day * -1)
            enddate = startdate + datetime.timedelta(days=7)
            base_key = '%s-w%s' % (iso_year, iso_week)
        elif span == 'month':
            startdate = datetime.date(today.year, today.month, 1)
            endmonth = today.month + 1
            endyear = today.year
            if endmonth == 13:
                endmonth = 1
                endyear += 1

            enddate = datetime.date(endyear, endmonth, 1)
            base_key = '%s-m%s' % (startdate.year, startdate.month)

        elif span == 'year':
            startdate = datetime.date(today.year, 1, 1)
            enddate = datetime.date(today.year + 1, 1, 1)
            base_key = str(startdate.year)

        if startdate == None or enddate == None or base_key == None: 
            raise Exception('Bad interval')

        starttimestamp = calendar.timegm((startdate.year, startdate.month, startdate.day, 0, 0, 0))
        endtimestamp = calendar.timegm((enddate.year, enddate.month, enddate.day, 0, 0, 0))

        count_column = 'counted'
        if span == 'week':
            count_column = 'counted_week'

        entry = None
        prev_key = None
        prev_count = 0

        lookup = {}

        count = 0
        for item in dbmodel.AggregateItem.all().filter('rangetype =', 'day').filter('timestamp >=', starttimestamp).filter('timestamp <', endtimestamp).order('timestamp'):

            key = '%s@%s:%s:%s' % (base_key, item.ostype, item.name, item.value)

            if not lookup.has_key(key):
                entry = dbmodel.AggregateItem.get_by_key_name(key)
                if entry == None:
                    entry = dbmodel.AggregateItem(key_name=key, rangetype=span, rangekey=base_key, timestamp=starttimestamp, ostype=item.ostype, name=item.name, value=item.value, value_sum=0, entry_count=0)

                prev_count += entry.entry_count

                entry.value_sum = 0
                entry.entry_count = 0
                lookup[key] = entry

            entry.value_sum += item.value_sum
            entry.entry_count += item.entry_count
            entry.lastupdated = calendar.timegm(datetime.datetime.utcnow().timetuple())
            count += 1

        for k in lookup:
            lookup[k].put()

        if count != prev_count:
            memcache.incr('aggregate-' + span, initial_value=0)

        logging.info('Processed %s day entries for %s %s', count, span, today.isoformat())
        return count != prev_count


    def process_days(self, today):
        logging.info('Processing day %s', today.isoformat())

        starttimestamp = calendar.timegm((today.year, today.month, today.day, 0, 0, 0))
        endtimestamp = starttimestamp + 24*60*60

        base_key = today.isoformat()
        
        count = 0
        for item in dbmodel.ReportItem.all().filter('counted =', None).filter('eventtype =', 'Information').filter('timestamp <', endtimestamp).filter('timestamp >=', starttimestamp).order('timestamp'):
            self.update_day_record(base_key, starttimestamp, item)
            count += 1

        if count > 0:
            memcache.incr('aggregate-day', initial_value=0)
        logging.info('Processed %s day items for %s', count, today.isoformat())
        return count

app = webapp2.WSGIApplication([
    ('/tasks/cron/aggregate', AggregateHandler)
], debug=TESTING)
