# -*- coding: utf-8 -*-
#
# Copyright 2013 - StackStorm, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


import unittest2
from mock import patch, call

from email.parser import Parser

from mistral.engine.actions import actions
from mistral.engine.actions import action_types
from mistral import exceptions as exc

ACTION_TYPE = action_types.SEND_EMAIL
ACTION_NAME = "TEMPORARY"

'''
To try against a real SNMP server:

1) set LOCAL_SMPTD = True
   run debug snmpd on the local machine:
   `sudo python -m smtpd -c DebuggingServer -n localhost:25`
   Debugging server doesn't support password.

2) set REMOTE_SMPT = True
   use external SNMP (like gmail), change the configuration,
   provide actual username and password
        self.settings = {
            'host': 'smtp.gmail.com:587',
            'from': "youraccount@gmail.com",
            'password': "secret"
        }

'''
LOCAL_SMTPD = False
REMOTE_SMTP = False


class SendEmailActionTest(unittest2.TestCase):

    def setUp(self):
        self.params = {
            'to': ["dz@example.com, deg@example.com", "xyz@example.com"],
            'subject': "Multi word subject с русскими буквами",
            'body': "short multiline\nbody\nc русскими буквами",
        }
        self.settings = {
            'smtp_server': 'mail.example.com:25',
            'from': "bot@example.com",
        }
        self.to_addrs = ', '.join(self.params['to'])

    @unittest2.skipIf(not LOCAL_SMTPD, "Setup local smtpd to run it")
    def test_send_email_real(self):
        action = actions.SendEmailAction(
            ACTION_TYPE, ACTION_NAME, self.params, self.settings)
        action.run()

    @unittest2.skipIf(not REMOTE_SMTP, "Configure Remote SMTP to run it")
    def test_with_password_real(self):
        self.params['to'] = ["dz@stackstorm.com"]
        self.settings = {
            'smtp_server': 'smtp.gmail.com:587',
            'from': "username@gmail.com",
        }
        self.settings['password'] = "secret"
        action = actions.SendEmailAction(
            ACTION_TYPE, ACTION_NAME, self.params, self.settings)
        action.run()

    @patch('smtplib.SMTP')
    def test_send_email(self, smtp):
        action = actions.SendEmailAction(
            ACTION_TYPE, ACTION_NAME, self.params, self.settings)
        action.run()
        smtp.assert_called_once_with(self.settings['smtp_server'])
        sendmail = smtp.return_value.sendmail
        self.assertTrue(sendmail.called, "should call sendmail")
        self.assertEqual(
            sendmail.call_args[1]['from_addr'], self.settings['from'])
        self.assertEqual(
            sendmail.call_args[1]['to_addrs'], self.to_addrs)
        message = Parser().parsestr(sendmail.call_args[1]['msg'])
        self.assertEqual(message['from'], self.settings['from'])
        self.assertEqual(message['to'], self.to_addrs)
        self.assertEqual(message['subject'], self.params['subject'])
        self.assertEqual(message.get_payload(), self.params['body'])

    @patch('smtplib.SMTP')
    def test_with_password(self, smtp):
        self.settings['password'] = "secret"
        action = actions.SendEmailAction(
            ACTION_TYPE, ACTION_NAME, self.params, self.settings)
        action.run()
        smtpmock = smtp.return_value
        calls = [call.ehlo(), call.starttls(), call.ehlo(),
                 call.login(self.settings['from'], self.settings['password'])]
        smtpmock.assert_has_calls(calls)
        self.assertTrue(smtpmock.sendmail.called, "should call sendmail")

    @patch('mistral.engine.actions.actions.LOG')
    def test_exception(self, log):
        self.params['smtp_server'] = "wrong host"
        action = actions.SendEmailAction(
            ACTION_TYPE, ACTION_NAME, self.params, self.settings)
        try:
            action.run()
        except exc.ActionException:
            pass
        else:
            self.assertFalse("Must throw exception")
