# -*- coding: utf-8 -*-
#
# Handlers dealing with tip interface for whistleblowers (wbtip)
import base64
import json
import os
from twisted.internet.threads import deferToThread
from twisted.internet.defer import inlineCallbacks, returnValue

from globaleaks import models
from globaleaks.models.config import ConfigFactory
from globaleaks.handlers.admin.node import db_admin_serialize_node
from globaleaks.handlers.admin.notification import db_get_notification
from globaleaks.handlers.base import BaseHandler
from globaleaks.handlers.rtip import serialize_comment, serialize_message, db_get_itip_comment_list
from globaleaks.handlers.submission import serialize_usertip, \
    decrypt_tip, db_set_internaltip_answers, db_get_questionnaire, \
    db_archive_questionnaire_schema, db_set_internaltip_data
from globaleaks.handlers.rtip import serialize_rtip
from globaleaks.handlers.user import user_serialize_user
from globaleaks.models import serializers
from globaleaks.orm import db_get, transact
from globaleaks.rest import requests
from globaleaks.utils.crypto import GCE
from globaleaks.utils.fs import directory_traversal_check
from globaleaks.utils.log import log
from globaleaks.utils.templating import Templating
from globaleaks.utils.utility import datetime_now


def db_notify_recipients_of_tip_update(session, itip_id):
    for user, rtip, itip in session.query(models.User, models.ReceiverTip, models.InternalTip) \
                                   .filter(models.User.id == models.ReceiverTip.receiver_id,
                                           models.ReceiverTip.internaltip_id == models.InternalTip.id,
                                           models.InternalTip.id == itip_id):
        data = {
          'type': 'tip_update'
        }

        data['user'] = user_serialize_user(session, user, user.language)
        data['tip'] = serialize_rtip(session, rtip, itip, user.language)

        data['node'] = db_admin_serialize_node(session, user.tid, user.language)

        if data['node']['mode'] == 'default':
            data['notification'] = db_get_notification(session, user.tid, user.language)
        else:
            data['notification'] = db_get_notification(session, 1, user.language)

        subject, body = Templating().get_mail_subject_and_body(data)

        session.add(models.Mail({
            'address': data['user']['mail_address'],
            'subject': subject,
            'body': body,
            'tid': user.tid
        }))



def db_get_itip_receiver_list(session, itip):
    ret = []

    for user, rtip in session.query(models.User, models.ReceiverTip) \
                             .filter(models.User.id == models.ReceiverTip.receiver_id,
                                     models.ReceiverTip.internaltip_id == itip.id):
        ret.append({
            "id": user.id,
            "name": user.public_name,
            "last_access": rtip.last_access,
            "access_counter": rtip.access_counter
        })

    return ret


def db_get_rfile_list(session, itip_id):
    ifiles = session.query(models.InternalFile) \
                    .filter(models.InternalFile.internaltip_id == itip_id,
                            models.InternalTip.id == itip_id)

    return [serializers.serialize_ifile(session, ifile) for ifile in ifiles]


def db_get_wbfile_list(session, itip_id):
    wbfiles = session.query(models.WhistleblowerFile) \
                     .filter(models.WhistleblowerFile.receivertip_id == models.ReceiverTip.id,
                             models.ReceiverTip.internaltip_id == itip_id)

    return [serializers.serialize_wbfile(session, wbfile) for wbfile in wbfiles]


def db_get_wbtip(session, itip_id, language):
    wbtip, itip = db_get(session,
                         (models.WhistleblowerTip, models.InternalTip),
                         (models.WhistleblowerTip.id == models.InternalTip.id,
                          models.InternalTip.id == itip_id))

    itip.wb_access_counter += 1
    itip.wb_last_access = datetime_now()

    return serialize_wbtip(session, wbtip, itip, language), base64.b64decode(wbtip.crypto_tip_prv_key)


@transact
def get_wbtip(session, itip_id, language):
    return db_get_wbtip(session, itip_id, language)


