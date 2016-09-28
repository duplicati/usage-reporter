import os

import webapp2
from google.appengine.ext import db

TESTING = os.environ.get('SERVER_SOFTWARE', '').startswith('Development')

from config import API_KEY


class LetsEncryptEntry(db.Model):
    value = db.TextProperty(required=False)
    created = db.DateTimeProperty(required=False, auto_now_add=True)


class LetsEncryptHandler(webapp2.RequestHandler):
    def get(self, key):
        entry = LetsEncryptEntry.get_by_key_name(key)
        if entry == None:
            self.response.set_status(404, 'Not found')
            self.response.write('Not found')
            return

        self.response.write(entry.value)

    def post(self, key):
        if not self.request.headers.has_key('api-key') or self.request.headers['api-key'] != API_KEY:
            # logging.info('Key was "%s", should be "%s"', self.request.headers['api-key'], API_KEY)
            self.response.set_status(403, 'Permission denied')
            self.response.write('Permission denied')
            return

        LetsEncryptEntry(key_name=key, value=self.request.body).put()


app = webapp2.WSGIApplication([
    ('/.well-known/acme-challenge/([\w-]+)', LetsEncryptHandler)
], debug=TESTING)
