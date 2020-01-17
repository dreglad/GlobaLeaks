# -*- coding: utf-8
from twisted.internet.defer import inlineCallbacks, returnValue

from globaleaks import models
from globaleaks.handlers.base import BaseHandler
from globaleaks.orm import transact
from globaleaks.rest import requests
from globaleaks.state import State


def serialize_redirect(redirect):
    return {
        'id': redirect.id,
        'path1': redirect.path1,
        'path2': redirect.path2
    }


@transact
def get_redirect_list(session, tid):
    return [serialize_redirect(redirect) for redirect in session.query(models.Redirect).filter(models.Redirect.tid == tid)]


@inlineCallbacks
def update_redirects_state(tid):
    State.tenant_cache[tid]['redirects'] = {}

    redirects = yield get_redirect_list(tid)

    for redirect in redirects:
        State.tenant_cache[tid]['redirects'][redirect['path1']] = redirect['path2']


@transact
def create(session, tid, request):
    request['tid'] = tid
    redirect = models.db_forge_obj(session, models.Redirect, request)
    return serialize_redirect(redirect)


class RedirectCollection(BaseHandler):
    check_roles = 'admin'
    cache_resource = True
    invalidate_cache = True

    def get(self):
        """
        Return the list of registered redirects
        """
        return get_redirect_list(self.request.tid)

    @inlineCallbacks
    def post(self):
        """
        Create a new redirect
        """
        request = self.validate_message(self.request.content.read(), requests.AdminRedirectDesc)

        redirect = yield create(self.request.tid, request)

        yield update_redirects_state(self.request.tid)

        returnValue(redirect)


class RedirectInstance(BaseHandler):
    check_roles = 'admin'
    invalidate_cache = True

    @inlineCallbacks
    def delete(self, redirect_id):
        """
        Delete the specified redirect.
        """
        yield models.delete(models.Redirect, models.Redirect.tid == self.request.tid, models.Redirect.id == redirect_id)

        yield update_redirects_state(self.request.tid)
