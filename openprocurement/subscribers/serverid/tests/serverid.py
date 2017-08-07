# -*- coding: utf-8 -*-
import uuid
import unittest
import webtest
from os import environ
from openprocurement.subscribers.serverid.serverid import (
    get_time,
    encrypt,
    decrypt,
    includeme
)
from datetime import datetime
from pytz import timezone
from pyramid.config import Configurator
from pyramid.httpexceptions import HTTPNotFound, HTTPInternalServerError

TZ = timezone(environ['TZ'] if 'TZ' in environ else 'Europe/Kiev')


def hello_world(request):
    resp = request.response
    resp.content_type = 'application/json'
    return resp


def status_404(request):
    resp = request.response
    resp.status = 404
    resp.content_type = 'application/json'
    return resp


def status_500(request):
    resp = request.response
    resp.status = 500
    resp.content_type = 'application/json'
    return resp


def error_404(request):
    resp = HTTPNotFound(content_type='application/json')
    resp.empty_body = True
    raise resp


def error_500(request):
    resp = HTTPInternalServerError(content_type='application/json')
    resp.empty_body = True
    raise resp


class SubscriberTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        config = Configurator()
        config.add_route('hello', '/')
        config.add_view(hello_world, route_name='hello')
        config.add_route('status_404', '/404')
        config.add_view(status_404, route_name='status_404')
        config.add_route('status_500', '/500')
        config.add_view(status_500, route_name='status_500')
        config.add_route('error_404', '/error404')
        config.add_view(error_404, route_name='error_404')
        config.add_route('error_500', '/error500')
        config.add_view(error_500, route_name='error_500')
        config.registry.server_id = uuid.uuid4().hex
        includeme(config)
        app = config.make_wsgi_app()
        cls.app = webtest.TestApp(app)

    def tearDown(self):
        self.app.reset()

    def test_get_time(self):
        time = get_time()
        local_time = datetime.now(TZ).isoformat()
        self.assertEqual(time.split('+')[1], local_time.split('+')[1])

    def test_encrypt(self):
        sid = uuid.uuid4().hex
        value, time = encrypt(sid)
        self.assertEqual(len(value), 128)

    def test_decrypt(self):
        sid = uuid.uuid4().hex
        value, time = encrypt(sid)

        decrypted = decrypt(sid, value)
        self.assertEqual(decrypted.startswith(sid), True)

        value = ''
        for x in xrange(0, 32):
            value += 'hello'
        decrypted = decrypt(sid, value)
        self.assertNotEqual(decrypted.startswith(sid), True)

    def test_includeme(self):
        config = Configurator()
        config.registry.server_id = ''
        self.assertEqual(config.registry.server_id, '')
        includeme(config)
        self.assertNotEqual(config.registry.couchdb_server_id, '')
        self.assertEqual(len(config.registry.couchdb_server_id), 32)

    def _test_couch_uuid_validator(self, path, status_code, status):
        # Request without cookie SERVER_ID
        self.assertEqual(self.app.cookies, {})
        resp = self.app.get(path, status=status_code)
        self.assertEqual(resp.status, status)
        self.assertEqual(resp.body, '')
        header = resp.headers.get('Set-Cookie', None).split(';')[0].split('=')
        header_name = header[0]
        header_value = header[1]
        self.assertEqual(header_name, 'SERVER_ID')
        self.assertEqual(len(header_value), 128)

        # Request POST without cookie SERVER_ID
        self.app.reset()
        self.assertEqual(self.app.cookies, {})
        resp = self.app.post_json(path, {'data': 'test data'}, status=412)
        self.assertEqual(resp.status, '412 Precondition Failed')
        header = resp.headers.get('Set-Cookie', None).split(';')[0].split('=')
        header_name = header[0]
        header_value = header[1]
        self.assertEqual(header_name, 'SERVER_ID')
        self.assertEqual(len(header_value), 128)

        # Request with valid cookie SERVER_ID
        cookie = self.app.cookies.get('SERVER_ID', None)
        self.assertNotEqual(cookie, None)
        resp = self.app.get(path, status=status_code)
        self.assertEqual(resp.status, status)
        self.assertEqual(resp.body, '')
        header = resp.headers.get('Set-Cookie', None)
        self.assertEqual(header, None)

        # Request with invalid cookie SERVER_ID
        cookie_value = 'f2154s5adf2as1f54asdf1as56f46asf3das4f654as31f456'
        self.app.set_cookie('SERVER_ID', cookie_value)
        resp = self.app.get(path, status=412)
        self.assertEqual(resp.status, '412 Precondition Failed')
        self.assertEqual(resp.request.cookies.get('SERVER_ID', None), cookie_value)
        header = resp.headers.get('Set-Cookie', None).split(';')[0].split('=')
        header_name = header[0]
        header_value = header[1]
        self.assertEqual(header_name, 'SERVER_ID')
        self.assertEqual(len(header_value), 128)

    def test_couch_uuid_validator(self):
        self._test_couch_uuid_validator('/', 200, '200 OK')

    def test_couch_uuid_validator_404(self):
        self._test_couch_uuid_validator('/404', 404, '404 Not Found')

    def test_couch_uuid_validator_500(self):
        self._test_couch_uuid_validator('/500', 500, '500 Internal Server Error')

    def test_couch_uuid_validator_error404(self):
        self._test_couch_uuid_validator('/error404', 404, '404 Not Found')

    def test_couch_uuid_validator_error500(self):
        self._test_couch_uuid_validator('/error500', 500, '500 Internal Server Error')


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SubscriberTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
