# -*- coding: UTF-8
#   Requests
#   ********
#
# This file contain the specification of all the requests that can be made by a
# GLClient to a GLBackend.
# These specifications may be used with rest.validateMessage() inside of the
# handler to verify if the request is correct.

from globaleaks.rest.base import formFieldsDict, uuid_regexp

authDict = {
    'username' : unicode,
    'password' : unicode,
    'role' : unicode
}

wbSubmissionDesc = {
    'wb_fields' : dict,
    'context_gus' : uuid_regexp,
    'receivers' : [ uuid_regexp ],
    'files' : [ uuid_regexp ],
    'finalize' : bool
}

receiverReceiverDesc = {
    'name' : unicode,
    'password' : unicode,
    'old_password': unicode,
    # 'username' : unicode, XXX at creation time is the same of mail_address
    'mail_address' : unicode,
    'description' : unicode,
    'gpg_key_armor': unicode,
    'gpg_key_remove': bool,
    "gpg_enable_notification": bool,
    "gpg_enable_files": bool,
    "comment_notification": bool,
    "file_notification": bool,
    "tip_notification": bool,
    "message_notification": bool,
    # remind:
    # notification language, a default need to be provided
    # and need to be sets by receiver (atm: 'en')
}

actorsCommentDesc = {
    'content' : unicode,
}

actorsTipOpsDesc = {
    'global_delete' : bool,
    'is_pertinent': bool
}

adminNodeDesc = {
    'name': unicode,
    'description' : unicode,
    'presentation' : unicode,
    'footer': unicode,
    'hidden_service' : unicode,
    'public_site' : unicode,
    'stats_update_time' : int,
    'email' : unicode,
    'password' : unicode,
    'old_password' : unicode,
    'languages_enabled': [ unicode ],
    'languages_supported': list, # ignored
    'maximum_namesize': int,
    'maximum_textsize': int,
    'maximum_filesize': int,
    'tor2web_admin': bool,
    'tor2web_submission': bool,
    'tor2web_receiver': bool,
    'tor2web_unauth': bool,
    'postpone_superpower': bool,
    'can_delete_submission': bool,
    'subtitle': unicode,
    'exception_email': unicode,
    'reset_css': bool,
    'ahmia': bool,
}

adminNotificationDesc = {
    'server': unicode,
    'port': int,
    'security': unicode, # 'TLS' or 'SSL' only
    'username': unicode,
    'password': unicode,
    'source_name' : unicode,
    'source_email' : unicode,
    'encrypted_tip_template': unicode,
    'encrypted_tip_mail_title': unicode,
    'plaintext_tip_template': unicode,
    'plaintext_tip_mail_title': unicode,
    'zip_description': unicode,
    'comment_template': unicode,
    'comment_mail_title': unicode,
    'file_template': unicode,
    'file_mail_title': unicode,
    'disable': bool,
}

adminContextDesc = {
    'name': unicode,
    'description': unicode,
    'receipt_regexp': unicode,
    'receiver_introduction': unicode,
    'fields_introduction': unicode,
    'postpone_superpower': bool,
    'can_delete_submission': bool,
    'maximum_selectable_receivers': int,
    'require_file_description': bool,
    'delete_consensus_percentage': int,
    'require_pgp': bool,
    'selectable_receiver': bool,
    'tip_max_access' : int,
    'tip_timetolive' : int,
    'file_max_download' : int,
    'escalation_threshold' : int,
    'receivers' : [ uuid_regexp ],
    'fields': [ formFieldsDict ],
    'file_required': bool,
    'tags' : [ unicode ],
    'select_all_receivers': bool,
    'show_small_cards': bool,
}

adminReceiverDesc =  {
    'password': unicode,
    'mail_address': unicode,
    'name': unicode,
    'description': unicode,
    'contexts': [ uuid_regexp ],
    'receiver_level': int,
    'can_delete_submission': bool,
    'postpone_superpower': bool,
    'tags': [ unicode ],
    'tip_notification': bool,
    'file_notification': bool,
    'comment_notification': bool,
    'message_notification': bool,
    'gpg_key_remove': bool,
    'gpg_key_fingerprint': unicode,
    'gpg_key_info': unicode,
    "gpg_key_armor": unicode,
    "gpg_key_status": unicode,
    "gpg_enable_notification": bool,
    "gpg_enable_files": bool,
}
