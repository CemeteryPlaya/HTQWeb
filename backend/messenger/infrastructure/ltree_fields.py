"""
LTreeField — PostgreSQL ltree with SQLite fallback.

In PostgreSQL: Uses the `ltree` extension with GiST index for O(1) ancestor
queries like ``WHERE department_path <@ 'Global.Engineering'``.

In SQLite (development): Falls back to a plain CharField with LIKE-based
queries for hierarchy traversal. Functional but slower — acceptable for dev.
"""

from django.db import connection, models


def _is_postgres() -> bool:
    """Check if the current database backend is PostgreSQL."""
    return connection.vendor == 'postgresql'


class LTreeField(models.CharField):
    """
    Materialized-path field for hierarchical data.

    Stores paths like ``Global.Engineering.Backend``.

    PostgreSQL:
        - Backed by ``ltree`` column type
        - Supports ``<@`` (is descendant of), ``@>`` (is ancestor of),
          ``~`` (regex match), ``?`` (match any) operators
        - Requires ``CREATE EXTENSION IF NOT EXISTS ltree`` (handled by migration)

    SQLite:
        - Stored as VARCHAR — queries use ``path LIKE 'prefix.%'`` fallback
    """

    description = "Materialized path (ltree in PostgreSQL, CharField in SQLite)"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 1024)
        kwargs.setdefault('blank', True)
        kwargs.setdefault('default', '')
        kwargs.setdefault('db_index', True)
        super().__init__(*args, **kwargs)

    def db_type(self, connection):
        if connection.vendor == 'postgresql':
            return 'ltree'
        return super().db_type(connection)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return ''
        return str(value)

    def get_prep_value(self, value):
        if value is None:
            return ''
        # Sanitize: ltree paths use dots, no spaces
        return str(value).strip()


class LTreeDescendantLookup(models.Lookup):
    """
    Custom lookup: ``field__descendant_of='Global.Engineering'``

    PostgreSQL: ``field <@ 'Global.Engineering'``
    SQLite:     ``field LIKE 'Global.Engineering.%' OR field = 'Global.Engineering'``
    """
    lookup_name = 'descendant_of'

    def as_postgresql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        return f'{lhs} <@ {rhs}', lhs_params + rhs_params

    def as_sql(self, compiler, connection):
        if connection.vendor == 'postgresql':
            return self.as_postgresql(compiler, connection)
        # SQLite fallback
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        return (
            f'({lhs} LIKE {rhs} || ".%%" OR {lhs} = {rhs})',
            lhs_params + rhs_params + rhs_params,
        )


class LTreeAncestorLookup(models.Lookup):
    """
    Custom lookup: ``field__ancestor_of='Global.Engineering.Backend'``

    PostgreSQL: ``field @> 'Global.Engineering.Backend'``
    SQLite:     ``'Global.Engineering.Backend' LIKE field || '.%'``
    """
    lookup_name = 'ancestor_of'

    def as_postgresql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        return f'{lhs} @> {rhs}', lhs_params + rhs_params

    def as_sql(self, compiler, connection):
        if connection.vendor == 'postgresql':
            return self.as_postgresql(compiler, connection)
        # SQLite fallback
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        return (
            f'({rhs} LIKE {lhs} || ".%%" OR {rhs} = {lhs})',
            rhs_params + lhs_params + rhs_params,
        )


# Register custom lookups on the field
LTreeField.register_lookup(LTreeDescendantLookup)
LTreeField.register_lookup(LTreeAncestorLookup)
