# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 CERN.
#
# Invenio-RDM-Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Tests for the service PIDsComponent."""

from functools import partial

import pytest
from invenio_pidstore.errors import PIDDoesNotExistError
from invenio_pidstore.models import PIDStatus
from invenio_records_resources.services.uow import UnitOfWork
from marshmallow import ValidationError

from invenio_rdm_records.records import RDMDraft, RDMRecord
from invenio_rdm_records.services import RDMRecordService
from invenio_rdm_records.services.components import PIDsComponent
from invenio_rdm_records.services.config import RDMRecordServiceConfig
from invenio_rdm_records.services.pids import PIDManager, PIDsService
from invenio_rdm_records.services.pids.errors import PIDSchemeNotSupportedError
from invenio_rdm_records.services.pids.providers import ExternalPIDProvider, PIDProvider

# providers


class TestManagedPIDProvider(PIDProvider):
    """Dummy managed provider for test purposes."""

    def __init__(self, name, pid_type=None, **kwargs):
        """Constructor."""
        super().__init__(name, pid_type=pid_type, managed=True)
        self.id_counter = 1

    def create(self, record, pid_value=None, **kwargs):
        """Create PID.

        Can be used as counter or get an assigned value (e.g. from reserve)
        """
        pid_value = pid_value or self.id_counter
        if not pid_value:
            self.id_counter += 1
        return super().create(record, pid_value=str(pid_value), **kwargs)

    def validate(self, record, identifier=None, provider=None, **kwargs):
        """Validate the attributes of the identifier."""
        success, errors = super().validate(record, identifier, provider, **kwargs)
        try:
            int(identifier)
        except ValueError:
            errors.append("Identifier must be an integer.")
        return (True, []) if not errors else (False, errors)


# configs


class TestServiceConfigNoPIDs(RDMRecordServiceConfig):
    """Custom service config with only pid providers."""

    pids_providers = {}
    pids_required = []


class TestServiceConfigNoRequiredPIDs(RDMRecordServiceConfig):
    """Custom service config with only pid providers."""

    pids_providers = {
        "test": {
            "default": "managed",
            "managed": TestManagedPIDProvider("managed", pid_type="test"),
            "external": ExternalPIDProvider("external", pid_type="test"),
        }
    }
    pids_required = []


class TestServiceConfigRequiredManagedPID(RDMRecordServiceConfig):
    """Custom service config with only pid providers."""

    pids_providers = {
        "test": {
            "default": "managed",
            "managed": TestManagedPIDProvider("managed", pid_type="test"),
        }
    }
    pids_required = ["test"]


class TestServiceConfigRequiredExternalPID(RDMRecordServiceConfig):
    """Custom service config with only pid providers."""

    pids_providers = {
        "test": {
            "default": "external",
            "external": ExternalPIDProvider("external", pid_type="test"),
        }
    }
    pids_required = ["test"]


# components


@pytest.fixture(scope="module")
def no_pids_cmp():
    service = RDMRecordService(
        config=TestServiceConfigNoPIDs,
        pids_service=PIDsService(
            config=TestServiceConfigNoPIDs, manager_cls=PIDManager
        ),
    )
    c = PIDsComponent(service=service)
    c.uow = UnitOfWork()
    return c


@pytest.fixture(scope="module")
def no_required_pids_service():
    return RDMRecordService(
        config=TestServiceConfigNoRequiredPIDs,
        pids_service=PIDsService(
            config=TestServiceConfigNoRequiredPIDs, manager_cls=PIDManager
        ),
    )


@pytest.fixture(scope="module")
def no_required_pids_cmp(no_required_pids_service):
    c = PIDsComponent(service=no_required_pids_service)
    c.uow = UnitOfWork()
    return c


@pytest.fixture(scope="module")
def required_managed_pids_cmp():
    service = RDMRecordService(
        config=TestServiceConfigRequiredManagedPID,
        pids_service=PIDsService(
            config=TestServiceConfigRequiredManagedPID, manager_cls=PIDManager
        ),
    )
    c = PIDsComponent(service=service)
    c.uow = UnitOfWork()
    return c


@pytest.fixture(scope="module")
def required_external_pids_cmp():
    service = RDMRecordService(
        config=TestServiceConfigRequiredExternalPID,
        pids_service=PIDsService(
            config=TestServiceConfigRequiredExternalPID, manager_cls=PIDManager
        ),
    )
    c = PIDsComponent(service=service)
    c.uow = UnitOfWork()
    return c


# PID Creation


def test_create_no_pids(no_pids_cmp, minimal_record, identity_simple, location):
    component = no_pids_cmp
    # empty pids field
    pids = {}
    # make sure `pids` field is added
    data = minimal_record.copy()
    data["pids"] = pids

    # create a minimal draft
    draft = RDMDraft.create(data)
    component.create(identity_simple, data=data, record=draft)
    assert "pids" in draft and draft.pids == {}


