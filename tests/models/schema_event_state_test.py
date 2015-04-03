# -*- coding: utf-8 -*-
import pytest

from replication_handler.models.schema_event_state import SchemaEventState
from testing import sandbox


class TestSchemaEventState(object):

    @pytest.fixture
    def gtid(self):
        return "3E11FA47-71CA-11E1-9E33-C80AA9429562:1-5"

    @pytest.fixture
    def status(self):
        return "Pending"

    @pytest.fixture
    def query(self):
        return "alter table business add column category varchar(255)"

    @pytest.fixture
    def create_table_statement(self):
        return "CREATE TABLE `business` (\
                   `id` int(11) NOT NULL AUTO_INCREMENT,\
                   `name` VARCHAR(255) NOT NULL,\
                   `time_created` int(11) NOT NULL,\
                   `time_updated` int(11) NOT NULL,\
                   PRIMARY KEY (`id`)\
               ) ENGINE=InnoDB DEFAULT CHARSET=utf8 COLLATE=utf8_unicode_ci"

    @pytest.fixture
    def table_name(self):
        return "business"

    @pytest.yield_fixture
    def sandbox_session(self):
        with sandbox.database_sandbox_master_connection_set() as sandbox_session:
            yield sandbox_session

    @pytest.yield_fixture
    def schema_event_state_obj(
        self,
        gtid,
        status,
        query,
        create_table_statement,
        table_name,
        sandbox_session
    ):
        schema_event_state = SchemaEventState(
            gtid=gtid,
            status=status,
            query=query,
            create_table_statement=create_table_statement,
            table_name=table_name
        )
        sandbox_session.add(schema_event_state)
        sandbox_session.flush()
        yield schema_event_state

    def test_get_latest_schema_event_state(self, schema_event_state_obj, sandbox_session):
        result = SchemaEventState.get_latest_schema_event_state(sandbox_session)
        # Since result is a copy of original obj, they are not the same object, we will
        # be comparing their attributes..
        assert result.id == schema_event_state_obj.id
        assert result.gtid == schema_event_state_obj.gtid
        assert result.table_name == schema_event_state_obj.table_name
        assert result.query == schema_event_state_obj.query
        assert result.status == schema_event_state_obj.status

    def test_delete_schema_event_state_by_id(self, schema_event_state_obj, sandbox_session):
        result = SchemaEventState.delete_schema_event_state_by_id(
            sandbox_session,
            schema_event_state_obj.id
        )
        result = sandbox_session.query(SchemaEventState).all()
        assert result == []
