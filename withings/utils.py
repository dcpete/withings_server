from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import json
import tzlocal

from .datablock import DataBlock

def timestamp2est(timestamp):
    # Convert timestamp to UTC first
    utc_dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    # Convert to local timezone
    est_dt = utc_dt.astimezone(ZoneInfo(tzlocal.get_localzone_name()))

    return est_dt

def rawdata2dfs(rawdata):
    dfs = {}
    for block in rawdata:
        db = DataBlock(block)
        #db.interpolate_timestamps()

        if not db.sensor_name in dfs:
            columns = ['timestamp', 'id'] + [col for col in db.df.columns if col != 'timestamp' and col != 'id']
            dfs[db.sensor_name] = db.df[columns]
        else:
            df = dfs[db.sensor_name]
            dfs[db.sensor_name] = pd.concat([df, db.df], axis=0, ignore_index=True)

    return dfs

import os

def write2json(json_data, filepath, filename):
    path_and_filename = os.path.join(filepath, filename)
    with open(path_and_filename, 'w') as f:
        json.dump(json_data, f, indent=4)

def write2csv(df, filepath, filename):
    path_and_filename = os.path.join(filepath, filename)
    df.to_csv(path_and_filename, index=False) 