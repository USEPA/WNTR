from abc import ABC, ABCMeta, abstractclassmethod
from dataclasses import dataclass
from typing import Iterable
from sqlalchemy import create_engine

import pandas as pd

class QueryService():
    def __init__(self, snowflake_username, 
            snowflake_password, 
            snowflake_account, 
            snowflake_database, 
            snowflake_schema, 
            snowflake_warehouse,
            snowflake_role) -> None:

        self.snowflake_username=snowflake_username
        self.snowflake_password=snowflake_password
        self.snowflake_account=snowflake_account
        self.snowflake_database=snowflake_database
        self.snowflake_schema=snowflake_schema
        self.snowflake_warehouse=snowflake_warehouse
        self.snowflake_role=snowflake_role

        # Create SQL engine
        self.engine = create_engine(
                'snowflake://{user}:{password}@{account}/{db}/{schema}?warehouse={warehouse}&role={role}'.format(
                    user=self.snowflake_username,
                    password=self.snowflake_password,
                    account=self.snowflake_account,
                    db=self.snowflake_database,
                    schema=self.snowflake_schema,
                    warehouse=self.snowflake_warehouse,
                    role=self.snowflake_role
                )
            )
        try:
            self.engine.connect()
            print('success')
        except:
            print('failure')

    def query_data(self, query, chunksize=5000000):
        print('Running query')
        data = pd.read_sql(query, self.engine)#, chunksize=chunksize)
        return data


class DataAquisitionService(ABC):
    def __init__(self, business_unit, 
            snowflake_username, 
            snowflake_password, 
            snowflake_account, 
            snowflake_database, 
            snowflake_schema, 
            snowflake_warehouse,
            snowflake_role) -> None:
        self._table = None
        self._query_service =  QueryService( 
                snowflake_username, 
                snowflake_password, 
                snowflake_account, 
                snowflake_database, 
                snowflake_schema, 
                snowflake_warehouse,
                snowflake_role
            )
        self._bu = business_unit

    @abstractclassmethod
    def _download_data(self, date_start, date_end, aux_data=None):
        date_start = pd.Timestamp(date_start)
        date_end = pd.Timestamp(date_end)
        return date_start.strftime('%Y%m%d'), date_end.strftime('%Y%m%d')

    def get(self, date_start, date_end, aux_data=None):
        data = self._download_data(date_start, date_end, aux_data)

        if type(data) == pd.DataFrame:
            return self._fix_data(data, aux_data)
        else: 
            self._get_generator(data, aux_data)

    def _get_generator(self, data, aux_data=None):
        for chunk in data:
            yield self._fix_data(chunk, aux_data)

    @abstractclassmethod
    def _fix_data(self, data_chunk, aux_data=None):
        raise NotImplementedError()


class SnowflakeAquisitionService(DataAquisitionService):
    def __init__(self, business_unit, 
            snowflake_username, 
            snowflake_password, 
            snowflake_account, 
            snowflake_database, 
            snowflake_schema, 
            snowflake_warehouse,
            snowflake_role) -> None:
        super().__init__(business_unit, 
            snowflake_username, 
            snowflake_password, 
            snowflake_account, 
            snowflake_database, 
            snowflake_schema, 
            snowflake_warehouse,
            snowflake_role)

    def _download_data(self, date_start, date_end, aux_data=None):
        date_start, date_end = super()._download_data(date_start, date_end)

        query = f'SELECT BUSINESS_UNIT_NAME,LOCATION_SERVICEPOINT,LOCATION_DMA,gallons_actual,TO_TIMESTAMP(CONCAT(date_id, \' \', hour_id, \':00:00\'), \'YYYYMMDD HH24:MI:SS\') as DATE_TIME,NODE_BADGE \n' +\
                    f'FROM EDW_PRD.DIM.D_USAGE_LOCATION LOC, \n' +\
                    f'  EDW_PRD.NRW.F_USAGE_BYHOUR USG, \n' +\
                    f'  EDW_PRD.DIM.D_BUSINESSUNIT BU, \n' +\
                    f'  EDW_PRD.DIM.D_USAGE_DATA_NODE DN\n'

        if aux_data is not None:
            if 'SPIDs' in aux_data:
                where_spids = f'LOC.LOCATION_SERVICEPOINT IN (' + ','.join(aux_data['SPIDs']) + ')\n  AND'
            elif 'DMAs' in aux_data:
                if type(aux_data) == str:
                    where_spids = f'LOC.LOCATION_DMA=\'' + aux_data['DMAs'] + '\'\n  AND'
                elif len(aux_data['DMAs']) == 1:
                    where_spids = f'LOC.LOCATION_DMA=\'' + aux_data['DMAs'][0] + '\'\n  AND'
                else:
                    where_spids = f'LOC.LOCATION_DMA IN (' + '\',\''.join(aux_data['DMAs']) + ')\n  AND'
        else:
            where_spids = ''

        query += f'WHERE {where_spids} usg.LOCATION_ID=LOC.LOCATION_ID \n' +\
                    f'  AND BU.BUSINESS_UNIT_REF_CODE=\'{self._bu}\' AND BU.SYSTEM_CATEGORY=\'CCB\'\n' +\
                    f'  AND usg.business_unit_id=BU.BUSINESS_UNIT_ID \n' +\
                    f'  AND usg.DATE_ID BETWEEN {date_start} AND {date_end} \n' +\
                    f'  AND DN.USAGE_DATA_NODE_ID=USG.USAGE_DATA_NODE_ID'
                    # f'  AND usg.business_unit_id={self._bu} \n' +\

        return self._query_service.query_data(query)

    def _fix_data(self, data_chunk, aux_data=None, test_plot=False):
        #TODO: DOWNSCALE NEPTUNE READINGS. INCREASE DATA TIME INTERVAL AND LOOK FOR VALUES THAT SHOW UP ONLY EVERY MONTH OR SO.
        print('Fixing data')

        badge_to_spid = data_chunk[['location_servicepoint', 'node_badge']].set_index('node_badge')
        data_chunk = data_chunk.pivot_table(index='date_time', columns='node_badge', values='gallons_actual')
        data_chunk = data_chunk[data_chunk.sum().sort_values().index]

        if test_plot:
            import matplotlib.pyplot as plt
            import seaborn as sns
            fig, ax = plt.subplots(figsize=(200, 10))
            sns.heatmap(data_chunk, annot=False, ax=ax, cmap='turbo')
            plt.tight_layout()
            plt.savefig('test.png')

        return data_chunk
