import http.client
import importlib
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path

class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        os.environ['RASDAD_DB'] = str(Path(cls.temp.name) / 'test.sqlite3')
        os.environ['RASDAD_ADMIN_TOKEN'] = 'test-only-token'
        cls.module = importlib.import_module('server')
        cls.server = cls.module.ThreadingHTTPServer(('127.0.0.1', 0), cls.module.Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def request(self, path, data=None, cookie=None, token=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        headers = {'Content-Type': 'application/json'}
        if cookie: headers['Cookie'] = cookie
        if token: headers['Authorization'] = 'Bearer ' + token
        conn.request('POST' if data is not None else 'GET', path, json.dumps(data) if data is not None else None, headers)
        response = conn.getresponse()
        status, cookie, raw = response.status, response.getheader('Set-Cookie'), response.read()
        conn.close()
        return status, cookie, raw

    def test_flow_and_privacy(self):
        status, cookie, _ = self.request('/api/visit', {})
        self.assertEqual(status, 200)
        cookie = cookie.split(';')[0]
        self.request('/api/visit', {}, cookie)
        for consent in [False, True]:
            status, _, _ = self.request('/api/leads', {'kind':'inquiry','name': 'Public' if consent else 'Private','email':'private@example.com','message':'private detail','publicConsent':consent}, cookie)
            self.assertEqual(status, 200)
        self.assertEqual(self.request('/api/leads', {'kind':'request'})[0],400)
        self.assertEqual(self.request('/api/leads', {'kind':'request','name':'Client','phone':'0563962821','entity':'School','type':'Dashboard','description':'Details','publicConsent':False})[0],200)
        review = {'name':'Reviewer','rating':5}
        self.assertEqual(self.request('/api/reviews',review,cookie)[0],200)
        review['rating']=4
        self.assertEqual(self.request('/api/reviews',review,cookie)[0],200)
        review['rating']=7
        self.assertEqual(self.request('/api/reviews',review,cookie)[0],400)
        raw=self.request('/api/community')[2]
        public=json.loads(raw)
        self.assertEqual(public['visitors'],1)
        self.assertEqual(public['count'],1)
        self.assertEqual(public['average'],4)
        self.assertNotIn('clients', public)
        self.assertEqual(public['reviews'], [{'name': 'Reviewer', 'rating': 4}])
        self.assertNotIn(b'private@example.com',raw)
        self.assertNotIn(b'private detail',raw)
        self.assertNotIn(b'Private',raw)
        self.assertEqual(self.request('/api/admin')[0],401)
        self.assertEqual(len(json.loads(self.request('/api/admin',token='test-only-token')[2])['leads']),3)
        for path in ['/server.py','/data/rasdad.sqlite3','/media/../server.py','/.env']:
            self.assertEqual(self.request(path)[0],404)
        for path in ['/','/services.html','/packages.html','/admin.html','/media/community.js']:
            self.assertEqual(self.request(path)[0],200)
        status, fresh_cookie, _ = self.request('/api/reviews', {'name':'New visitor','rating':5})
        self.assertEqual(status,200)
        self.assertIn('rasdad_visitor=',fresh_cookie)
        self.assertEqual(json.loads(self.request('/api/community')[2])['count'],2)

if __name__ == '__main__': unittest.main()
