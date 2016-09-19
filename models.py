# coding:utf-8
import datetime
from mongoengine import Document
from mongoengine import IntField, StringField, DateTimeField, FloatField


class IpProxies(Document):
    (HIGH_ANONYMITY, ANONYMITY) = range(0, 2)
    (HTTP, HTTPS) = range(0, 2)
    is_ANONYMITY = (HIGH_ANONYMITY, ANONYMITY)
    types = (HTTP, HTTPS)

    ip = StringField(required=True, unique=True)
    port = IntField(required=True,)
    ip_type = IntField(choices=is_ANONYMITY, default=HIGH_ANONYMITY)
    protocol = IntField(choices=types, default=HTTP)
    speed = FloatField()
    creation_date = DateTimeField()
    update_date = DateTimeField()
    meta = {"db_alias": "material"}

    def save(self, *args, **kwargs):
        if not self.creation_date:
            self.creation_date = datetime.datetime.now()
        return super(IpProxies, self).save(*args, **kwargs)

    def get_proxies(self):
        proxy_address = '{ip}:{port}'.format(
            ip=self.ip,
            port=self.port
        )
        return {
            'http': 'http://%s' % proxy_address,
            'https': 'https://%s' % proxy_address,
        }
