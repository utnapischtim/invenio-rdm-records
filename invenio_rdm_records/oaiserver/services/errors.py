# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2022 Graz University of Technology.
#
# Invenio-RDM-Records is free software; you can redistribute it and/or modify
# under the terms of the MIT License; see LICENSE file for more details.

"""Errors for OAIPMH-Set."""

from flask_babelex import gettext as _


class OAIPMHError(Exception):
    """Base class for OAI-PMH errors."""

    def __init__(self, description, *args: object):
        """Constructor."""
        self.description = description
        super().__init__(*args)


class OAIPMHSetDoesNotExistError(OAIPMHError):
    """The provided set spec does not exist."""

    def __init__(self, query_arguments):
        """Initialise error."""
        super().__init__(
            description=_(f"A set where {query_arguments} does not exist.")
        )


class OAIPMHSetIDDoesNotExistError(OAIPMHError):
    """The provided set spec does not exist."""

    def __init__(self, id):
        """Initialise error."""
        super().__init__(description=_(f"A set with id {id} does not exist."))


class OAIPMHSetSpecAlreadyExistsError(OAIPMHError):
    """The provided set spec already exists."""

    def __init__(self, spec):
        """Initialise error."""
        super().__init__(description=_(f"A set with spec '{spec}' already exists."))
