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

TZ = timezone(environ['TZ'] if 'TZ' in environ else 'Europe/Kiev')


def hello_world(request):
    resp = request.response
    resp.content_type = 'application/json'
    return resp


class SubscriberTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        config = Configurator()
        config.add_route('hello', '/')
        config.add_view(hello_world, route_name='hello')
        config.registry.server_id = uuid.uuid4().hex
        includeme(config)
        app = config.make_wsgi_app()
        cls.app = webtest.TestApp(app)

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
        self.assertNotEqual(config.registry.server_id, '')
        self.assertEqual(len(config.registry.server_id), 32)

    def test_couch_uuid_validator(self):
        # Request without cookie SERVER_ID
        self.assertEqual(self.app.cookies, {})
        resp = self.app.get('/')
        self.assertEqual(resp.status, '200 OK')
        self.assertEqual(resp.body, '')
        header = resp.headers.get('Set-Cookie', None).split(';')[0].split('=')
        header_name = header[0]
        header_value = header[1]
        self.assertEqual(header_name, 'SERVER_ID')
        self.assertEqual(len(header_value), 128)

        # Request POST without cookie SERVER_ID
        self.app.reset()
        self.assertEqual(self.app.cookies, {})
        resp = self.app.post_json('/', {'data': 'test data'}, status=412)
        self.assertEqual(resp.status, '412 Precondition Failed')
        header = resp.headers.get('Set-Cookie', None).split(';')[0].split('=')
        header_name = header[0]
        header_value = header[1]
        self.assertEqual(header_name, 'SERVER_ID')
        self.assertEqual(len(header_value), 128)

        # Request with valid cookie SERVER_ID
        cookie = self.app.cookies.get('SERVER_ID', None)
        self.assertNotEqual(cookie, None)
        resp = self.app.get('/')
        self.assertEqual(resp.status, '200 OK')
        self.assertEqual(resp.body, '')
        header = resp.headers.get('Set-Cookie', None)
        self.assertEqual(header, None)

        # Request with invalid cookie SERVER_ID
        cookie_value = 'f2154s5adf2as1f54asdf1as56f46asf3das4f654as31f456'
        self.app.set_cookie('SERVER_ID', cookie_value)
        resp = self.app.get('/', status=412)
        self.assertEqual(resp.status, '412 Precondition Failed')
        self.assertEqual(resp.request.cookies.get('SERVER_ID', None), cookie_value)
        header = resp.headers.get('Set-Cookie', None).split(';')[0].split('=')
        header_name = header[0]
        header_value = header[1]
        self.assertEqual(header_name, 'SERVER_ID')
        self.assertEqual(len(header_value), 128)


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SubscriberTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
