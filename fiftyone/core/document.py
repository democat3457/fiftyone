"""
Base classes for objects that are backed by database documents.

| Copyright 2017-2021, Voxel51, Inc.
| `voxel51.com <https://voxel51.com/>`_
|
"""
from copy import deepcopy

import eta.core.serial as etas
import eta.core.utils as etau

import fiftyone.core.labels as fol
from fiftyone.core.singletons import DocumentSingleton


class _Document(object):
    def __init__(self, doc, dataset=None):
        self._doc = doc
        self._dataset = dataset

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return self._doc.fancy_repr(class_name=self.__class__.__name__)

    def __dir__(self):
        return super().__dir__() + list(self.field_names)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return self._doc == other._doc

    def __getattr__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError:
            return self.get_field(name)

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
            return

        if not self.has_field(name):
            dtype = "frame" if "Frame" in self.__class__.__name__ else "sample"
            raise ValueError(
                "Adding %s fields using the `%s.field = value` syntax is not "
                "allowed; use `%s['field'] = value` instead"
                % (dtype, dtype, dtype)
            )

        self.set_field(name, value)

    def __delattr__(self, name):
        try:
            super().__delattr__(name)
        except AttributeError:
            self.clear_field(name)

    def __getitem__(self, field_name):
        try:
            return self.get_field(field_name)
        except AttributeError as e:
            raise KeyError(e.args[0])

    def __setitem__(self, field_name, value):
        self.set_field(field_name, value)

    def __delitem__(self, field_name):
        try:
            self.clear_field(field_name)
        except AttributeError as e:
            raise KeyError(e.args[0])

    def __copy__(self):
        return self.copy()

    @property
    def id(self):
        """The ID of the document, or ``None`` if it has not been added to the
        database.
        """
        return str(self._doc.id) if self._in_db else None

    @property
    def _id(self):
        """The ObjectId of the document, or ``None`` if it has not been added
        to the database.
        """
        return self._doc.id if self._in_db else None

    @property
    def ingest_time(self):
        """The time the document was added to the database, or ``None`` if it
        has not been added to the database.
        """
        return self._doc.ingest_time

    @property
    def in_dataset(self):
        """Whether the document has been added to a dataset."""
        return self.dataset is not None

    @property
    def dataset(self):
        """The dataset to which this document belongs, or ``None`` if it has
        not been added to a dataset.
        """
        return self._dataset

    @property
    def field_names(self):
        """An ordered tuple of the names of the fields of this document."""
        return self._doc.field_names

    @property
    def _in_db(self):
        """Whether the document has been inserted into the database."""
        return self._doc.in_db

    def _get_field_names(self, include_private=False):
        """Returns an ordered tuple of field names of this document.

        Args:
            include_private (False): whether to include private fields

        Returns:
            a tuple of field names
        """
        return self._doc._get_field_names(include_private=include_private)

    def has_field(self, field_name):
        """Determines whether the document has the given field.

        Args:
            field_name: the field name

        Returns:
            True/False
        """
        return self._doc.has_field(field_name)

    def get_field(self, field_name):
        """Gets the value of a field of the document.

        Args:
            field_name: the field name

        Returns:
            the field value

        Raises:
            AttributeError: if the field does not exist
        """
        if field_name == "id":
            return self.id

        try:
            return self._doc.get_field(field_name)
        except AttributeError:
            raise AttributeError(
                "%s has no field '%s'" % (self.__class__.__name__, field_name)
            )

    def set_field(self, field_name, value, create=True):
        """Sets the value of a field of the document.

        Args:
            field_name: the field name
            value: the field value
            create (True): whether to create the field if it does not exist

        Raises:
            ValueError: if ``field_name`` is not an allowed field name
            AttirubteError: if the field does not exist and ``create == False``
        """
        if field_name.startswith("_"):
            raise ValueError(
                "Invalid field name: '%s'. Field names cannot start with '_'"
                % field_name
            )

        self._doc.set_field(field_name, value, create=create)

    def update_fields(self, fields_dict, expand_schema=True):
        """Sets the dictionary of fields on the document.

        Args:
            fields_dict: a dict mapping field names to values
            expand_schema (True): whether to dynamically add new fields
                encountered to the document schema. If False, an error is
                raised if any fields are not in the document schema

        Raises:
            AttributeError: if ``expand_schema == False`` and a field does not
                exist
        """
        for field_name, value in fields_dict.items():
            self.set_field(field_name, value, create=expand_schema)

    def clear_field(self, field_name):
        """Clears the value of a field of the document.

        Args:
            field_name: the name of the field to clear

        Raises:
            AttributeError: if the field does not exist
        """
        self._doc.clear_field(field_name)

    def iter_fields(self):
        """Returns an iterator over the ``(name, value)`` pairs of the fields
        of the document.

        Returns:
            an iterator that emits ``(name, value)`` tuples
        """
        for field_name in self.field_names:
            yield field_name, self.get_field(field_name)

    def merge(
        self,
        document,
        fields=None,
        omit_fields=None,
        omit_none_fields=True,
        merge_lists=False,
        overwrite=True,
        expand_schema=True,
    ):
        """Merges the fields of the document into this document.

        Args:
            document: a :class:`Document` or :class:`DocumentView` the same
                type
            fields (None): an optional field or iterable of fields to which to
                restrict the merge
            omit_fields (None): an optional field or iterable of fields to
                exclude from the merge
            omit_none_fields (True): whether to omit ``None``-valued fields of
                the provided document
            merge_lists (False): whether to merge top-level list fields and the
                elements of label list fields. If ``True``, this parameter
                supercedes the ``overwrite`` parameter for list fields, and,
                for label lists fields, existing
                :class:`fiftyone.core.label.Label` elements are either replaced
                (when ``overwrite`` is True) or kept (when ``overwrite`` is
                False) when their ``id`` matches a
                :class:`fiftyone.core.label.Label` from the provided document
            overwrite (True): whether to overwrite existing fields. Note that
                existing fields whose values are ``None`` are always
                overwritten
            expand_schema (True): whether to dynamically add new fields
                encountered to the document schema. If False, an error is
                raised if any fields are not in the document schema

        Raises:
            AttributeError: if ``expand_schema == False`` and a field does not
                exist
        """
        if not overwrite:
            existing_field_names = set(self.field_names)

        fields = self._parse_fields(fields=fields, omit_fields=omit_fields)

        for field_name in fields:
            value = document[field_name]

            if omit_none_fields and value is None:
                continue

            try:
                curr_value = self[field_name]
            except KeyError:
                curr_value = None

            if merge_lists:
                field_type = type(curr_value)

                if issubclass(field_type, list):
                    if value is not None:
                        curr_value.extend(
                            v for v in value if v not in curr_value
                        )

                    continue

                if field_type in fol._LABEL_LIST_FIELDS:
                    if value is not None:
                        list_field = field_type._LABEL_LIST_FIELD
                        _merge_labels(
                            curr_value[list_field],
                            value[list_field],
                            overwrite=overwrite,
                        )

                    continue

            if (
                not overwrite
                and field_name in existing_field_names
                and curr_value is not None
            ):
                continue

            self.set_field(field_name, value, create=expand_schema)

    def copy(self, fields=None, omit_fields=None):
        """Returns a deep copy of the document that has not been added to the
        database.

        Args:
            fields (None): an optional field or iterable of fields to which to
                restrict the copy
            omit_fields (None): an optional field or iterable of fields to
                exclude from the copy

        Returns:
            a :class:`Document`
        """
        raise NotImplementedError("subclass must implement copy()")

    def to_dict(self):
        """Serializes the document to a JSON dictionary.

        The document ID and private fields are excluded in this representation.

        Returns:
            a JSON dict
        """
        d = self._doc.to_dict(extended=True)
        return {k: v for k, v in d.items() if not k.startswith("_")}

    def to_mongo_dict(self):
        """Serializes the document to a BSON dictionary equivalent to the
        representation that would be stored in the database.

        Returns:
            a BSON dict
        """
        return self._doc.to_dict()

    def to_json(self, pretty_print=False):
        """Serializes the document to a JSON string.

        The document ID and private fields are excluded in this representation.

        Args:
            pretty_print (False): whether to render the JSON in human readable
                format with newlines and indentations

        Returns:
            a JSON string
        """
        return etas.json_to_str(self.to_dict(), pretty_print=pretty_print)

    def save(self):
        """Saves the document to the database."""
        self._doc.save()

    def _parse_fields(self, fields=None, omit_fields=None):
        if fields is None:
            fields = self.field_names
        elif etau.is_str(fields):
            fields = [fields]

        if omit_fields is not None:
            if etau.is_str(omit_fields):
                omit_fields = {omit_fields}
            else:
                omit_fields = set(omit_fields)

            fields = [f for f in fields if f not in omit_fields]

        return fields


