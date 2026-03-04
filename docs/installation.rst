Installation
============

Requirements
------------

- Python >= 3.11
- A running MagnetDB instance

The package depends on the following Python packages:

- ``requests`` >= 2.32.3
- ``pandas`` >= 2.2.1
- ``numpy`` >= 2.2.1
- ``scipy`` >= 1.14.1
- ``param`` >= 1.12.0
- ``rich`` >= 9.11.0
- ``python-magnetsetup``

Python Virtual Environment (recommended for development)
---------------------------------------------------------

Clone the repository and install in a virtual environment:

.. code-block:: bash

   git clone https://github.com/Trophime/python_magnetapi.git
   cd python_magnetapi

   # Create and activate a virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install in editable mode with dev dependencies
   pip install -e ".[dev]"

A helper script ``start-venv.sh`` is also provided. It creates a virtual
environment with ``--system-site-packages`` enabled (useful when system-level
dependencies like ``python3-magnetsetup`` are installed via apt):

.. code-block:: bash

   ./start-venv.sh
   source venv/bin/activate

Using ``uv`` instead of pip:

.. code-block:: bash

   uv venv venv
   source venv/bin/activate
   uv pip install -e ".[dev]"


Debian Packaging
----------------

Installing from the LNCMI Debian repository
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the package is available in the LNCMI Debian repository:

.. code-block:: bash

   sudo apt update
   sudo apt install python3-magnetapi

Building the Debian package locally
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Install required build tools and dependencies:

.. code-block:: bash

   sudo apt install debhelper dh-python python3-all python3-setuptools \
                    devscripts build-essential
   sudo apt install python3-magnetrun python3-magnetsetup python3-rich

Build the package:

.. code-block:: bash

   # Using the archive script (recommended)
   ./archive.sh -v 0.1.0 -d trixie

   # Or manually
   dpkg-buildpackage -us -uc -b

Install the resulting ``.deb`` file:

.. code-block:: bash

   sudo dpkg -i ../python3-magnetapi_0.1.0-1_all.deb
   sudo apt install -f  # Fix any missing dependencies


Docker / DevContainer
---------------------

A DevContainer configuration is provided in ``.devcontainer/`` for use with
VS Code or any OCI-compatible runtime.

Building the Docker image:

.. code-block:: bash

   docker build -f .devcontainer/Dockerfile -t magnetapi:latest .

Running the container:

.. code-block:: bash

   docker run -it --net host \
     -e MAGNETDB_API_KEY=${MAGNETDB_API_KEY} \
     magnetapi:latest

For VS Code users, open the project folder and select **"Reopen in Container"**
when prompted. The DevContainer automatically builds the image, installs all
dependencies (including ``python3-magnetrun``, ``python3-magnetsetup``, and
``python3-rich`` from the LNCMI Debian repository), and configures Python
tooling.


Singularity / Apptainer
------------------------

Convert the Docker image to a Singularity/Apptainer container (useful for HPC
environments):

.. code-block:: bash

   # Build from the local Docker image
   singularity build magnetapi.sif docker-daemon://magnetapi:latest

   # Or with Apptainer
   apptainer build magnetapi.sif docker-daemon://magnetapi:latest

Run the container:

.. code-block:: bash

   singularity exec magnetapi.sif python -m python_magnetapi.cli --help


Optional Dependencies
---------------------

For development and testing:

.. code-block:: bash

   pip install -e ".[dev]"

This installs ``pytest`` and ``pytest-cov``.

For building the documentation:

.. code-block:: bash

   pip install -e ".[doc]"

This installs ``sphinx`` and ``sphinx-rtd-theme``.
