"""Data reading modules"""

from abc import ABCMeta, abstractmethod
from datetime import datetime
import codecs
import csv
import pandas as pd
from user_agents import parse


class DataReader:
    """Sequential data reader with ability to specify
    it's own row parsing funtion."""

    __metaclass__ = ABCMeta

    def __init__(self, data_path):
        """Create data reader for IPinYou RTB dataset.

        Parameters
        ----------
        data_path : str
            Path to data file.

        row_transformers : list of func
            Functions that parse row of data and return feature array.
            Each transformer will be applied sequentially like t3(t2(t1(row)))

        post_processor : func
            Post processing function that takes transformed data list as input
        """

        self.data_path = data_path

    def read_data(self, limit=None, verbose=False):
        """Read data from files and perform row transformations and post processing

        Parameters
        ----------
        limit : int
            Limit data loading to `limit` lines
        verbose : bool
            Print progress
            """
        with codecs.open(self.data_path,
                         'r', encoding='utf-8',
                         errors='ignore') as data_file:
            reader = csv.reader(data_file, delimiter='\t')
            result = []

            for i, row in enumerate(reader):
                if limit is not None:
                    if i > limit:
                        break

                    if i % 10000 == 0 and verbose:
                        load_percent = i / limit
                        print("%.2f" % load_percent)

                try:
                    transformed_row = self._row_transformer(row)
                    result.append(transformed_row)
                except Exception as e:
                    print("Error transforming row %d: %s" % (i, str(e)))

        result = self._post_processor(result)
        return result

    @abstractmethod
    def _row_transformer(self, row):
        """Transform data row.

        Returns
        -------
        row
            Transformed row.
        """
        pass

    @abstractmethod
    def _post_processor(self, data):
        """Perform data post processing.

        Returns
        -------
        result
            Post processed data.
        """
        pass


class ImpressionsReader(DataReader):
    """IPinYou RTB impressions Dataset loader.
    Expecting data from 2 or 3 competition (with additional columns)
    """

    def _row_transformer(self, row):
        entry = {'bid_id': row[0],
                 'timestamp': row[1],
                 'log_type': row[2],
                 'ipinyou_id': row[3],
                 'user_agent': row[4],
                 'ip_address': row[5],
                 'region_id': row[6],
                 'city_id': row[7],
                 'ad_exchange': row[8],
                 'domain': row[9],
                 'url': row[10],
                 'anonymous_url_id': row[11],
                 'ad_slot_id': row[12],
                 'ad_slot_width': row[13],
                 'ad_slot_height': row[14],
                 'ad_slot_visibility': row[15],
                 'ad_slot': row[16],
                 'ad_slot_floor_price': row[17],
                 'creative_id': row[18],
                 'bidding_price': row[19],
                 'paying_price': row[20],
                 'key_page_url': row[21],
                 'advertiser_id': row[22],
                 'user_tags': row[23]}

        entry['user_tags'] = [int(tag) for tag in entry['user_tags'].split(
            ',')] if entry['user_tags'] != 'null' else None
        entry['timestamp'] = datetime.strptime(
            entry['timestamp'][:-3], '%Y%m%d%H%M%S')

        return entry

    def _post_processor(self, data):
        user_tag_col_cache = set()

        for row in data:
            # parse user agent
            user_agent = parse(row['user_agent'])
            row['os'] = user_agent.os.family
            row['browser'] = user_agent.browser.family
            row['device'] = user_agent.device.family

            # vectorize user tags (one-hot)
            tags = row['user_tags']

            if tags is not None:
                for t in tags:
                    col_name = "user_tag_%d" % t
                    user_tag_col_cache.add(col_name)

                    row[col_name] = 1

        df = pd.DataFrame(data)
        df.drop('user_tags', inplace=True, axis=1)
        df[list(user_tag_col_cache)] = df[list(user_tag_col_cache)].fillna(
            0)  # fill not present tags with 0 for each user

        # convert numeric columns from object to numeric dtypes
        convert_to_nums = ['ad_slot_floor_price',
                           'ad_slot_height',
                           'ad_slot_width',
                           'advertiser_id',
                           'bidding_price',
                           'log_type',
                           'paying_price',
                           'city_id',
                           'creative_id']

        for col in convert_to_nums:
            df[col] = pd.to_numeric(df[col])

        return df


class ClicksReader(DataReader):
    """IPinYou RTB clicks dataset loader.
    Expecting data from 2 or 3 competition (with additional columns)"""

    def _row_transformer(self, row):
        entry = {'bid_id': row[0],
                 'timestamp': row[1],
                 'ipinyou_id': row[3]}

        entry['timestamp'] = datetime.strptime(
            entry['timestamp'][:-3], '%Y%m%d%H%M%S')

        return entry

    def _post_processor(self, data):
        df = pd.DataFrame(data)
        return df
