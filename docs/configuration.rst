Configuration
=============

Before using ``python_magnetapi``, you need to configure access to a running
MagnetDB instance.

MagnetDB Server
---------------

Add the following entries to ``/etc/hosts`` with the IP address of your MagnetDB
server:

.. code-block:: text

   aa.bb.xx.yy magnetdb.local
   aa.bb.xx.yy api.magnetdb.local
   aa.bb.xx.yy lemon.magnetdb.local
   aa.bb.xx.yy manager.lemon.magnetdb.local
   aa.bb.xx.yy auth.lemon.magnetdb.local
   aa.bb.xx.yy pgadmin.magnetdb.local
   aa.bb.xx.yy minio.magnetdb.local
   aa.bb.xx.yy traefik.magnetdb.local

Replace ``aa.bb.xx.yy`` with the actual IP address of the MagnetDB host.


CA Certificate
--------------

If the MagnetDB server uses HTTPS with a self-signed certificate, retrieve and
install the server certificate:

.. code-block:: bash

   # Retrieve the certificate
   echo | openssl s_client -servername magnetdb.local \
     -connect magnetdb.local:443 | cat > magnetdb.crt

   # Install it system-wide
   sudo cp magnetdb.crt /usr/local/share/ca-certificates/
   sudo update-ca-certificates


API Key
-------

Obtain your API key from your profile page on ``magnetdb.local`` and export it
as an environment variable:

.. code-block:: bash

   export MAGNETDB_API_KEY=your_api_key_here

You can also add this to your shell profile (e.g. ``~/.bashrc``) for
persistence.


Environment Variables
---------------------

The following environment variables are recognized:

.. list-table::
   :header-rows: 1
   :widths: 30 50 20

   * - Variable
     - Description
     - Default
   * - ``MAGNETDB_API_KEY``
     - API key for authenticating with MagnetDB
     - *(none)*
   * - ``MAGNETDB_API_SERVER``
     - API server hostname
     - ``api.magnetdb-dev.local``
