import logging
import sys
import time
from fubon_neo.sdk import FubonSDK
import utils
import os
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
import warnings
import requests
from urllib3.exceptions import InsecureRequestWarning
import json

##
# Initialization
##
if 'initialized' not in st.session_state:
    st.session_state['initialized'] = True

    # Setup logging
    utils.mk_folder("log")
    LOGGER = utils.get_logger("Tiger", log_file="log/tigerdash.log", log_level=logging.DEBUG)
    st.session_state['logger'] = LOGGER


    def login(retry=0):
        global LOGGER, SDK, RestStock
        LOGGER.debug("login")

        if retry > 5:
            LOGGER.error(f"登入重試次數超過 5 次，請確定登入訊息，並重啟程式 ...")
            sys.exit(1)

        # Load .env
        load_dotenv()

        # Get credential data
        id = os.getenv("ID")
        trade_password = os.getenv("TRADEPASS")
        cert_filepath = os.getenv("CERTFILEPATH")
        cert_password = os.getenv("CERTPASSS")

        # Establish connection
        LOGGER.info("建立主機連線 ...")
        try:
            SDK = FubonSDK()
        except ValueError as e:
            LOGGER.error(f"無法連至API主機, error msg {e}")
            return False

        # Login
        LOGGER.info("登入帳號 ...")
        if cert_password:
            response = SDK.login(id, trade_password, cert_filepath, cert_password)
        else:
            response = SDK.login(id, trade_password, cert_filepath)

        if response.is_success:
            LOGGER.info("登入成功!")
            LOGGER.debug(f"可用帳號:\n{response.data}")

            return SDK
        else:
            LOGGER.info(f"登入失敗, message {response.message}, 5秒後重試 ...")
            time.sleep(5)
            return login(retry=retry + 1)


    def marketdata_connection():
        global LOGGER, SDK, RestStock
        LOGGER.debug("marketdata_connection")

        SDK.init_realtime()  # 建立行情連線
        RestStock = SDK.marketdata.rest_client.stock

        return RestStock


    SDK = login()
    RestStock = marketdata_connection()
    st.session_state['sdk'] = SDK
    st.session_state['reststock'] = RestStock

else:
    SDK = st.session_state.sdk
    RestStock = st.session_state.reststock
    LOGGER = st.session_state.logger


###
#    Functions
###
def renew_df():
    '''
    Renew the raw pandas df to be display on the dashboard
    :return: df or None (when failed)
    '''
    global LOGGER, SDK, RestStock

    try:
        # Get market snapshot from FubonNeo API
        market_snapshot_df = {}
        for market_type in ["TSE", "OTC"]:  # TSE - 上市; OTC - 上櫃
            market_snapshot_data = RestStock.snapshot.quotes(market=market_type)["data"]
            market_snapshot_df[market_type] = pd.DataFrame(market_snapshot_data)

        # Combine the two market snapshot dfs
        agg_market_snapshot_df = pd.concat(list(market_snapshot_df.values()),
                                           ignore_index=True
                                           )

        # Get 借券賣出可用餘額 data from mis.twse.com.tw
        with warnings.catch_warnings():
            # Sometimes the ssl certification check for mis.twse.com.tw fails for some unknown reasons, so here
            # we disable the check and mute the warning temporarily
            warnings.simplefilter('ignore', InsecureRequestWarning)
            # Make the request
            response = requests.get("https://mis.twse.com.tw/stock/api/getStockSblsCap.jsp", verify=False)
            #LOGGER.debug(f"request response code:\n{response.status_code}")

        if response.status_code != 200:
            LOGGER.error(f"擷取借券賣出可用餘額資訊失敗, status code: {response.status_code}")
            SBL_volume_df = None
        else:
            # Convert JSON string to Python dictionary
            data = json.loads(response.text)
            SBL_volume_df = pd.DataFrame(data["msgArray"])

        # Combine everything
        if SBL_volume_df is not None:
            df = pd.merge(SBL_volume_df,
                          agg_market_snapshot_df,
                          left_on='stkno',
                          right_on='symbol',
                          how='inner'
                          )
        else:
            df = None

    except Exception as e:
        LOGGER.error(f"renew_df exception: {e}")
        df = None

    finally:
        return df