def serialize_wbtip(session, wbtip, itip, language):
    ret = serialize_usertip(session, itip, itip, language)

    ret['receivers'] = db_get_itip_receiver_list(session, itip)
    ret['comments'] = db_get_itip_comment_list(session, itip.id)
    ret['messages'] = db_get_itip_message_list(session, itip.id)
    ret['rfiles'] = db_get_rfile_list(session, itip.id)
    ret['wbfiles'] = db_get_wbfile_list(session, itip.id)

    return ret


@transact
def create_comment(session, tid, wbtip_id, content):
    wbtip, itip = db_get(session,
                         (models.WhistleblowerTip, models.InternalTip),
                         (models.WhistleblowerTip.id == wbtip_id,
                          models.InternalTip.id == models.WhistleblowerTip.id,
                          models.InternalTip.enable_two_way_comments.is_(True),
                          models.InternalTip.status != 'closed',
                          models.InternalTip.tid == tid))

    itip.update_date = itip.wb_last_access = datetime_now()

    _content = content
    if itip.crypto_tip_pub_key:
        _content = base64.b64encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, content)).decode()

    comment = models.Comment()
    comment.internaltip_id = wbtip_id
    comment.type = 'whistleblower'
    comment.content = _content
    session.add(comment)
    session.flush()

    ret = serialize_comment(session, comment)
    ret['content'] = content

    return ret


def db_get_itip_message_list(session, wbtip_id):
    messages = session.query(models.Message) \
                      .filter(models.Message.receivertip_id == models.ReceiverTip.id,
                              models.ReceiverTip.internaltip_id == models.InternalTip.id,
                              models.InternalTip.id == wbtip_id)

    return [serialize_message(session, message) for message in messages]


@transact
def create_message(session, tid, wbtip_id, receiver_id, content):
    wbtip, itip, rtip_id = db_get(session,
                                  (models.WhistleblowerTip, models.InternalTip, models.ReceiverTip.id),
                                  (models.WhistleblowerTip.id == wbtip_id,
                                   models.ReceiverTip.internaltip_id == wbtip_id,
                                   models.ReceiverTip.receiver_id == receiver_id,
                                   models.InternalTip.id == models.WhistleblowerTip.id,
                                   models.InternalTip.enable_two_way_messages.is_(True),
                                   models.InternalTip.status != 'closed',
                                   models.InternalTip.tid == tid))

    itip.update_date = itip.wb_last_access = datetime_now()

    _content = content
    if itip.crypto_tip_pub_key:
        _content = base64.b64encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, content)).decode()

    msg = models.Message()
    msg.receivertip_id = rtip_id
    msg.type = 'whistleblower'
    msg.content = _content
    session.add(msg)
    session.flush()

    ret = serialize_message(session, msg)
    ret['content'] = content

    return ret


@transact
def update_identity_information(session, tid, tip_id, identity_field_id, wbi, language):
    itip = db_get(session,
                  models.InternalTip,
                  (models.InternalTip.id == tip_id,
                   models.InternalTip.status != 'closed',
                   models.InternalTip.tid == tid))

    if itip.crypto_tip_pub_key:
        wbi = base64.b64encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, json.dumps(wbi).encode())).decode()

    db_set_internaltip_data(session, itip.id, 'whistleblower_identity', wbi)

    now = datetime_now()
    itip.update_date = now
    itip.wb_last_access = now

    db_notify_recipients_of_tip_update(session, itip.id)


@transact
def store_additional_questionnaire_answers(session, tid, tip_id, answers, language):
    itip, context = session.query(models.InternalTip, models.Context) \
                           .filter(models.InternalTip.id == tip_id,
                                   models.InternalTip.status != 'closed',
                                   models.InternalTip.tid == tid,
                                   models.Context.id == models.InternalTip.context_id).one()

    if not context.additional_questionnaire_id:
        return

    steps = db_get_questionnaire(session, tid, context.additional_questionnaire_id, None)['steps']
    questionnaire_hash = db_archive_questionnaire_schema(session, steps)

    if itip.crypto_tip_pub_key:
        answers = base64.b64encode(GCE.asymmetric_encrypt(itip.crypto_tip_pub_key, json.dumps(answers).encode())).decode()

    db_set_internaltip_answers(session, itip.id, questionnaire_hash, answers)

    db_notify_recipients_of_tip_update(session, itip.id)


