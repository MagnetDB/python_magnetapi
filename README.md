# Usage

# Pre-requisites

## MagnetDB

Add the following machines in /etc/hosts with IP of MagnetDB

```
aa.bb.xx.yy magnetdb.local
aa.bb.xx.yy api.magnetdb.local
aa.bb.xx.yy lemon.magnetdb.local
aa.bb.xx.yy manager.lemon.magnetdb.local 
aa.bb.xx.yy auth.lemon.magnetdb.local
aa.bb.xx.yy pgadmin.magnetdb.local
aa.bb.xx.yy minio.magnetdb.local
aa.bb.xx.yy traefik.magnetdb.local
```

## Add CA cert

Get the server certificate

```bash
echo | openssl s_client -servername magnetdb.local -connect magnetdb.local:443 | cat > magnetdb.crt
```

Then

```bash
sudo cp magnetdb.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```
   
# Running

## Examples

You can find your API key in your profile page on magnetdb.local.

```bash
export MAGNETDB_API_KEY=xxx
python -m python_magnetapi.cli --help
python -m python_magnetapi.cli --https list --mtype material
python -m python_magnetapi.cli --https view --mtype material --name testmat2
python -m python_magnetapi.cli --https create --mtype material --data '{"name": "tutu"}'
python -m python_magnetapi.cli --https create --mtype material --file data.json
python -m python_magnetapi.cli --https delete --mtype material --name testmat2
python -m python_magnetapi.cli --https compute --mtype magnet  --name M19061901 --flow_params
python -m python_magnetapi.cli --https compute  --mtype part --name H15101601--hoop_stress
python -m python_magnetapi.cli --https setup --mtype site --name M10_M19020601 \
   --method cfpdes --static --geometry Axi --model thelec --cooling mean --current 31000 12000 100 \
   [--wd path_to_store_setup]
python -m python_magnetapi.cli --https run --simu_id id [--wd path_to_store_results]
```

## Test suite

```bash
export MAGNETDB_API_KEY=xxx
pytest-3 --verbose
```

