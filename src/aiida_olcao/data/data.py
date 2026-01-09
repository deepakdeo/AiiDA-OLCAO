"""Data types for the ``aiida-olcao`` plugin.

For OLCAO you typically need a (sometimes large) set of input parameters.
Storing these parameters as an AiiDA data node makes them:

- queryable (you can search by parameter values)
- fully provenance-tracked (parameters become part of the provenance graph)
- easy to reuse across calculations/workflows

This module defines :class:`~aiida_olcao.data.OlcaoParameters`, which validates
OLCAO calculation parameters and provides helper methods for generating
command-line arguments for ``makeinput`` and ``uolcao``.
"""

from __future__ import annotations

from aiida import orm
from aiida.common.exceptions import ValidationError

# Valid calculation types for uolcao
CALCULATION_TYPES = (
    "scf",  # SCF only
    "dos",  # Density of states
    "bond",  # Bond order analysis
    "sybd",  # Symmetric band structure
    "optc",  # Optical properties
    "pacs",  # X-ray absorption (XANES)
    "field",  # Charge density, potential
    "force",  # Atomic forces
    "nlop",  # Nonlinear optical
    "sige",  # Optical transitions near Fermi
    "loen",  # Local environment (bispectrum)
)

# Valid basis set options
BASIS_TYPES = ("EB", "FB", "MB")  # Extended, Full, Minimal

# Valid edge options for post-SCF calculations
EDGE_OPTIONS = (
    "gs",  # Ground state
    "1s",
    "2s",
    "2p",
    "3s",
    "3p",
    "3d",
    "4s",
    "4p",
    "4d",
    "4f",
    "5s",
    "5p",
    "5d",
    "5f",
    "6s",
    "6p",
    "6d",
    "7s",
)

# Default parameter values
DEFAULTS = {
    "kpoints": [1, 1, 1],
    "calculation_type": "scf",
    "basis_scf": "FB",
    "basis_pscf": "FB",
    "edge": "gs",
}


