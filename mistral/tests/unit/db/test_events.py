# -*- coding: utf-8 -*-
#
# Copyright 2013 - Mirantis, Inc.
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

from mistral.openstack.common import timeutils

from mistral.db.sqlalchemy import api as db_api
from mistral.tests.unit import base as test_base


SAMPLE_EVENT = {
    "id": "123",
    "name": "test_event",
    "pattern": "* *",
    "next_execution_time": timeutils.utcnow()
}


class EventTest(test_base.DbTestCase):
    def test_event_create_list_delete(self):
        event_db_obj = db_api.event_create(SAMPLE_EVENT)
        self.assertIsInstance(event_db_obj, dict)