def conditional_process_df(df, conds):
    '''
    :param df: The raw data df given by renew_df
    :param conds: Conditions (as dictionary) to filter the given df
    :return: Filtered df
    '''
    global LOGGER, SDK, RestStock

    try:
        new_df = df.copy()

        if st.session_state.filtering_conditions["apply_increase_threshold"]:
            # Condition 1: Filter rows where "changePercent" is non-negative and < increase_threshold
            condition1 = (new_df['changePercent'] <= conds["increase_threshold"])
            new_df = new_df[~condition1]  # Keep rows where condition1 is False

        if st.session_state.filtering_conditions["apply_decrease_threshold"]:
            # Condition 2: Filter rows where "changePercent" is negative and abs value < decrease_threshold
            condition2 = (new_df['changePercent'] >= -1 * conds["decrease_threshold"])
            new_df = new_df[~condition2]  # Keep rows where condition2 is False

        # Condition 3: Sort df according to column "tradeVolume" in descending order and keep top volume_threshold rows
        new_df = new_df.sort_values(by='tradeVolume', ascending=False).head(conds["volume_threshold"])

    except Exception as e:
        LOGGER.debug(f"conditional_process_df exception {e}")
        new_df = df

    finally:
        new_df = new_df[['slblimit', 'symbol', 'name', 'openPrice', 'highPrice', 'lowPrice', 'closePrice', 'changePercent',
                 'tradeVolume', 'tradeValue']]
        new_df.rename(columns={
            'slblimit': '借券賣出可用餘額',
            'symbol': '股號',
            'name': '股名',
            'openPrice': '開盤價',
            'highPrice': '最高價',
            'lowPrice': '最低價',
            'closePrice': '現價（收盤價）',
            'changePercent': '漲跌百分比',
            'tradeVolume': '交易量',
            'tradeValue': '交易金額'
        }, inplace=True)

        # Reordering columns
        new_df = new_df[['股號', '股名', '借券賣出可用餘額', '漲跌百分比', '交易量', '交易金額', '開盤價', '最高價', '最低價',
                 '現價（收盤價）']]

        return new_df


def update_checkbox(key_changed):
    if key_changed == 'apply_increase_threshold' and st.session_state['apply_increase_threshold']:
        st.session_state['apply_decrease_threshold'] = False
    elif key_changed == 'apply_decrease_threshold' and st.session_state['apply_decrease_threshold']:
        st.session_state['apply_increase_threshold'] = False


# Main logic
if __name__ == '__main__':
    # Streamlit App #######################
    st.set_page_config(layout="wide")  # Set the page configuration to wide mode
    input_col, df_col = st.columns([1, 3])  # Adjust the ratio as needed

    # Place input widgets in the input column
    with input_col:
        st.title('借券賣出可用餘額')
        st.subheader('篩選看盤範例')

        # Initialize the session states for the checkboxes if they do not exist
        if 'apply_increase_threshold' not in st.session_state:
            st.session_state['apply_increase_threshold'] = True

        if 'apply_decrease_threshold' not in st.session_state:
            st.session_state['apply_decrease_threshold'] = False

        # User input fields
        st.session_state.filtering_conditions = {
            "apply_increase_threshold": st.checkbox("使用上漲幅度條件?",
                                                    key='apply_increase_threshold',
                                                    on_change=update_checkbox,
                                                    args=('apply_increase_threshold',)),
            "apply_decrease_threshold": st.checkbox("使用下跌幅度條件?",
                                                    key='apply_decrease_threshold',
                                                    on_change=update_checkbox,
                                                    args=('apply_decrease_threshold',)),
            "increase_threshold": st.number_input('上漲幅度 > %', min_value=0.0, max_value=10.0, step=0.5),
            "decrease_threshold": st.number_input('下跌幅度 > %', min_value=0.0, max_value=10.0, step=0.5),
            "volume_threshold": st.number_input('成交量最大 n 檔', min_value=5, step=1)
        }

    with df_col:
        # Display information
        if st.session_state['initialized']:
            df = renew_df()
            filtered_df = conditional_process_df(df, st.session_state.filtering_conditions)
            st.session_state['processed_data'] = filtered_df
            st.dataframe(st.session_state['processed_data'], height=600)

    # Updating
    time.sleep(5)  # 每 5 秒更新一次
    st.rerun()
