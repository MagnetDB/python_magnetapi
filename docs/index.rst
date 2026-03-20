.. python_magnetapi documentation master file

python_magnetapi
================

**Python CLI and library for interacting with MagnetDB** — a database for magnetic
materials, parts, magnets, and sites used in high-field magnet research.

``python_magnetapi`` provides utilities to:

- List, view, create, and delete objects (materials, parts, magnets, sites, records, servers, simulations)
- Set up and run simulations (cfpdes, CRB, HDG, etc.)
- Compute derived quantities (inductances, flow parameters, hoop stress)
- Post-process simulation results

.. note::

   This package requires a running `MagnetDB <https://github.com/Trophime/magnetdb>`_ instance
   and a valid API key to operate.

Getting Started
---------------

.. toctree::
   :maxdepth: 2

   installation
   quickstart
   configuration

User Guide
----------

.. toctree::
   :maxdepth: 2

   cli
   usage

API Reference
-------------

.. toctree::
   :maxdepth: 2

   api/index

Development
-----------

.. toctree::
   :maxdepth: 2

   testing
   contributing

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
