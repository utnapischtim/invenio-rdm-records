# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 CERN.
#
# Invenio-RDM-Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""External provider tests."""

import pytest
from flask_babelex import lazy_gettext as _
from invenio_pidstore.models import PersistentIdentifier, PIDStatus

from invenio_rdm_records.records import RDMDraft, RDMRecord
from invenio_rdm_records.services.pids.providers import ExternalPIDProvider


@pytest.fixture(scope="function")
def external_provider():
    """Application factory fixture."""
    return ExternalPIDProvider("external", "testid", label="DOI")


@pytest.fixture(scope="function")
def record(location, db):
    """Creates an empty record."""
    draft = RDMDraft.create({})
    record = RDMRecord.publish(draft)
    return record


def test_external_provider_create(record, external_provider, db):
    created_pid = external_provider.create(record, "avalue")
    db_pid = PersistentIdentifier.get(
        pid_value=created_pid.pid_value, pid_type="testid"
    )

    assert created_pid == db_pid
    assert created_pid.pid_value
    assert created_pid.pid_type == "testid"
    assert created_pid.status == PIDStatus.NEW


def test_external_provider_get(record, external_provider, db):
    created_pid = external_provider.create(record, "avalue")
    get_pid = external_provider.get(created_pid.pid_value)

    assert created_pid == get_pid
    assert get_pid.pid_value
    assert get_pid.pid_type == "testid"
    assert get_pid.status == PIDStatus.NEW


def test_external_provider_register(record, external_provider, db):
    created_pid = external_provider.create(record, "avalue")
    assert external_provider.register(pid=created_pid, record=record)

    db_pid = PersistentIdentifier.get(
        pid_value=created_pid.pid_value, pid_type="testid"
    )

    assert created_pid == db_pid
    assert db_pid.pid_value
    assert db_pid.pid_type == "testid"
    assert db_pid.status == PIDStatus.REGISTERED


def test_external_provider_validate(running_app, db, external_provider, record):
    success, errors = external_provider.validate(
        identifier="somevalue", record=record, provider="external"
    )
    assert success
    assert not errors


def test_external_provider_validate_failure(running_app, db, external_provider, record):
    with pytest.raises(Exception):
        external_provider.validate(
            record=record, client="someclient", provider="external"
        )

    with pytest.raises(Exception):
        external_provider.validate(record=record, provider="wrong")

    success, errors = external_provider.validate(record=record, provider="external")
    assert not success
    assert "Missing DOI for required field." in errors
