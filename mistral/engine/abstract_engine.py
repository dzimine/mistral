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

import abc

from mistral.openstack.common import log as logging
from mistral.db import api as db_api
from mistral import dsl_parser as parser
from mistral import exceptions as exc
from mistral.engine import states
from mistral.engine import workflow
from mistral.engine import data_flow


LOG = logging.getLogger(__name__)


class AbstractEngine(object):
    transport = None

    @classmethod
    @abc.abstractmethod
    def _run_tasks(cls, tasks):
        pass

    @classmethod
    def start_workflow_execution(cls, workbook_name, task_name, context):
        db_api.start_tx()

        workbook = cls._get_workbook(workbook_name)
        # Persist execution and tasks in DB.
        try:
            execution = cls._create_execution(workbook_name,
                                              task_name,
                                              context)

            tasks = cls._create_tasks(
                workflow.find_workflow_tasks(workbook, task_name),
                workbook,
                workbook_name, execution['id']
            )

            tasks_to_start = workflow.find_resolved_tasks(tasks)

            data_flow.prepare_tasks(tasks_to_start, context)

            db_api.commit_tx()
        except Exception as e:
            raise exc.EngineException("Failed to create necessary DB objects:"
                                      " %s" % e)
        finally:
            db_api.end_tx()

        cls._run_tasks(tasks_to_start)

        return execution

    @classmethod
    def convey_task_result(cls, workbook_name, execution_id,
                           task_id, state, result):
        db_api.start_tx()

        workbook = cls._get_workbook(workbook_name)
        try:
            #TODO(rakhmerov): validate state transition
            task = db_api.task_get(workbook_name, execution_id, task_id)

            task_output = data_flow.get_task_output(task, result)

            # Update task state.
            task = db_api.task_update(workbook_name, execution_id, task_id,
                                      {"state": state, "output": task_output})

            execution = db_api.execution_get(workbook_name, execution_id)

            # Calculate task outbound context.
            outbound_context = data_flow.get_outbound_context(task)

            cls._create_next_tasks(task, workbook)

            # Determine what tasks need to be started.
            tasks = db_api.tasks_get(workbook_name, execution_id)

            new_exec_state = cls._determine_execution_state(execution, tasks)

            if execution['state'] != new_exec_state:
                execution = \
                    db_api.execution_update(workbook_name, execution_id, {
                        "state": new_exec_state
                    })

                LOG.info("Changed execution state: %s" % execution)

            tasks_to_start = workflow.find_resolved_tasks(tasks)

            data_flow.prepare_tasks(tasks_to_start, outbound_context)

            db_api.commit_tx()
        except Exception as e:
            raise exc.EngineException("Failed to create necessary DB objects:"
                                      " %s" % e)
        finally:
            db_api.end_tx()

        if states.is_stopped_or_finished(execution["state"]):
            return task

        if tasks_to_start:
            cls._run_tasks(tasks_to_start)

        return task

    @classmethod
    def stop_workflow_execution(cls, workbook_name, execution_id):
        return db_api.execution_update(workbook_name, execution_id,
                                       {"state": states.STOPPED})

    @classmethod
    def get_workflow_execution_state(cls, workbook_name, execution_id):
        execution = db_api.execution_get(workbook_name, execution_id)

        if not execution:
            raise exc.EngineException("Workflow execution not found "
                                      "[workbook_name=%s, execution_id=%s]"
                                      % (workbook_name, execution_id))

        return execution["state"]

    @classmethod
    def get_task_state(cls, workbook_name, execution_id, task_id):
        task = db_api.task_get(workbook_name, execution_id, task_id)

        if not task:
            raise exc.EngineException("Task not found.")

        return task["state"]

    @classmethod
    def _create_execution(cls, workbook_name, task_name, context):
        return db_api.execution_create(workbook_name, {
            "workbook_name": workbook_name,
            "task": task_name,
            "state": states.RUNNING,
            "context": context
        })

    @classmethod
    def _create_next_tasks(cls, task, workbook):
        tasks = workflow.find_tasks_after_completion(task, workbook)

        db_tasks = cls._create_tasks(tasks, workbook, task['workbook_name'],
                                     task['execution_id'])

        return workflow.find_resolved_tasks(db_tasks)

    @classmethod
    def _create_tasks(cls, task_list, workbook, workbook_name, execution_id):
        tasks = []

        for task in task_list:
            db_task = db_api.task_create(workbook_name, execution_id, {
                "name": task.name,
                "requires": task.requires,
                "task_spec": task.to_dict(),
                "service_spec": workbook.services.get(
                    task.get_action_service()).to_dict(),
                "state": states.IDLE,
                "tags": task.get_property("tags", None)
            })

            tasks.append(db_task)

        return tasks

    @classmethod
    def _get_workbook(cls, workbook_name):
        wb = db_api.workbook_get(workbook_name)
        return parser.get_workbook(wb["definition"])

    @classmethod
    def _determine_execution_state(cls, execution, tasks):
        if workflow.is_error(tasks):
            return states.ERROR

        if workflow.is_success(tasks) or workflow.is_finished(tasks):
            return states.SUCCESS

        return execution['state']
