"""Data types for the :mod:`aiida_olcao` plugin.

Right now, the plugin only defines :class:`~aiida_olcao.data.OlcaoParameters`, a
light wrapper around :class:`aiida.orm.Dict` used to store OLCAO parameters.
"""

from .data import OlcaoParameters

__all__ = ("OlcaoParameters",)
