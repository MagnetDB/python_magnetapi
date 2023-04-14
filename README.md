# Usage

## Pre-requisites

Add the following machines in /etc/hosts with IP of MagnetDB

# MagnetDB

```
147.173.xx.yy handler.sso.lncmig.local api.manager.sso.lncmig.local manager.sso.lncmig.local sso.lncmig.local test.sso.grenoble.lncmi
147.173.xx.yy magnetdb.lncmig.local
147.173.xx.yy magnetdb-api.lncmig.local
147.173.xx.yy magnetdb-worker.lncmig.local
147.173.xx.yy redis.lncmig.local
147.173.xx.yy postgres.lncmig.local
147.173.xx.yy pgadmin.lncmig.local
147.173.xx.yy minio.lncmig.local
147.173.xx.yy minio-storage.lncmig.local
```

## Running the examples

You can find your API key in your profile page.

```bash
export MAGNETDB_API_KEY=xxx
python -m python_magnetapi.cli --help
python -m python_magnetapi.cli list --mtype material
python -m python_magnetapi.cli view --mtype material --name testmat2
python -m python_magnetapi.cli create --mtype material --data '{"name": "tutu"}'
python -m python_magnetapi.cli create --mtype material --file data.json
python -m python_magnetapi.cli delete --mtype material --name testmat2
python -m python_magnetapi.cli compute --mtype magnet  --name M19061901 --flow_params
python -m python_magnetapi.cli compute  --mtype part --name H15101601--hoop_stress
python -m python_magnetapi.cli run --mtype site --name M10_M19020601 --setup --method cfpdes --static --geometry Axi --model thelec --cooling mean --current 31000 12000 100
```

## Running the test suite

```bash
export MAGNETDB_API_KEY=xxx
pytest-3 --verbose
```

