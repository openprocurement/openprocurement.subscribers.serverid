# -*- coding: utf-8 -*-
import uuid
from Cookie import SimpleCookie
from os import environ
from binascii import hexlify, unhexlify
from Crypto.Cipher import AES
from pyramid.events import NewRequest
from webob.exc import HTTPPreconditionFailed
from logging import getLogger
from datetime import datetime
from pytz import timezone
from hashlib import md5

TZ = timezone(environ['TZ'] if 'TZ' in environ else 'Europe/Kiev')

logger = getLogger(__name__)


def get_time():
    return datetime.now(TZ).isoformat()


def encrypt(sid):
    time = get_time()
    text = "{}{:^{}}".format(sid, time, AES.block_size * 2)
    return hexlify(AES.new(sid).encrypt(text)), time


def decrypt(sid, key):
    try:
        text = AES.new(sid).decrypt(unhexlify(key))
        text.startswith(sid)
    except:
        text = ''
    return text


def server_id_validator(event):
    request = event.request
    server_id = event.request.registry.couchdb_server_id
    cookies = SimpleCookie(request.environ.get('HTTP_COOKIE'))
    cookie_server_id = cookies.get('SERVER_ID', None)
    if cookie_server_id:
        value = cookie_server_id.value
        decrypted = decrypt(server_id, value)
        if not decrypted or not decrypted.startswith(server_id):
            logger.info('Invalid cookie: {}'.format(value,
                        extra={'MESSAGE_ID': 'serverid_invalid'}))
            response_cookie = SimpleCookie()
            value, time = encrypt(server_id)
            response_cookie['SERVER_ID'] = value
            response_cookie['SERVER_ID']['path'] = '/'
            request.response = HTTPPreconditionFailed(
                headers={'Set-Cookie': response_cookie['SERVER_ID'].OutputString()}
            )
            request.response.empty_body = True
            logger.info('New cookie: {} ({})'.format(value, time),
                        extra={'MESSAGE_ID': 'serverid_new'})
            raise request.response
        else:
            time = decrypted[len(server_id):]
            logger.debug('Valid cookie: {} ({})'.format(value, time),
                         extra={'MESSAGE_ID': 'serverid_valid'})
    elif request.method in ['POST', 'PATCH', 'PUT', 'DELETE']:
        value, time = encrypt(server_id)
        response_cookie = SimpleCookie()
        response_cookie['SERVER_ID'] = value
        response_cookie['SERVER_ID']['path'] = '/'
        request.response = HTTPPreconditionFailed(
            headers={'Set-Cookie': response_cookie['SERVER_ID'].OutputString()}
        )
        request.response.empty_body = True
        logger.info('New cookie: {} ({})'.format(value, time),
                    extra={'MESSAGE_ID': 'serverid_new'})
        raise request.response
    if not cookie_server_id:
        value, time = encrypt(server_id)
        request.response.set_cookie(name='SERVER_ID', value=value)
        logger.info('New cookie: {} ({})'.format(value, time),
                    extra={'MESSAGE_ID': 'serverid_new'})
        return request.response


def includeme(config):
    logger.info('init server_id NewRequest subscriber')

    if config.registry.server_id == '':
        config.registry.couchdb_server_id = uuid.uuid4().hex
        logger.warning('\'server_id\' is empty. Used generated \'server_id\' {}'.format(
            config.registry.server_id
        ))
    else:
        config.registry.couchdb_server_id = md5(config.registry.server_id).hexdigest()
    config.add_subscriber(server_id_validator, NewRequest)

