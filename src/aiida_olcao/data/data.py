"""Data types for the ``aiida-olcao`` plugin.

For OLCAO you typically need a (sometimes large) set of input parameters.
Storing these parameters as an AiiDA data node makes them:

- queryable (you can search by parameter values)
- fully provenance-tracked (parameters become part of the provenance graph)
- easy to reuse across calculations/workflows

This module currently defines :class:`~aiida_olcao.data.OlcaoParameters`, a thin
wrapper around :class:`aiida.orm.Dict`.

As we learn the OLCAO input format better, we can add more validation here
(e.g. enforcing allowed keys/values, normalising units, etc.).
"""

from __future__ import annotations

from aiida import orm


class OlcaoParameters(orm.Dict):
    """AiiDA data node for OLCAO input parameters.

    Notes
    -----
    - This class intentionally performs only minimal validation.
    - If you prefer a stricter schema, we can extend ``validate`` and/or add
      a pydantic model later.
    """

    def validate(self):  # type: ignore[override]
        """Validate the parameters stored in this node.

        Raises
        ------
        :class:`aiida.common.exceptions.ValidationError`
            If the stored data is not a dictionary.
        """
        super().validate()

        params = self.get_dict()
        if not isinstance(params, dict):
            # This should never happen (orm.Dict enforces it), but keep the
            # check here because users may subclass/mutate in odd ways.
            from aiida.common.exceptions import ValidationError

            raise ValidationError('OlcaoParameters must contain a dictionary.')

