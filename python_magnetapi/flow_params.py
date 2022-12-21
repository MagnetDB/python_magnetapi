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

    records = utils.gethistory(api_server, headers, oid, mtype, debug)
    if debug:
        print(f'records: {records}')

    with tempfile.TemporaryDirectory() as tempdir:
        os.chdir(tempdir)
        print(f'moving to {tempdir}')

        for key in fit_data:
            fit_data[key]['rlist'] = [record for record in records if key in record['name']]

            # download files
            files = []
            total = 0
            nrecors = len(fit_data[key]['rlist'])
            for i in track(range(nrecors), description=f"Processing records for {key}..."):
                f = fit_data[key]['rlist'][i]
                # print(f'f={f}')
                # id = f['id']
                # data = utils.getobject(api_server, headers, id=id, mtype='record', debug=debug)

                attach = f['attachment_id']
                files.append(utils.download(api_server, headers, attach, debug))
                total += 1
            print(f"Processed {total} records.")

            # get keys to be extracted
            df = pd.read_csv(files[0], sep='\s+', engine='python', skiprows=1)
            Ikey = "tttt"
            if not Get_Ikey:
                # get first Icoil column (not necessary Icoil1)
                keys = df.columns.values.tolist()

                # key firs header that match Icoil\d+
                for _key in keys:
                    _found = re.match("Icoil\d+", _key)
                    if _found:
                        Ikey = _found.group()
                        print(f"Ikey={Ikey}")
                        Get_Ikey = True
                        break

            plot_files(files, key1=Ikey ,key2=fit_data[key]['Rpm'], show=debug, debug=debug)
            df = concat_files(files, keys=[Ikey, fit_data[key]['Rpm']], show=debug, debug=debug)
            pairs = [f"{Ikey}-{fit_data[key]['Rpm']}"]

            def vpump_func(x, a: float, b: float):
                return a * (x/Imax)**2 + b

            df.replace([np.inf, -np.inf], np.nan, inplace=True)
            df.dropna(inplace=True)

            # # drop values for Icoil1 > Imax
            result = df.query(f'{Ikey} <= {Imax}') #, inplace=True)
            if result is not None:
                print(f'df: nrows={df.shape[0]}, results: nrows={result.shape[0]}')

            x_data = result[f'{Ikey}'].to_numpy()
            y_data = result[fit_data[key]['Rpm']].to_numpy()
            params, params_covariance = optimize.curve_fit(vpump_func, x_data, y_data) #, p0=[flow_params['Vp0']['value'], flow_params['Vpmax']['value'] = params[1]])
            print(f'result params: {params}')
            print(f'result covariance: {params_covariance}')
            print(f'result stderr: {np.sqrt(np.diag(params_covariance))}')
            flow_params['Vp0']['value'] = params[0]
            flow_params['Vpmax']['value'] = params[1]

            # save flow_params
            filename = f"{cwd}/flow_params.json"
            with open(filename, 'w') as f:
                f.write(json.dumps(flow_params, indent=4))

        os.chdir(cwd)