def test_create_pid_type_not_supported(
    no_pids_cmp, minimal_record, identity_simple, location
):
    component = no_pids_cmp
    # managed pid
    pids = {"test": {"identifier": "1234", "provider": "managed"}}
    # make sure `pids` field is added
    data = minimal_record.copy()
    data["pids"] = pids

    # create a minimal draft
    draft = RDMDraft.create(data)
    # note that something like {"test": {}} should be caught at marshmallow
    # level, which is tested at service level
    with pytest.raises(PIDSchemeNotSupportedError):
        component.create(identity_simple, data=data, record=draft)


@pytest.mark.parametrize(
    "pids",
    [
        {},
        {"test": {"identifier": "1234", "provider": "managed"}},
        {"test": {"identifier": "1234", "provider": "external"}},
    ],
)
def test_create_no_required_pids(
    pids, no_required_pids_cmp, minimal_record, identity_simple, location
):
    component = no_required_pids_cmp
    # make sure `pids` field is added
    data = minimal_record.copy()
    data["pids"] = pids

    # create a minimal draft
    draft = RDMDraft.create(data)
    component.create(identity_simple, data=data, record=draft)
    assert "pids" in draft and draft.pids == pids


@pytest.mark.parametrize(
    "pids", [{}, {"test": {"identifier": "1234", "provider": "managed"}}]
)
def test_create_with_required_managed(
    pids, required_managed_pids_cmp, minimal_record, identity_simple, location
):
    component = required_managed_pids_cmp
    # make sure `pids` field is added
    data = minimal_record.copy()
    data["pids"] = pids

    # create a minimal draft
    draft = RDMDraft.create(data)
    component.create(identity_simple, data=data, record=draft)
    assert "pids" in draft and draft.pids == pids


@pytest.mark.parametrize(
    "pids,expected_errors",
    [
        (
            {"test": {"identifier": "", "provider": "managed"}},
            [{"field": "pids.test", "messages": ["Identifier must be an integer."]}],
        ),
        (
            {"test": {"identifier": "", "provider": "external"}},
            [
                {
                    "field": "pids.test",
                    "messages": ["Missing external for required field."],
                }
            ],
        ),
    ],
)
def test_create_with_incomplete_payload(
    pids,
    expected_errors,
    no_required_pids_cmp,
    minimal_record,
    identity_simple,
    location,
):
    component = no_required_pids_cmp
    # make sure `pids` field is added
    data = minimal_record.copy()
    data["pids"] = pids

    # create a minimal draft
    draft = RDMDraft.create(data)
    errors = []
    component.create(identity_simple, data=data, record=draft, errors=errors)
    assert errors == expected_errors
    assert "pids" in draft and draft.pids == pids


# PID Publishing


def test_publish_no_pids(no_pids_cmp, minimal_record, identity_simple, location):
    component = no_pids_cmp
    # empty pids field
    pids = {}
    # make sure `pids` field is added
    data = minimal_record.copy()
    data["pids"] = pids

    # create a minimal draft
    draft = RDMDraft.create(data)
    # no validation needed since /publish gets no payload (new data)
    record = RDMRecord.publish(draft)
    component.publish(identity_simple, draft=draft, record=record)
    assert record.get("pids") == {}


@pytest.mark.parametrize(
    "pids",
    [
        {},
        {"test": {"identifier": "1234", "provider": "external"}},
    ],
)
def test_publish_no_required_pids(
    pids,
    no_required_pids_service,
    no_required_pids_cmp,
    minimal_record,
    identity_simple,
    location,
):
    # a managed pid is not accepted in this case since it would need to be
    # created/reserved before hand. that flow is tested at service level.
    component = no_required_pids_cmp
    # make sure `pids` field is added
    data = minimal_record.copy()
    data["pids"] = pids

    # create a minimal draft
    draft = RDMDraft.create(data)
    # no validation needed since /publish gets no payload (new data)
    record = RDMRecord.publish(draft)

    component.publish(identity_simple, draft=draft, record=record)
    assert record.get("pids") == pids
    for schema, pid in pids.items():
        provider = no_required_pids_service.pids.pid_manager._get_provider(
            schema, pid["provider"]
        )
        pid = provider.get(pid.get("identifier"))
        assert pid.is_reserved()  # cannot test registration because is async


def test_publish_non_existing_required_managed(
    required_managed_pids_cmp, minimal_record, identity_simple, location
):
    # no need to test for existing (i.e. already in the payload) required pids
    # since they go over the flow of the test above
    # test_publish_no_required_pids

    component = required_managed_pids_cmp
    # make sure `pids` field is added
    data = minimal_record.copy()
    data["pids"] = {}

    # create a minimal draft
    draft = RDMDraft.create(data)
    # no validation needed since /publish gets no payload (new data)
    record = RDMRecord.publish(draft)
    component.publish(identity_simple, draft=draft, record=record)
    assert "pids" in record
    assert record.pids == {"test": {"identifier": "1", "provider": "managed"}}

    provider = TestManagedPIDProvider("managed", pid_type="test")
    pid = provider.get(record.pids["test"]["identifier"])
    assert pid.is_reserved()  # cannot test registration because is async


