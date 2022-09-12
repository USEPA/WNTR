from multiprocessing import freeze_support
from os.path import abspath, dirname, join

import pytest
import wntr
import geopandas as gpd
from wntr.network.model import DemandDataCenter, ServicePointGIS
from wntr.utils.constants import *
from credentials import *

testdir = dirname(abspath(str(__file__)))
test_network_dir = join(testdir, "networks_for_testing")
test_data_dir = join(testdir, "data_for_testing")
ex_datadir = join(testdir, "..", "..", "examples", "networks")

def test_get_online_data():
    ddc = DemandDataCenter(            
            '15720',
            username,
            password,
            'suezna.us-east-1',
            'ODS_PRD',
            'CDR',
            'LOAD_WH',
            'DATASCIENCE')
    data = ddc.update(None, '07/10/2022', '07/11/2022')
    
    assert data.shape == (48, 11155)
    assert data.iloc[20, -4] == 1309.091
    
    data = ddc.update(None, '07/10/2022', '07/11/2022', aux_data={'SPIDs': ['5204320971', '5335220250', '3931220924', '1835220106', '6652220895']})
    
    assert data.shape == (48, 5)
    assert data.iloc[20, -4] == 1309.091

def test_clean_data():
    online_data_kwargs = {
        'business_unit': '055',
        'snowflake_username': username,
        'snowflake_password': password,
        'snowflake_account': 'suezna.us-east-1',
        'snowflake_database': 'ODS_PRD',
        'snowflake_schema': 'CDR',
        'snowflake_warehouse': 'LOAD_WH',
        'snowflake_role': 'DATASCIENCE'
    }
    demand_data_service = DemandDataCenter(**online_data_kwargs)
    data = demand_data_service.update(None, '05/01/2022', '08/31/2022', aux_data={'DMAs': ['H2']})

    i=0

if __name__ == '__main__':
    freeze_support()
    test_clean_data()