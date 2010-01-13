# Copyright (c) 2010, Takashi Ito
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. Neither the name of the authors nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import logging

from django.conf import settings
from django.contrib.auth.models import User
from djblets.util.misc import get_object_or_none


def get_trac_user(path, username):
    from trac.env import Environment
    env = Environment(path)
    db = env.get_db_cnx()
    cursor = db.cursor()
    cursor.execute("SELECT name, value"
                   " FROM session_attribute"
                   " WHERE sid='%s'"
                   " AND (name='email' OR name='name')" % username)
    return dict((name, value) for name, value in cursor)


class TracHtPasswdBackend(object):

    htpasswd = settings.TRAC_HTPASSWD
    htgroup = settings.TRAC_HTGROUP
    trac_env = settings.TRAC_ENV
    store_password = settings.TRAC_STORE_PASSWORD

    def _get_trac_user(self, username):
        try:
            data = get_trac_user(self.trac_env, username)
        except Exception, e:
            data = {}
        email = data.get('email', '')
        name = data.get('name', '').split(None, 1)
        first_name = (len(name) >= 1) and name[0] or ''
        last_name = (len(name) == 2) and name[1] or ''
        return (email, first_name, last_name)

    def _get_member_of(self, username):
        groups = [map(str.split, x.split(':', 1)) for x in file(self.htgroup)]
        groups = dict([[x, y.split()] for x, y in groups])
        return [group for group, users in groups.iteritems() if username in users]

    def authenticate(self, username, password):
        import crypt
        users = dict([x.strip().split(':', 1) for x in file(self.htpasswd)])
        if username in users:
            # TODO: check group
            hashed_passwd = users.get(username)
            if hashed_passwd == crypt.crypt(password, hashed_passwd[:2]):
                return self.get_or_create_user(username, password)

    def get_or_create_user(self, username, password=None):
        try:
            user = User.objects.get(username=username)
            if self.store_password:
                # check password change
                if not user.check_password(password):
                    user.set_password(password)
        except User.DoesNotExist:
            email, first_name, last_name = self._get_trac_user(username)
            try:
                user = User(username=username,
                            password='',
                            first_name=first_name,
                            last_name=last_name,
                            email=email)
                user.is_staff = False
                user.is_superuser = False
                if self.store_password and password != None:
                    user.set_password(password)
                else:
                    user.set_unusable_password()
                user.save()
            except:
                pass
        return user

    def get_user(self, user_id):
        return get_object_or_none(User, pk=user_id)