class WBTipInstance(BaseHandler):
    """
    This interface expose the Whistleblower Tip.
    """
    check_roles = 'whistleblower'

    @inlineCallbacks
    def get(self):
        tip, crypto_tip_prv_key = yield get_wbtip(self.session.user_id, self.request.language)

        if crypto_tip_prv_key:
            tip = yield deferToThread(decrypt_tip, self.session.cc, crypto_tip_prv_key, tip)

        returnValue(tip)


class WBTipCommentCollection(BaseHandler):
    """
    This interface expose the Whistleblower Tip Comments
    """
    check_roles = 'whistleblower'

    def post(self):
        request = self.validate_message(self.request.content.read(), requests.CommentDesc)
        return create_comment(self.request.tid, self.session.user_id, request['content'])


class WBTipMessageCollection(BaseHandler):
    """
    This interface expose the Whistleblower Tip Messages
    """
    check_roles = 'whistleblower'

    def post(self, receiver_id):
        request = self.validate_message(self.request.content.read(), requests.CommentDesc)
        return create_message(self.request.tid, self.session.user_id, receiver_id, request['content'])


class WBTipWBFileHandler(BaseHandler):
    check_roles = 'whistleblower'
    handler_exec_time_threshold = 3600

    @transact
    def download_wbfile(self, session, tid, file_id):
        wbfile, wbtip = db_get(session,
                               (models.WhistleblowerFile, models.WhistleblowerTip),
                               (models.WhistleblowerFile.id == file_id,
                                models.WhistleblowerFile.receivertip_id == models.ReceiverTip.id,
                                models.ReceiverTip.internaltip_id == models.WhistleblowerTip.id,
                                models.WhistleblowerTip.id == self.session.user_id))

        if not wbtip:
            raise errors.ResourceNotFound()

        wbfile.downloads += 1

        log.debug("Download of file %s by whistleblower %s",
                  wbfile.id, self.session.user_id)

        return serializers.serialize_wbfile(session, wbfile), base64.b64decode(wbtip.crypto_tip_prv_key), ''

    @inlineCallbacks
    def get(self, wbfile_id):
        wbfile, tip_prv_key, pgp_key = yield self.download_wbfile(self.request.tid, wbfile_id)

        filelocation = os.path.join(self.state.settings.attachments_path, wbfile['filename'])

        directory_traversal_check(self.state.settings.attachments_path, filelocation)

        if tip_prv_key:
            tip_prv_key = GCE.asymmetric_decrypt(self.session.cc, tip_prv_key)
            wbfile['name'] = GCE.asymmetric_decrypt(tip_prv_key, base64.b64decode(wbfile['name'].encode())).decode()
            filelocation = GCE.streaming_encryption_open('DECRYPT', tip_prv_key, filelocation)

        yield self.write_file_as_download(wbfile['name'], filelocation, pgp_key)


class WBTipIdentityHandler(BaseHandler):
    """
    This is the interface that securely allows the whistleblower to provide his identity
    """
    check_roles = 'whistleblower'

    def post(self, tip_id):
        request = self.validate_message(self.request.content.read(), requests.WhisleblowerIdentityAnswers)

        return update_identity_information(self.request.tid,
                                           tip_id,
                                           request['identity_field_id'],
                                           request['identity_field_answers'],
                                           self.request.language)


class WBTipAdditionalQuestionnaire(BaseHandler):
    """
    This is the interface that securely allows the whistleblower to fill the additional questionnaire
    """
    check_roles = 'whistleblower'

    def post(self, tip_id):
        request = self.validate_message(self.request.content.read(), requests.AdditionalQuestionnaireAnswers)

        return store_additional_questionnaire_answers(self.request.tid,
                                                      tip_id,
                                                      request['answers'],
                                                      self.request.language)