class Document(_Document):
    """Abstract base class for objects that are associated with
    :class:`fiftyone.core.dataset.Dataset` instances and are backed by
    documents in database collections.

    Document subclasses whose in-dataset instances should be singletons can
    inherit this behavior by deriving from the
    :class:`fiftyone.core.singletons.DocumentSingleton` metaclass.

    Args:
        **kwargs: field names and values
    """

    # The :class:`fiftyone.core.odm.document.Document` class used by this class
    # to store backing documents for instances that are *not* in the dataset
    _NO_DATASET_DOC_CLS = None

    def __init__(self, **kwargs):
        # pylint: disable=not-callable
        doc = self._NO_DATASET_DOC_CLS(**kwargs)
        super().__init__(doc)

    def copy(self, fields=None, omit_fields=None):
        fields = self._parse_fields(fields=fields, omit_fields=omit_fields)
        return self.__class__(
            **{field: deepcopy(self[field]) for field in fields}
        )

    def reload(self, hard=False):
        """Reloads the document from the database.

        Args:
            hard (False): whether to reload the document's schema in addition
                to its field values. This is necessary if new fields may have
                been added to the document schema
        """
        if hard:
            self._reload_backing_doc()
        else:
            # We can only reload fields that are in our schema
            self._doc.reload(*list(self._doc))

    @classmethod
    def from_doc(cls, doc, dataset=None):
        """Creates a :class:`Document` backed by the given database document.

        Args:
            doc: a :class:`fiftyone.core.odm.document.Document`
            dataset (None): the :class:`fiftyone.core.dataset.Dataset` that
                the document belongs to, if any

        Returns:
            a :class:`Document`
        """
        if isinstance(doc, cls._NO_DATASET_DOC_CLS):
            document = cls.__new__(cls)
            document._doc = doc
            document._dataset = None
            return document

        if issubclass(type(cls), DocumentSingleton):
            document = cls._get_instance(doc)
            if document is not None:
                return document

        if dataset is None:
            raise ValueError(
                "`dataset` argument must be provided for documents in "
                "datasets"
            )

        document = cls.__new__(cls)
        document._doc = None  # prevents recursion
        document._set_backing_doc(doc, dataset=dataset)

        return document

    @classmethod
    def from_dict(cls, d):
        """Loads the document from a JSON dictionary.

        The returned document will not belong to a dataset.

        Returns:
            a :class:`Document`
        """
        doc = cls._NO_DATASET_DOC_CLS.from_dict(d, extended=True)
        return cls.from_doc(doc)

    @classmethod
    def from_json(cls, s):
        """Loads the document from a JSON string.

        The returned document will not belong to a dataset.

        Args:
            s: the JSON string

        Returns:
            a :class:`Document`
        """
        doc = cls._NO_DATASET_DOC_CLS.from_json(s)
        return cls.from_doc(doc)

    def _reload_backing_doc(self):
        """Reloads the backing doc from the database."""
        raise NotImplementedError(
            "subclass must implement _reload_backing_doc()"
        )

    def _set_backing_doc(self, doc, dataset=None):
        """Sets the backing doc for the document.

        Args:
            doc: a :class:`fiftyone.core.odm.document.Document`
            dataset (None): the :class:`fiftyone.core.dataset.Dataset` to which
                the document belongs, if any
        """
        self._doc = doc
        self._dataset = dataset

        cls = self.__class__
        if issubclass(type(cls), DocumentSingleton):
            cls._register_instance(self)

    def _reset_backing_doc(self):
        """Resets the backing doc for the document.

        The document will no longer belong to a dataset.
        """
        self._doc = self.copy()._doc
        self._dataset = None