def test_publish_non_existing_required_external(
    required_external_pids_cmp, minimal_record, identity_simple, location
):
    # no need to test for existing (i.e. already in the payload) required pids
    # since they go over the flow of the test above
    # test_publish_no_required_pids

    component = required_external_pids_cmp
    # make sure `pids` field is added
    data = minimal_record.copy()
    data["pids"] = {}

    # create a minimal draft
    draft = RDMDraft.create(data)
    # no validation needed since /publish gets no payload (new data)
    record = RDMRecord.publish(draft)
    with pytest.raises(ValidationError):
        component.publish(identity_simple, draft=draft, record=record)


# PID Deletion
# Ad-hoc PID deletion happens in the PIDs subservice. These tests are only
# meant to test the chain of deletion that happens when deleting a record


def _create_managed_pid(draft, pid_value, provider):
    pid = provider.create(draft, pid_value=pid_value)
    pid = provider.get(pid_value, pid_provider="managed")
    assert pid.status == PIDStatus.NEW
    return pid


def test_delete_pids_from_draft(
    no_required_pids_cmp, minimal_record, identity_simple, location
):
    # a draft that gets updated with a pid saved to pidstore via reserve
    component = no_required_pids_cmp
    data = minimal_record.copy()
    pid_value = "1"
    data["pids"] = {"test": {"identifier": pid_value, "provider": "managed"}}

    # create a minimal draft
    draft = RDMDraft.create(data)
    # create pid, simulates a query to the reserve endpoint (/:scheme)
    provider = TestManagedPIDProvider("managed", pid_type="test")
    pid = _create_managed_pid(draft, pid_value, provider)

    # run the delete hook and check the pid is not in the system anymore
    component.delete_draft(identity_simple, draft=draft)
    with pytest.raises(PIDDoesNotExistError):
        pid = provider.get(pid_value, pid_provider="managed")


# PID Update
# permissions updates are check at service level
def test_update_external_to_empty(
    no_required_pids_cmp, minimal_record, superuser_identity, location
):
    component = no_required_pids_cmp
    data = minimal_record.copy()
    data["pids"] = {"test": {"identifier": "1234", "provider": "external"}}

    # create a minimal draft
    draft = RDMDraft.create(data)
    assert draft.pids["test"]["identifier"] == "1234"
    data["pids"] = {}
    # run the delete hook and check the pid is not in the system anymore
    component.update_draft(superuser_identity, data=data, record=draft)
    assert draft.pids == {}


def test_update_managed_to_empty(
    no_required_pids_cmp, minimal_record, superuser_identity, location
):
    component = no_required_pids_cmp
    data = minimal_record.copy()
    pid_value = "1"
    data["pids"] = {"test": {"identifier": pid_value, "provider": "managed"}}

    # create a minimal draft
    draft = RDMDraft.create(data)
    assert draft.pids["test"]["identifier"] == "1"
    # create pid, simulates a query to the reserve endpoint (/:scheme)
    provider = TestManagedPIDProvider("managed", pid_type="test")
    pid = _create_managed_pid(draft, pid_value, provider)

    data["pids"] = {}
    # run the delete hook and check the pid is not in the system anymore
    component.update_draft(superuser_identity, data=data, record=draft)
    assert draft.pids == {}
    # note that the old pid will still exist in the db until publish time


def test_update_external_to_managed(
    no_required_pids_cmp, minimal_record, superuser_identity, location
):
    component = no_required_pids_cmp
    data = minimal_record.copy()
    data["pids"] = {"test": {"identifier": "1234", "provider": "external"}}

    # create a minimal draft
    draft = RDMDraft.create(data)
    assert draft.pids["test"]["identifier"] == "1234"
    # create pid, simulates a query to the reserve endpoint (/:scheme)
    pid_value = "1"
    provider = TestManagedPIDProvider("managed", pid_type="test")
    pid = _create_managed_pid(draft, pid_value, provider)

    ext_pids = {"test": {"identifier": pid_value, "provider": "managed"}}
    data["pids"] = ext_pids
    # run the delete hook and check the pid is not in the system anymore
    component.update_draft(superuser_identity, data=data, record=draft)
    assert draft.pids == ext_pids
    pid = provider.get(pid_value, pid_provider="managed")
    assert pid.pid_value == pid_value
    assert pid.status == PIDStatus.NEW


def test_update_managed_to_external(
    no_required_pids_cmp, minimal_record, superuser_identity, location
):
    component = no_required_pids_cmp
    data = minimal_record.copy()
    pid_value = "1"
    data["pids"] = {"test": {"identifier": pid_value, "provider": "managed"}}

    # create a minimal draft
    draft = RDMDraft.create(data)
    assert draft.pids["test"]["identifier"] == "1"
    # create pid, simulates a query to the reserve endpoint (/:scheme)
    provider = TestManagedPIDProvider("managed", pid_type="test")
    pid = _create_managed_pid(draft, pid_value, provider)

    ext_pids = {"test": {"identifier": "1234", "provider": "external"}}
    data["pids"] = ext_pids
    # run the delete hook and check the pid is not in the system anymore
    component.update_draft(superuser_identity, data=data, record=draft)
    assert draft.pids == ext_pids
    # note that the old pid will still exist in the db until publish time
