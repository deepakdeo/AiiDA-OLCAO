==========
Quickstart
==========

This quickstart runs the OLCAO plugin end-to-end using the repository's
``dummy_olcao.sh`` executable.

Install
+++++++

Install the plugin and create a profile if you have not already::

    pip install -e .
    verdi quicksetup

Set up a local code
+++++++++++++++++++

Make sure the dummy executable is runnable::

    chmod +x /path/to/aiida-olcao/dummy_olcao.sh

Create a local computer (skip if you already have ``localhost``)::

    verdi computer setup --non-interactive --label localhost --hostname localhost --transport core.local --scheduler core.direct --workdir /tmp/aiida-olcao
    verdi computer configure core.local localhost --safe-interval 0

Register a local code pointing to the dummy executable::

    verdi code create core.installed --label olcao-dummy --computer localhost --filepath-executable /path/to/aiida-olcao/dummy_olcao.sh --default-calc-job-plugin olcao

Run the example
+++++++++++++++

Run the hello-world example script::

    verdi run examples/example_01.py --code olcao-dummy@localhost

The script prints the ``output_parameters`` dictionary from the parser.
If you omit ``--code``, the script will create ``olcao-dummy@localhost`` for you.

Inspect outputs and provenance
++++++++++++++++++++++++++++++

List recent processes and inspect a run::

    verdi process list -a
    verdi process report <PK>

Show the parsed output parameters node::

    verdi node show <OUTPUT_PARAMETERS_PK>
