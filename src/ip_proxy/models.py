# coding:utf-8
import datetime
from mongoengine import Document
from mongoengine import IntField, StringField, DateTimeField, FloatField, ListField


class IpProxies(Document):
    TYPE_CHOICES = (u'高匿', u'匿名')
    PRO_CHOICES = ('http', 'https')

    ip = StringField(required=True, unique=True)
    port = IntField(required=True)
    ip_type = StringField(choices=TYPE_CHOICES, default=u'匿名')
    protocol = StringField(choices=PRO_CHOICES, default='http')
    speeds = ListField(FloatField())
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
