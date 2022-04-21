# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 CERN.
# Copyright (C) 2021 data-futures.
# Copyright (C) 2022 Universität Hamburg.
#
# Invenio-RDM-Records is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""IIIF Presentation API Schema for Invenio RDM Records."""

from marshmallow import Schema, fields, missing, post_dump


class SelfList(fields.List):
    """Pass parent to the nested key.

    https://github.com/marshmallow-code/marshmallow/issues/940
    # TODO: move to marshmallow-utils
    """

    def get_value(self, obj, attr, accessor=None, default=missing):
        """Return the value for a given key from an object attribute."""
        return [obj]


class SelfNested(fields.Nested):
    """Pass parent to the nested key.

    https://github.com/marshmallow-code/marshmallow/issues/940
    # TODO: move to marshmallow-utils
    """

    def get_value(self, obj, attr, accessor=None, default=missing):
        """Return the value for a given key from an object attribute."""
        return obj


class ListAttribute(fields.List):
    """Similar to ``NestedAttribute`` but for lists.

    It also allows for ``.`` attributes, i.e. ``a.b``.
    # TODO: move to marshmallow-utils
    """

    def get_value(self, obj, attr, accessor=None, default=missing):
        """Return the value for a given key from an object attribute."""
        attribute = getattr(self, "attribute", None)
        check_key = attr if attribute is None else attribute
        if "." not in check_key:
            return getattr(obj, check_key, default)

        for key in check_key.split("."):
            obj = getattr(obj, key, default)
            if obj == default:
                return obj
        return obj


class IIIFInfoV2Schema(Schema):
    """IIIF info response schema."""

    class Meta:
        """Marshmallow meta class."""

        include = {
            "@context": fields.Constant("http://iiif.io/api/image/2/context.json"),
            "@id": fields.String(attribute="links.iiif_base"),
        }

    protocol = fields.Constant("http://iiif.io/api/image")
    profile = fields.Constant(["http://iiif.io/api/image/2/level2.json"])
    tiles = fields.Constant([{"width": 256, "scaleFactors": [1, 2, 4, 8, 16, 32, 64]}])

    width = fields.Integer(attribute="metadata.width")
    height = fields.Integer(attribute="metadata.height")


class IIIFImageServiceV2Schema(Schema):
    """IIIF image service."""

    class Meta:
        """Marshmallow meta class."""

        include = {
            "@context": fields.Constant("http://iiif.io/api/image/2/context.json"),
            "@id": fields.String(attribute="links.iiif_info"),
            "profile": fields.Constant("http://iiif.io/api/image/2/level1.json"),
        }


class IIIFImageResourceV2Schema(Schema):
    """IIIF image resource schema."""

    class Meta:
        """Marshmallow meta class."""

        include = {
            "@id": fields.String(attribute="links.iiif_api"),
            "@type": fields.Constant("dctypes:Image"),
        }

    format = fields.String(attribute="mimetype")
    width = fields.Integer(attribute="metadata.width")
    height = fields.Integer(attribute="metadata.height")
    service = SelfNested(IIIFImageServiceV2Schema)


class IIIFImageV2Schema(Schema):
    """IIIF image resource schema."""

    class Meta:
        """Marshmallow meta class."""

        include = {
            "@context": fields.Constant(
                "http://iiif.io/api/presentation/2/context.json"
            ),
            # "@id": fields.String(attribute="links.iiif_annotation"), TODO
            "@type": fields.Constant("oa:Annotation"),
        }

    motivation = fields.Constant("sc:painting")
    resource = SelfNested(IIIFImageResourceV2Schema)
    on = fields.String(attribute="links.iiif_canvas")


class IIIFCanvasV2Schema(Schema):
    """IIIF canvas schema."""

    class Meta:
        """Marshmallow meta class."""

        include = {
            "@context": fields.Constant(
                "http://iiif.io/api/presentation/2/context.json"
            ),
            "@id": fields.String(attribute="links.iiif_canvas"),
            "@type": fields.Constant("sc:Canvas"),
        }

    label = fields.String(attribute="key")
    height = fields.Integer(attribute="metadata.height")
    width = fields.Integer(attribute="metadata.width")

    images = SelfList(SelfNested(IIIFImageV2Schema))


class IIIFSequenceV2Schema(Schema):
    """IIIF sequence schema."""

    class Meta:
        """Marshmallow meta class."""

        include = {
            "@id": fields.String(attribute="links.self_iiif_sequence"),
            "@type": fields.Constant("sc:Sequence"),
        }

    label = fields.Constant("Current Page Order")
    viewingDirection = fields.Constant("left-to-right")
    viewingHint = fields.Constant("paged")

    canvases = ListAttribute(
        fields.Nested(IIIFCanvasV2Schema), attribute="files.entries"
    )


class IIIFManifestV2Schema(Schema):
    """IIIF manifest schema."""

    class Meta:
        """Marshmallow meta class."""

        include = {
            "@context": fields.Constant(
                "http://iiif.io/api/presentation/2/context.json"
            ),
            "@type": fields.Constant("sc:Manifest"),
            "@id": fields.String(attribute="links.self_iiif_manifest"),
        }

    label = fields.String(attribute="metadata.title")
    metadata = fields.Method("get_metadata")
    description = fields.String(
        attribute="metadata.description",
        default="Manifest generated by InvenioRDM",
    )
    license = fields.Method("get_license")

    sequences = SelfList(SelfNested(IIIFSequenceV2Schema))

    def get_license(self, obj):
        """Create the license."""
        # FIXME: only supports one license
        try:
            return obj["metadata"]["rights"][0]["link"]
        except (AttributeError, KeyError):
            return missing

    def get_metadata(self, obj):
        """Generate metadata entries."""
        # TODO: add creator
        return [
            {
                "label": "Publication Date",
                "value": obj["metadata"]["publication_date"],
            }
        ]

    @post_dump
    def sortcanvases(self, manifest, many, **kwargs):
        """Sort files by key.

        TODO: should sorting be done elsewhere?
        """
        manifest["sequences"][0]["canvases"].sort(key=lambda x: x["@id"])
        return manifest
