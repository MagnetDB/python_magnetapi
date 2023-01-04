"""
Extract flow params from records using a fit
"""


import tempfile
import os
import re

import numpy as np
from scipy import optimize

import json
import pandas as pd
from rich.progress import track
from . import utils

# from txt2csv import load_files
from python_magnetrun.utils.files import concat_files
from python_magnetrun.utils.plots import plot_files

def compute(api_server: str, headers: dict, oid: int, mtype: str='magnet', debug: bool=False):
    """
    compute flow_params for a given objet (magnet/site)
    """
    print(f'flow_params.compute: api_server={api_server}, mtype={mtype}, id={oid}')
    cwd = os.getcwd()
    print(f'cwd={cwd}')

    # default value
    flow_params = {
        "Vp0": { "value" : 1000, "unit": "rpm"},
        "Vpmax": { "value" : 2840, "unit": "rpm"},
        "F0": { "value" : 0, "unit": "l/s"},
        "Fmax": { "value" : 61.71612272405876 , "unit": "l/s"},
        "Pmax": { "value" : 22, "unit": "bar"},
        "Pmin": { "value" : 4, "unit": "bar"},
        "Imax": { "value" : 28000, "unit": "A"}
    }

    Imax = flow_params['Imax']['value'] # 28000

    fit_data = {
        'M9': { 'Rpm': 'Rpm1', 'Flow': 'Flow1', 'rlist' : []},
        'M10': { 'Rpm': 'Rpm2', 'Flow': 'Flow2', 'rlist' : []},
    }

    sites = utils.gethistory(api_server, headers, oid, mtype=mtype, otype='site', debug=debug)
    if debug:
        print(f'sites: {sites}')

    with tempfile.TemporaryDirectory() as tempdir:
        os.chdir(tempdir)
        print(f'moving to {tempdir}')

        for site in sites:
            # print(f"site: {site}, id={site['site_id']}")
            records = utils.gethistory(api_server, headers, site['site_id'], mtype='site', otype='record', verbose=debug, debug=debug)
            # print(f'records: {records}')
            
            # download files
            files = []
            total = 0
            nrecords = len(records)
            housing = None
            for i in track(range(nrecords), description=f"Processing records for site {site['site']['name']}..."):
                f = records[i]
                # print(f'f={f}')
                attach = f['attachment_id']
                filename = utils.download(api_server, headers, attach, verbose=debug, debug=debug)
                housing = filename.split('_')[0]
                files.append(filename)
                total += 1
                if i >= 10: break
            print(f"Processed {total} records.")

            if files:
                # get keys to be extracted
                df = pd.read_csv(files[0], sep='\s+', engine='python', skiprows=1)
                Ikey = "tttt"

                # get first Icoil column (not necessary Icoil1)
                keys = df.columns.values.tolist()

                # key firs header that match Icoil\d+
                for _key in keys:
                    _found = re.match("Icoil\d+", _key)
                    if _found:
                        Ikey = _found.group()
                        print(f"Ikey={Ikey}")
                        break

                plot_files(files, key1=Ikey ,key2=fit_data[housing]['Rpm'], show=debug, debug=debug)
                df = concat_files(files, keys=[Ikey, fit_data[housing]['Rpm']], debug=debug)
                pairs = [f"{Ikey}-{fit_data[housing]['Rpm']}"]

                def vpump_func(x, a: float, b: float):
                    return a * (x/Imax)**2 + b

                df.replace([np.inf, -np.inf], np.nan, inplace=True)
                df.dropna(inplace=True)

                # # drop values for Icoil1 > Imax
                result = df.query(f'{Ikey} <= {Imax}') #, inplace=True)
                if result is not None:
                    print(f'df: nrows={df.shape[0]}, results: nrows={result.shape[0]}')

                x_data = result[f'{Ikey}'].to_numpy()
                y_data = result[fit_data[housing]['Rpm']].to_numpy()
                params, params_covariance = optimize.curve_fit(vpump_func, x_data, y_data)
                print(f'result params: {params}')
                print(f'result covariance: {params_covariance}')
                print(f'result stderr: {np.sqrt(np.diag(params_covariance))}')
                flow_params['Vp0']['value'] = params[0]
                flow_params['Vpmax']['value'] = params[1]

                # save flow_params
                filename = f"{cwd}/{site['site']['name']}-flow_params.json"
                with open(filename, 'w') as f:
                    f.write(json.dumps(flow_params, indent=4))

        os.chdir(cwd)
