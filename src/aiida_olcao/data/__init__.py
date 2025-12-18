"""Data types for the :mod:`aiida_olcao` plugin.

Right now, the plugin only defines :class:`~aiida_olcao.data.OlcaoParameters`, a
light wrapper around ``aiida.orm.nodes.data.dict.Dict`` used to store OLCAO parameters.
"""

from .data import OlcaoParameters

__all__ = ("OlcaoParameters",)
