# -*- coding: utf-8 -*-

import json
import random
import re
import requests
import time
import xml.dom.minidom

class ClientException(Exception):
    pass

class Client(object):
    """
    Call APIs for WeChat Group
        login
        send_message_to_group
        send_message_to_groups
        send_messages_to_group
        send_messages_to_groups
        receive_message_from_group
        receive_messages_from_group
        receive_messages_from_groups
    """
    def __init__(self):
        self.session = requests.Session()
        self.host = 'https://wx.qq.com'
        self.login_host = 'https://login.weixin.qq.com'
        self.webpush_host = 'https://webpush.weixin.qq.com'
        self.device_id = "e{0}".format(random.randint(100000000000000, 1000000000000000))
        self.uuid = None
        self.wxuin = None
        self.wxsid = None
        self.pass_ticket = None
        self.skey = None

    def get_uuid(self):
        uri = ''.join([self.login_host, '/jslogin'])
        params = {
            'appid': 'wx782c26e4c19acffb',
            'redirect_uri': 'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage',
            'fun': 'new',
            'lang': 'zh_CN',
            '_': int(time.time())
        }
        r = self.session.get(uri, params=params)
        if r.status_code == 200:
            return self.text_to_dict(r.text.encode('utf8'))['window.QRLogin.uuid']
        else:
            raise ClientException("Status code is {0}".format(r.status_code))

    def get_qrcode_uri(self):
        self.uuid = self.get_uuid()
        return "{0}/qrcode/{1}".format(self.login_host, self.uuid)

    def get_login_uri(self):
        uri = ''.join([self.login_host, '/cgi-bin/mmwebwx-bin/login'])
        r = self.session.get('{0}?loginicon=true&uuid={1}&tip=0&_={2}'.format(uri, self.uuid, int(time.time())))
        if r.status_code == 200:
            response = self.text_to_dict(r.text.encode('utf8'))
            window_code = response['window.code']
            if window_code == '200':
                return response['window.redirect_uri']
            else:
                return ""
        else:
            raise ClientException("Status code is {0}".format(r.status_code))

    def login(self, login_uri):
        r = self.session.get(login_uri)
        with open("login", "w") as f:
            f.write(r.text.encode('utf8'))
        cookies = self.session.cookies
        self.wxuin = cookies['wxuin']
        self.wxsid = cookies['wxsid']
        # returns pass_ticket and skey before redirecting
        xml_string = r.history[0].text.encode('utf8')
        doc = xml.dom.minidom.parseString(xml_string)
        node = doc.getElementsByTagName("pass_ticket")[0]
        self.pass_ticket = node.childNodes[0].nodeValue
        node = doc.getElementsByTagName("skey")[0]
        self.skey = node.childNodes[0].nodeValue

    def webwx_stat_report(self):
        uri = '{0}/cgi-bin/mmwebwx-bin/webwxstatreport'.format(self.host)
        params = {
            'fun': 'new'
        }


    def wx_init(self):
        uri = '{0}/cgi-bin/mmwebwx-bin/webwxinit'.format(self.host)
        params = {
            'pass_ticket': self.pass_ticket
        }
        data = {
            "BaseRequest": {
                "Uin": self.wxuin,
                "Sid": self.wxsid,
                "Skey": self.skey,
                "DeviceID": self.device_id
            }
        }
        r = self.session.post(uri, params=params, data=json.dumps(data))
        response_json = r.json()
        synckey = response_json['SyncKey']
        synckey_list = list()
        for item in synckey['List']:
            key = item['Key']
            value = item['Val']
            synckey_list.append('{0}_{1}'.format(key,value))
        self.synckey = '|'.join(synckey_list)

    def webwx_get_contact(self): 
        uri = '{0}/cgi-bin/mmwebwx-bin/webwxgetcontact'.format(self.host)
        params = {
            'pass_ticket': self.pass_ticket,
            'skey': self.skey,
            'r': int(time.time())
        }
        r = self.session.get(uri, params=params)
        response_json = r.json()
        with open('contact','w') as f:
            f.write(r.text.encode('utf8'))

    def sync_check(self):
        uri = '{0}/cgi-bin/mmwebwx-bin/synccheck'.format(self.webpush_host)
        params = {
            'skey': self.skey,
            'sid': self.wxsid,
            'uin': self.wxuin,
            'deviceid': self.device_id,
            'synckey': self.synckey,
            '_': int(time.time())
        }
        r = self.session.get(uri, params=params)
        response_json = r.json()
        with open('synccheck','w') as f:
            f.write(r.text.encode('utf8'))
        # TODO
        window.synccheck={retcode:"0",selector:"2"}

    def webwx_sync(self):
        uri = '{0}/cgi-bin/mmwebwx-bin/webwxsync'.format(self.host)
        params = {
            'sid': self.wxsid,
            'skey': self.skey,
            'pass_ticket': self.pass_ticket
        }
        # TODO
        r = self.session.get(uri, params=params)
        response_json = r.json()
        with open('webwxsync','w') as f:
            f.write(r.text.encode('utf8'))

    def send_message_to_group(self, msg, group):
        pass

    def text_to_dict(self, text):
        ret = dict()
        for line in text.split(';'):
            if line:
                [key, __, value] = line.partition('=')
                ret[key.strip().strip('"')] = value.strip().strip('"')
        return ret


if __name__ == "__main__":
    client = Client()
    print client.get_qrcode_uri()
    redirect_uri = ''
    while not redirect_uri:
        print "polling"
        redirect_uri = client.get_login_uri()
        time.sleep(5)
    print redirect_uri
    client.login(redirect_uri)
    client.wx_init()
    client.webwx_get_contact()
    client.sync_check()
    client.webwx_sync()
