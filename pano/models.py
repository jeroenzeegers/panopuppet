from __future__ import unicode_literals
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


# Create your models here.
@python_2_unicode_compatible
class LdapGroupPermissions(models.Model):
    ldap_group_name = models.CharField(max_length=200, primary_key=True, unique=True)
    puppetdb_query = models.TextField()

    def __str__(self):
        return self.ldap_group_name
