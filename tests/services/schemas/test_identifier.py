# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 CERN.
#
# Invenio-RDM-Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Test identifier schema."""

import idutils
import pytest
from marshmallow import ValidationError

from invenio_rdm_records.services.schemas.metadata import (
    IdentifierSchema,
    MetadataSchema,
)

allowed_schemes = {"doi": {"label": "DOI", "validator": idutils.is_doi}}


def test_valid_identifier():
    valid = {"identifier": "10.5281/rdm.9999999", "scheme": "doi"}
    loaded = IdentifierSchema(allowed_schemes=allowed_schemes).load(valid)
    assert valid == loaded


def test_valid_no_schema():
    """It is valid becuase the schema is detected by the schema."""
    valid_identifier = {
        "identifier": "10.5281/rdm.9999999",
    }
    loaded = IdentifierSchema(allowed_schemes=allowed_schemes).load(valid_identifier)
    valid_identifier["scheme"] = "doi"
    assert valid_identifier == loaded


def test_invalid_no_identifier():
    invalid = {"scheme": "doi"}
    with pytest.raises(ValidationError):
        data = IdentifierSchema(allowed_schemes=allowed_schemes).load(invalid)


def test_valid_empty_list(app, minimal_record):
    metadata = minimal_record["metadata"]
    metadata["identifiers"] = []
    data = MetadataSchema().load(metadata)
    assert data["identifiers"] == metadata["identifiers"]


def test_valid_multiple_identifiers(app, minimal_record):
    metadata = minimal_record["metadata"]
    metadata["identifiers"] = [
        {"identifier": "10.5281/rdm.9999999", "scheme": "doi"},
        {"identifier": "ark:/123/456", "scheme": "ark"},
    ]
    data = MetadataSchema().load(metadata)
    assert data["identifiers"] == metadata["identifiers"]


def test_invalid_duplicate_scheme(app, minimal_record):
    # NOTE: Duplicates are accepted, there is no de-duplication
    metadata = minimal_record["metadata"]
    metadata["identifiers"] = [
        {"identifier": "10.5281/rdm.9999999", "scheme": "doi"},
        {"identifier": "10.5281/rdm.0000000", "scheme": "doi"},
    ]

    with pytest.raises(ValidationError):
        data = MetadataSchema().load(metadata)

    metadata["identifiers"] = [
        {"identifier": "10.5281/rdm.9999999", "scheme": "doi"},
        {"identifier": "10.5281/rdm.0000000"},
    ]

    with pytest.raises(ValidationError):
        data = MetadataSchema().load(metadata)
