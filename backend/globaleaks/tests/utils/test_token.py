# -*- encoding: utf-8 -*-

import os
from twisted.internet.defer import inlineCallbacks

from globaleaks.anomaly import Alarm
from globaleaks.rest import errors
from globaleaks.tests import helpers
from globaleaks.tests.test_anomaly import pollute_events_for_testing
from globaleaks.utils.token import Token, TokenList


class TestToken(helpers.TestGL):
    """
    This is an object testing class,
    to check the handler testing, see in
    test_anomalies
    """
    stress_indicator = ['human_captcha', 'proof_of_work']

    @inlineCallbacks
    def setUp(self):
        yield helpers.TestGL.setUp(self)

        pollute_events_for_testing()
        yield Alarm.compute_activity_level()

    def test_token(self):
        st = Token('submission')

        st_dict = st.serialize()

        self.assertEqual(st_dict['remaining_uses'], Token.MAX_USES)

        if st.human_captcha:
            self.assertTrue(st.human_captcha.has_key('answer'))
            self.assertTrue(isinstance(st.human_captcha['answer'], int))

    @inlineCallbacks
    def test_token_create_and_get_upload_expire(self):
        file_list = []

        token_collection = []
        for i in xrange(20):
            st = Token('submission')

            token_collection.append(st)

        for t in token_collection:
            token = TokenList.get(t.id)

            yield self.emulate_file_upload(token, 3)

            for f in token.uploaded_files:
                self.assertTrue(os.path.exists(f['encrypted_path']))
                file_list.append(f['encrypted_path'])

        TokenList.reactor.advance(TokenList.get_timeout()+1)

        for t in token_collection:
            self.assertRaises(errors.TokenFailure, TokenList.get, t.id)

            for f in file_list:
                self.assertFalse(os.path.exists(f))

    def test_token_update_right_answer(self):
        token = Token('submission')

        token.human_captcha = {'question': '1 + 0', 'answer': 1, 'solved': False}
        token.proof_of_work = {'solved': False}

        # validate with right value: OK
        token.update({'human_captcha_answer': 1})

        # verify that the challenge is marked as solved
        self.assertTrue(token.human_captcha['solved'])

    def test_token_update_wrong_answer(self):
        token = Token('submission')

        token.human_captcha = {'question': 'XXX', 'answer': 1, 'solved': False}

        token.update({'human_captcha_answer': 0})

        # verify that the challenge is changed
        self.assertNotEqual(token.human_captcha['question'], 'XXX')

    def test_token_uses_limit(self):
        token = Token('submission')

        token.human_captcha = {'question': 'XXX', 'answer': 1, 'solved': False}
        token.proof_of_work = {'solved': True}

        # validate with right value: OK
        token.update({'human_captcha_answer': 1})

        for i in range(0, token.MAX_USES):
            token.use()

        # validate with right value but with no additional
        # attempts available: FAIL
        self.assertRaises(errors.TokenFailure, token.use)

    def test_proof_of_work_wrong_answer(self):
        token = Token('submission')

        difficulty = {
            'human_captcha': False,
            'proof_of_work': False
        }

        token.generate_token_challenge(difficulty)

        token = TokenList.get(token.id)
        # Note, this solution works with two '00' at the end, if the
        # difficulty changes, also this dummy value has to.
        token.proof_of_work = {'question': "7GJ4Sl37AEnP10Zk9p7q"}

        # validate with right value: OK
        self.assertFalse(token.update({'proof_of_work_answer': 26}))

        self.assertTrue(token.proof_of_work['solved'])

    def test_proof_of_work_right_answer(self):
        token = Token('submission')
        token.human_captcha = {'solved': True}

        # Note, this solution works with two '00' at the end, if the
        # difficulty changes, also this dummy value has to.
        token.proof_of_work = {'question': "7GJ4Sl37AEnP10Zk9p7q"}

        # validate with right value: OK
        self.assertTrue(token.update({'proof_of_work_answer': 0}))

    def test_tokens_garbage_collected(self):
        self.assertTrue(len(TokenList) == 0)

        for i in range(100):
            Token('submission')

        tempdict.test_reactor.advance(TokenList.get_timeout()+1)

        self.assertTrue(len(TokenList) == 0)
