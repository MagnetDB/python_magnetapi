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
from python_magnetrun.MagnetRun import MagnetRun

import MagnetTools.Bmap as bmap
import MagnetTools.MagnetTools as mt

def compute(api_server: str, headers: dict, oid: int, mtype: str='part', verbose: bool=False, debug: bool=False):
    """
    compute hoop stress for a given part
    """
    if mtype != 'part':
        print(f'hoop_stress.compute: expect a part - got a {mtype}')
        return None

    part = utils.getobject(f"{api_server}", headers=headers, mtype='part', id=oid, verbose=verbose, debug=debug)
    part_type = part['type']
    if part['type'] == 'helix':
        mpart = 'H'
    elif part['type'] == 'bitter':
        mpart = "B"
    elif part['type'] == 'supra':
        mpart = "S"
    else:
        print(f"hoop_stress.compute: expect a part of type (helix|bitter|supra) - got a {part_type} for part={part['name']}")
        return None
        
    # download geofile
    attach = f['attachment_id']
    filename = utils.download(api_server, headers, attach, debug)

    # get r from geofile
    # load filename
    # r =

    print(f'hoop_stress.compute: api_server={api_server}, mtype={mtype}, id={oid}, name={part['name']')
    cwd = os.getcwd()
    print(f'cwd={cwd}')

    records = utils.gethistory(api_server, headers, oid, mtype, debug)
    if debug:
        print(f'records: {records}')

    with tempfile.TemporaryDirectory() as tempdir:
        os.chdir(tempdir)
        print(f'moving to {tempdir}')

        total = 0
        nrecords = len(records)
        for i in track(range(nrecords), description=f"Processing records for part id={id}..."):
            f = records[i]

            # get site
            site_id = f['site']
            site = utils.getobject(f"{api_server}", headers=headers, mtype='site', id=site_id, verbose=verbose, debug=debug)
            print(f'site: {site}')

            # how to now wether part is in Tubes|BMagnets|UMagnets
            # mimic python_magnetdb/actions/generate_simulation_config.py: generate_site_config(site_id)
            site_data = {'name': site['name'], 'magnets': []}
            for magnet in site['magnets']:
                magnet_data = {} 
                site_data['magnets'].append(magnet_data)

            # get index of part in magnet def
            
            
            # create datastruct for Hoop calc
            (Tubes, Helices, OHelices, BMagnets, UMagnets, Shims) = site_data
            icurrents = mt.get_currents(Tubes, Helices, BMagnets, UMagnets)
            
            # get record data
            attach = f['attachment_id']
            filename = utils.download(api_server, headers, attach, debug)
            housing = filename.split('_')
            if filename.endswith(".txt"):
                rundata = MagnetRun.fromtxt(housing, site['name'], filename)
            else:
                rundata = MagnetRun.fromcsv(housing, site['name'], filename)
            total += 1

            # extract timestamp, currents from rundata
            df = rundata.MagnetData.Data['timestamp', 'Field', 'IH', 'IB']
            Currents_val = df[['IH'] + 'IB']
            for values in Currents_val:
                print(f'values={values}')
                
                # # update Ih, Ib, Is range
                # vcurrents = list(icurrents)
                # num = 0
                # if len(Tubes) != 0: vcurrents[num] = values[num]; num += 1
                # if len(BMagnets) != 0: vcurrents[num] = values[num]; num += 1
                # if len(UMagnets) != 0: vcurrents[num] = values[num]; num += 1

                # currents = mt.DoubleVector(vcurrents)
                # mt.set_currents(Tubes, Helices, BMagnets, UMagnets, OHelices, currents)

                # if part is Helix: part -> Tube
                # n_elem = Tube.get_n_elem()
                # mid_elem = int(n_elem / 2) if (n_elem % 2) == 0 else int((n_elem+1) / 2)
                # j = Helices[mid_elem+Magnet.get_index()].get_CurrentDensity()
                # if part is Bitter: part -> which stack 
                # stacks = mt.create_Bstack(Magnets)
                # for i,stack in enumerate(stacks):
                #     rint = Magnets[stack[0]].get_R_int()
                #     mid_stack = 0
                #     for n in stack:
                #         mid_stack = int(n / 2) if (n % 2) == 0 else int((n+1) / 2)
                #     j = Magnets[mid_stack].get_CurrentDensity()
                # if part is Supra: part -> which stack 
                # stacks = mt.create_Bstack(Magnets)
                # for i,stack in enumerate(stacks):
                #     rint = Magnets[stack[0]].get_R_int()
                #     mid_stack = 0
                #     for n in stack:
                #         mid_stack = int(n / 2) if (n % 2) == 0 else int((n+1) / 2)
                #     j = Magnets[mid_stack].get_CurrentDensity()
                # 
                # bz = bmap.getBz(r, 0, Tubes, Helices, BMagnets, UMagnets)

                # df['Hoopstress'] = r * j * bz
            
        print(f"Processed {total} records.")
        os.chdir(cwd)
