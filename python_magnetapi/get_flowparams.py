import os
import sys
import datetime
from datetime import timezone
from datetime import datetime
from time import sleep

import requests
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("names", help="magnet names (ex. M19061901)", nargs='+', metavar='MagnetNames', type=str, default="M19061901")
parser.add_argument("--show", help="display graphs (default save in png format)", action='store_true')
parser.add_argument("--debug", help="activate debug", action='store_true')
args = parser.parse_args()

print(f'args: {args}')

api_server = os.getenv('MAGNETDB_API_SERVER') or "http://magnetdb-api.grenoble.lncmi.local"

for magnet_name in args.names:
    print(f'looking for: {magnet_name}')

    r = requests.get(
        f"{api_server}:8000/api/magnets",
        headers={'Authorization': os.getenv('MAGNETDB_API_KEY')}
    )

    result_list = r.json()['items']
    for magnet in result_list:
        print(f"MAGNET: {magnet['name']} (status:{magnet['status']}, id:{magnet['id']})")
        if magnet['name'] == magnet_name:
            found = True
            break

    if not found:
        print(f"magnet: {magnet_name} not found in magnetdb ({api_server})")
        print(f"available magnets: {[magnet['name'] for magnet in result_list]}")
        sys.exit(1)

    r = requests.get(
        f"{api_server}:8000/api/magnets/{magnet['id']}",
        headers={'Authorization': os.getenv('MAGNETDB_API_KEY')}
    )

    # print(f'result={r.json()}, type={type(r.json())}')
    list_records = []
    magnet_data = r.json()
    for site in magnet_data['site_magnets']:
        # print(f"site={site}, id={site['site_id']}")
        site_result = requests.get(
            f"{api_server}:8000/api/sites/{site['site_id']}",
            headers={'Authorization': os.getenv('MAGNETDB_API_KEY')}
        )
        site_data = site_result.json()
        #print(f'site_data={r.json()}, type={type(r.json())}')
    
        print(f"site={site_data['name']}, status={site_data['status']}, records:")
        for record in site_data['records']:
            # list_records.append(record['id'])
            # temporary hack
            # for a better solution see download_ ex
            # work in temporary dir
            rname = record['name']
            actual_site = rname.split('_')[0]
            list_records.append(f"../../python_magnetrun/{rname}")
            # get record file from S3
            # print(f"record={rname}, actual_site={actual_site}")

        flow_params = {
                "Vp0": { "value" : 1000, "unit": "rpm"},
                "Vpmax": { "value" : 2840, "unit": "rpm"},
                "F0": { "value" : 0, "unit": "l/s"},
                "Fmax": { "value" : 61.71612272405876 , "unit": "l/s"},
                "Pmax": { "value" : 22, "unit": "bar"},
                "Pmin": { "value" : 4, "unit": "bar"},
                "Imax": { "value" : 28000, "unit": "A"}
            }
        
        import pandas as pd
        from txt2csv import load_files, plot_key_vs_key

        # get records by actual site
        M9_records = [record for record in list_records if 'M9' in record]
        M10_records = [record for record in list_records if 'M10' in record]
        print(f'M9 records: {len(M9_records)} over {len(list_records)} records')
        print(f'M10 records: {len(M10_records)} over {len(list_records)} records')

        fit_data = {
            'M9': { 'Rpm': 'Rpm1', 'Flow': 'Flow1', 'rlist' : M9_records},
            'M10': { 'Rpm': 'Rpm2', 'Flow': 'Flow2', 'rlist' : M10_records},
        }

        Get_Ikey = False
        for key in fit_data:
            if fit_data[key]['rlist']:
                df = load_files(fit_data[key]['rlist'], show=args.debug, debug=args.debug)

                Ikey = "tttt"
                if not Get_Ikey:
                    # get first Icoil column (not necessary Icoil1)
                    keys = df.columns.values.tolist()
                
                    # key firs header that match Icoil\d+
                    import re
                    for _key in keys:
                        _found = re.match("Icoil\d+", _key)
                        if _found:
                            Ikey = _found.group()
                            print(f"Ikey={Ikey}")
                            Get_Ikey = True
                            break

                pairs = [f"{Ikey}-{fit_data[key]['Rpm']}"]
                # plot_key_vs_key(df, pairs, show=True)

                import matplotlib.pyplot as plt
                import numpy as np
                from scipy import optimize

                Imax = flow_params['Imax']['value'] # 28000
                def vpump_func(x, a, b):
                    return a * (x/Imax)**2 + b

                df.replace([np.inf, -np.inf], np.nan, inplace=True)
                df.dropna(inplace=True)

                # # drop values for Icoil1 > Imax
                result = df.query(f'{Ikey} <= 28000.') #, inplace=True)
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
        
                if args.show:
                    ax = plt.gca()
                    plt.xlabel('$I_h$ [A]')
                    plt.ylabel(f"{fit_data[key]['Rpm']} [rpm]")
                    plt.scatter(x_data, y_data, s=20, c='red')

                    x_data = np.sort(x_data)
                    plt.plot(x_data, vpump_func(x_data, params[0], params[1]), markevery=100, label='Fitted Vpump function')
                    plt.legend(loc='best')
                    plt.grid(visible=True)
                    plt.title(f"{key}: {magnet_name} {fit_data[key]['Rpm']} vs I (cropped)")
                    plt.show()

                    ax = plt.gca()
                    x_data = result[f'{Ikey}'].to_numpy()
                    y_data = result[fit_data[key]['Flow']].to_numpy()
                    plt.xlabel('$I_h$ [A]')
                    plt.ylabel(f"{fit_data[key]['Flow']} [l/s]")
                    plt.scatter(x_data, y_data, s=20, c='red')

                def flow_func(x, c, d):
                    vpmax = (params[0]+params[1])
                    return c * vpump_func(x, params[0], params[1])/ vpmax + d
                fparams, fparams_covariance = optimize.curve_fit(flow_func, x_data, y_data) #, p0=[flow_params['F0']['value'], flow_params['Fmax']['value']])
                print(f'result fparams: {fparams}')
                print(f'result fcovariance: {fparams_covariance}')
                print(f'result fstderr: {np.sqrt(np.diag(fparams_covariance))}')
                flow_params['F0']['value'] = fparams[0]
                flow_params['Fmax']['value'] = fparams[1]

                if args.show:
                    ax = plt.gca()
                    plt.xlabel('$I_h$ [A]')
                    plt.ylabel(f"{fit_data[key]['Flow']} [flow]")
                    plt.scatter(x_data, y_data, s=20, c='red')

                    x_data = np.sort(x_data)
                    plt.plot(x_data, flow_func(x_data, fparams[0], fparams[1]), markevery=100, label='Flow predicted')
                    plt.legend(loc='best')
                    plt.grid(visible=True)
                    plt.title(f"{key}: {magnet_name} {fit_data[key]['Flow']} vs I (cropped)")
                    plt.show()

                # save flow_params
                import json
                filename = f"{magnet_name}-{site_data['name']}-{key}-flow_params.json"
                with open(filename, 'w') as f:
                    f.write(json.dumps(flow_params, indent=4))
        
        
