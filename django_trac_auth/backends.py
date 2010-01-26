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


class HtPasswdBackend(object):

    def _get_user_info(self, username, password=None):
        if getattr(settings, 'TRAC_EMAIL_USERNAME', False):
            email = username
        return (email, '', '')

    def _get_member_of(self, username, seen=None):
        if seen is None:
            seen = set()
        htgroup = getattr(settings, 'TRAC_HTGROUP', None)
        if htgroup:
            groups = [map(str.strip, x.strip().split(':', 1)) for x in file(htgroup)]
            groups = dict([[x, y.split()] for x, y in groups])
            seen.update([group for group, users in groups.iteritems() if username in users])
        return seen

    def authenticate(self, username, password):
        import crypt
        htpasswd = getattr(settings, 'TRAC_HTPASSWD', None)
        if not password:
            logging.warning('settings.TRAC_HTPASSWD not found')
            return None
        users = dict([x.strip().split(':', 1) for x in file(htpasswd)])
        if username not in users:
            return None
        # check required group
        required_groups = getattr(settings, 'TRAC_REQUIRED_GROUPS', None)
        if required_groups:
            seen = self._get_member_of(username)
            if not seen.intersection(required_groups):
                logging.warning("User %s does not belong to the required groups %s" %
                                (username, required_groups))
                return None
        # check password
        hashed_passwd = users.get(username)
        if hashed_passwd == crypt.crypt(password, hashed_passwd[:2]):
            return self.get_or_create_user(username, password)

    def get_or_create_user(self, username, password=None):
        store_password = getattr(settings, 'TRAC_STORE_PASSWORD', False)
        try:
            user = User.objects.get(username=username)
            # TODO: check user info change
            if store_password:
                # check password change
                if not user.check_password(password):
                    user.set_password(password)
        except User.DoesNotExist:
            email, first_name, last_name = self._get_user_info(username, password)
            try:
                user = User(username=username,
                            password='',
                            first_name=first_name,
                            last_name=last_name,
                            email=email)
                user.is_staff = False
                user.is_superuser = False
                if store_password and password != None:
                    user.set_password(password)
                else:
                    user.set_unusable_password()
                user.save()
            except Exception, e:
                logging.warning("Unexpected exception occurred: " + str(e))
        return user

    def get_user(self, user_id):
        return get_object_or_none(User, pk=user_id)


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


class TracHtPasswdBackend(HtPasswdBackend):

    def _get_user_info(self, username, password=None):
        try:
            data = get_trac_user(settings.TRAC_ENV, username)
        except:
            data = {}
        email = data.get('email', '')
        name = data.get('name', '').split(None, 1)
        first_name = (len(name) >= 1) and name[0] or ''
        last_name = (len(name) == 2) and name[1] or ''
        if email == '' and getattr(settings, 'TRAC_EMAIL_USERNAME', False):
            email = username
        return (email, first_name, last_name)

