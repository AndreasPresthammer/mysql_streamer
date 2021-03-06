# -*- coding: utf-8 -*-
# Copyright 2016 Yelp Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import time

import pymysql
from data_pipeline.testing_helpers.containers import Containers
from data_pipeline.testing_helpers.containers import ContainerUnavailableError
from sqlalchemy import create_engine


logger = logging.getLogger('replication_handler.testing_helper.util')


def get_service_host(containers, service_name):
    return Containers.get_container_ip_address(containers.project, service_name)


def get_db_connection(containers, db_name):
    db_host = get_service_host(containers, db_name)
    return pymysql.connect(
        host=db_host,
        user='yelpdev',
        password='',
        db='yelp',
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


def get_db_engine(containers, db_name):
    db_host = get_service_host(containers, db_name)
    return create_engine(
        "mysql+pymysql://yelpdev:@{host}/yelp?charset=utf8mb4".format(
            host=db_host
        )
    )


def execute_query_get_one_row(containers, db_name, query):
    connection = get_db_connection(containers, db_name)
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            result = cursor.fetchone()
            connection.commit()
            return result
    finally:
        connection.close()


def execute_query_get_all_rows(containers, db_name, query):
    connection = get_db_connection(containers, db_name)
    try:
        with connection.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            connection.commit()
            return results
    finally:
        connection.close()


def increment_heartbeat(containers, rbrsource):
    heartbeat_query = (
        "update yelp_heartbeat.replication_heartbeat set serial=serial+1"
    )
    execute_query_get_one_row(containers, rbrsource, heartbeat_query)


def get_heartbeat_serial(containers, rbrsource):
    query = "select * from yelp_heartbeat.replication_heartbeat"
    return execute_query_get_one_row(containers, rbrsource, query)['serial']


def db_health_check(containers, db_name, timeout_seconds):
    # Just to check the connection
    query = "SELECT 1;"
    # wait for db to pass health check
    end_time = time.time() + timeout_seconds
    logger.info("Waiting for db {} to pass health check".format(db_name))
    while end_time > time.time():
        time.sleep(0.1)
        try:
            result = execute_query_get_one_row(containers, db_name, query)
            assert result['1'] == 1
            logger.info("db {} is ready!".format(db_name))
            return
        except Exception:
            logger.info("db {} not yet available, waiting...".format(db_name))
    raise ContainerUnavailableError()


def replication_handler_health_check(containers, rbrsource, schematracker, timeout_seconds):
    table_name = "health_check"
    end_time = time.time() + timeout_seconds
    logger.info("Waiting for replication handler to pass health check")
    create_query = "CREATE TABLE {} (`id` int(11) DEFAULT NULL)".format(table_name)
    check_query = "SHOW TABLES LIKE '{}'".format(table_name)
    while end_time > time.time():
        time.sleep(0.1)
        if not execute_query_get_one_row(containers, rbrsource, check_query):
            execute_query_get_one_row(containers, rbrsource, create_query)
        if execute_query_get_one_row(containers, schematracker, check_query):
            logger.info("replication handler is ready!")
            return
        else:
            logger.info("replication handler not yet available, waiting...")
    raise ContainerUnavailableError()