class DocumentView(_Document):
    """A view into a :class:`Document` in a dataset.

    Like :class:`Document` instances, the fields of a :class:`DocumentView`
    instance can be modified, new fields can be created, and any changes can be
    saved to the database.

    :class:`DocumentView` instances differ from :class:`Document` instances
    in the following ways:

    -   A document view may contain only a subset of the fields of its source
        document, either by selecting and/or excluding specific fields
    -   A document view may contain array fields or embedded array fields that
        have been filtered, thus containing only a subset of the array elements
        from the source document
    -   Excluded fields of a document view may not be accessed or modified

    .. note::

        :meth:`DocumentView.save` will not delete any excluded fields or
        filtered array elements from the source document.

    Document views should never be created manually; they are generated when
    accessing the contents of a :class:`fiftyone.core.view.DatasetView`.

    Args:
        doc: a :class:`fiftyone.core.odm.document.Document`
        view: the :class:`fiftyone.core.view.DatasetView` that the document
            belongs to
        selected_fields (None): a set of field names that this document view is
            restricted to, if any
        excluded_fields (None): a set of field names that are excluded from
            this document view, if any
        filtered_fields (None): a set of field names of array fields that are
            filtered in this document view, if any
    """

    # The `Document` class associated with this `DocumentView` class
    # Subclasses must define this
    _DOCUMENT_CLS = Document

    def __init__(
        self,
        doc,
        view,
        selected_fields=None,
        excluded_fields=None,
        filtered_fields=None,
    ):
        if selected_fields is not None and excluded_fields is not None:
            selected_fields = selected_fields.difference(excluded_fields)
            excluded_fields = None

        self._view = view
        self._selected_fields = selected_fields
        self._excluded_fields = excluded_fields
        self._filtered_fields = filtered_fields

        super().__init__(doc, dataset=view._dataset)

    def __repr__(self):
        if self._selected_fields is not None:
            select_fields = ("id",) + tuple(self._selected_fields)
        else:
            select_fields = None

        return self._doc.fancy_repr(
            class_name=self.__class__.__name__,
            select_fields=select_fields,
            exclude_fields=self._excluded_fields,
        )

    @property
    def field_names(self):
        """An ordered tuple of field names of this document view.

        This may be a subset of all fields of the document if fields have been
        selected or excluded.
        """
        field_names = super().field_names

        if self._selected_fields is not None:
            field_names = tuple(
                fn for fn in field_names if fn in self._selected_fields
            )

        if self._excluded_fields is not None:
            field_names = tuple(
                fn for fn in field_names if fn not in self._excluded_fields
            )

        return field_names

    @property
    def selected_field_names(self):
        """The set of field names that are selected on this document view, or
        ``None`` if no fields are explicitly selected.
        """
        return self._selected_fields

    @property
    def excluded_field_names(self):
        """The set of field names that are excluded on this document view, or
        ``None`` if no fields are explicitly excluded.
        """
        return self._excluded_fields

    @property
    def filtered_field_names(self):
        """The set of field names or ``embedded.field.names`` that have been
        filtered on this document view, or ``None`` if no fields are filtered.
        """
        return self._filtered_fields

    def has_field(self, field_name):
        ef = self._excluded_fields
        if ef is not None and field_name in ef:
            return False

        sf = self._selected_fields
        if sf is not None and field_name not in sf:
            return False

        return super().has_field(field_name)

    def get_field(self, field_name):
        ef = self._excluded_fields
        if ef is not None and field_name in ef:
            raise AttributeError(
                "Field '%s' is excluded from this %s"
                % (field_name, self.__class__.__name__)
            )

        value = super().get_field(field_name)

        sf = self._selected_fields
        if sf is not None and field_name not in sf:
            raise AttributeError(
                "Field '%s' was not selected on this %s"
                % (field_name, self.__class__.__name__)
            )

        return value

    def set_field(self, field_name, value, create=True):
        if not create:
            # Ensures field exists
            _ = self.get_field(field_name)

            super().set_field(field_name, value, create=False)
        else:
            super().set_field(field_name, value, create=True)

            if self._excluded_fields is not None:
                self._excluded_fields.discard(field_name)

            if self._selected_fields is not None:
                self._selected_fields.add(field_name)

    def clear_field(self, field_name):
        # Ensures field exists
        _ = self.get_field(field_name)

        super().clear_field(field_name)

    def to_dict(self):
        d = super().to_dict()

        if self._selected_fields or self._excluded_fields:
            d = {k: v for k, v in d.items() if k in self.field_names}

        return d

    def to_mongo_dict(self):
        d = super().to_mongo_dict()

        if self._selected_fields or self._excluded_fields:
            d = {k: v for k, v in d.items() if k in self.field_names}

        return d

    def copy(self, fields=None, omit_fields=None):
        fields = self._parse_fields(fields=fields, omit_fields=omit_fields)
        return self._DOCUMENT_CLS(
            **{field: deepcopy(self[field]) for field in fields}
        )

    def save(self):
        self._doc.save(filtered_fields=self._filtered_fields)

        if issubclass(type(self._DOCUMENT_CLS), DocumentSingleton):
            self._DOCUMENT_CLS._reload_instance(self)


def _merge_labels(labels, new_labels, overwrite=True):
    if overwrite:
        existing_ids = {l.id: idx for idx, l in enumerate(labels)}
        for l in new_labels:
            idx = existing_ids.get(l.id, None)
            if idx is not None:
                labels[idx] = l
            else:
                labels.append(l)
    else:
        existing_ids = set(l.id for l in labels)
        labels.extend(l for l in new_labels if l.id not in existing_ids)
