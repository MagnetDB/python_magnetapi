# Usage

## Pre-requisites

Add the following machines in /etc/hosts with IP of magnetdb

# MagnetDB
147.173.xx.yy handler.sso.grenoble.lncmi.local api.manager.sso.grenoble.lncmi.local manager.sso.grenoble.lncmi.local sso.grenoble.lncmi.local test.sso.grenoble.lncmi
147.173.xx.yy magnetdb.grenoble.lncmi.local
147.173.xx.yy magnetdb-api.grenoble.lncmi.local
147.173.xx.yy magnetdb-worker.grenoble.lncmi.local
147.173.xx.yy redis.grenoble.lncmi.local
147.173.xx.yy postgres.grenoble.lncmi.local
147.173.xx.yy pgadmin.grenoble.lncmi.local
147.173.xx.yy minio.grenoble.lncmi.local
147.173.xx.yy minio-storage.grenoble.lncmi.local


## Running the examples

You can find your API key in your profile page.

```bash
export MAGNETDB_API_KEY=xxx
python -m python_magnetapi.cli --help
python -m python_magnetapi.cli --name M19061901 compute --flow_params
python -m python_magnetapi.cli --mtype part --name H15101601 compute --hoop_stress
```