class OlcaoParameters(orm.Dict):
    """AiiDA data node for OLCAO input parameters with validation.

    Parameters
    ----------
    kpoints : list of int, optional
        K-point mesh [a, b, c] for both SCF and post-SCF. Default: [1, 1, 1]
    kpoints_scf : list of int, optional
        K-point mesh for SCF only (overrides kpoints for SCF stage)
    kpoints_pscf : list of int, optional
        K-point mesh for post-SCF only (overrides kpoints for post-SCF stage)
    calculation_type : str, optional
        Type of calculation: 'scf', 'dos', 'bond', 'sybd', 'optc', 'pacs',
        'field', 'force', 'nlop', 'sige', 'loen'. Default: 'scf'
    basis_scf : str, optional
        Basis set for SCF: 'EB', 'FB', 'MB'. Default: 'FB'
    basis_pscf : str, optional
        Basis set for post-SCF: 'EB', 'FB', 'MB'. Default: 'FB'
    edge : str, optional
        Edge for excited state calculations: 'gs', '1s', '2s', '2p', etc.
        Default: 'gs'

    Example
    -------
    >>> params = OlcaoParameters({
    ...     'kpoints': [5, 5, 5],
    ...     'calculation_type': 'dos',
    ...     'basis_scf': 'FB',
    ...     'basis_pscf': 'FB',
    ...     'edge': 'gs'
    ... })
    """

    def validate(self):
        """Validate the parameters stored in this node.

        Raises
        ------
        ValidationError
            If any parameter has an invalid type or value.
        """
        params = self.get_dict()
        if not isinstance(params, dict):
            raise ValidationError("OlcaoParameters must contain a dictionary.")

        # Validate kpoints (if provided)
        if "kpoints" in params:
            self._validate_kpoints(params["kpoints"], "kpoints")

        # Validate kpoints_scf (optional)
        if "kpoints_scf" in params:
            self._validate_kpoints(params["kpoints_scf"], "kpoints_scf")

        # Validate kpoints_pscf (optional)
        if "kpoints_pscf" in params:
            self._validate_kpoints(params["kpoints_pscf"], "kpoints_pscf")

        # Validate calculation_type
        if "calculation_type" in params:
            calc_type = params["calculation_type"]
            if not isinstance(calc_type, str):
                raise ValidationError(f"'calculation_type' must be a string, got {type(calc_type).__name__}")
            if calc_type not in CALCULATION_TYPES:
                raise ValidationError(
                    f"Invalid calculation_type '{calc_type}'. " f"Must be one of: {', '.join(CALCULATION_TYPES)}"
                )

        # Validate basis_scf
        if "basis_scf" in params:
            basis = params["basis_scf"]
            if not isinstance(basis, str):
                raise ValidationError(f"'basis_scf' must be a string, got {type(basis).__name__}")
            if basis not in BASIS_TYPES:
                raise ValidationError(f"Invalid basis_scf '{basis}'. Must be one of: {', '.join(BASIS_TYPES)}")

        # Validate basis_pscf
        if "basis_pscf" in params:
            basis = params["basis_pscf"]
            if not isinstance(basis, str):
                raise ValidationError(f"'basis_pscf' must be a string, got {type(basis).__name__}")
            if basis not in BASIS_TYPES:
                raise ValidationError(f"Invalid basis_pscf '{basis}'. Must be one of: {', '.join(BASIS_TYPES)}")

        # Validate edge
        if "edge" in params:
            edge = params["edge"]
            if not isinstance(edge, str):
                raise ValidationError(f"'edge' must be a string, got {type(edge).__name__}")
            if edge not in EDGE_OPTIONS:
                raise ValidationError(f"Invalid edge '{edge}'. Must be one of: {', '.join(EDGE_OPTIONS)}")

    @staticmethod
    def _validate_kpoints(kpoints, param_name: str) -> None:
        """Validate a k-points parameter.

        Parameters
        ----------
        kpoints : list
            The k-points value to validate.
        param_name : str
            Name of the parameter (for error messages).

        Raises
        ------
        ValidationError
            If kpoints is not a list of 3 positive integers.
        """
        if not isinstance(kpoints, (list, tuple)):
            raise ValidationError(
                f"'{param_name}' must be a list of 3 positive integers, " f"got {type(kpoints).__name__}"
            )
        if len(kpoints) != 3:
            raise ValidationError(f"'{param_name}' must have exactly 3 elements, got {len(kpoints)}")
        for i, val in enumerate(kpoints):
            if not isinstance(val, int) or isinstance(val, bool):
                raise ValidationError(f"'{param_name}[{i}]' must be an integer, got {type(val).__name__}")
            if val < 1:
                raise ValidationError(f"'{param_name}[{i}]' must be a positive integer, got {val}")

    def get_makeinput_cmdline(self) -> str:
        """Generate command-line arguments for makeinput.

        Returns
        -------
        str
            Command-line arguments string, e.g., '-kp 5 5 5' or
            '-scfkp 3 3 3 -pscfkp 7 7 7'.
        """
        params = self.get_dict()
        args = []

        # Check if we have separate SCF and PSCF k-points
        kpoints_scf = params.get("kpoints_scf")
        kpoints_pscf = params.get("kpoints_pscf")
        kpoints = params.get("kpoints", DEFAULTS["kpoints"])

        if kpoints_scf is not None or kpoints_pscf is not None:
            # Use separate k-point specifications
            scf_kp = kpoints_scf if kpoints_scf is not None else kpoints
            pscf_kp = kpoints_pscf if kpoints_pscf is not None else kpoints
            args.append(f"-scfkp {scf_kp[0]} {scf_kp[1]} {scf_kp[2]}")
            args.append(f"-pscfkp {pscf_kp[0]} {pscf_kp[1]} {pscf_kp[2]}")
        else:
            # Use unified k-points
            args.append(f"-kp {kpoints[0]} {kpoints[1]} {kpoints[2]}")

        return " ".join(args)

    def get_uolcao_cmdline(self) -> str:
        """Generate command-line arguments for uolcao.

        Returns
        -------
        str
            Command-line arguments string, e.g., '-dos' or '-scf FB -bond gs'.
        """
        params = self.get_dict()

        calc_type = params.get("calculation_type", DEFAULTS["calculation_type"])
        basis_scf = params.get("basis_scf", DEFAULTS["basis_scf"])
        edge = params.get("edge", DEFAULTS["edge"])

        if calc_type == "scf":
            # SCF-only calculation
            return f"-scf {basis_scf}"

        # Post-SCF calculations may need edge specification
        # Format: -<calc_type> [edge]
        if calc_type in ("pacs",):
            # PACS requires edge specification
            return f"-{calc_type} {edge}"

        if edge != "gs":
            # Non-ground-state edge specified
            return f"-{calc_type} {edge}"

        # Ground state, just the calculation type
        return f"-{calc_type}"
