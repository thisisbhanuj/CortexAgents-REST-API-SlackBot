from typing import Any
import os

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

import snowflake.connector
from snowflake.core import Root
import cortex_chat

from dotenv import load_dotenv
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import time
import requests

matplotlib.use('Agg')
load_dotenv()

# ===== ENV VARS =====
ACCOUNT = os.getenv("ACCOUNT")
HOST = os.getenv("HOST")
USER = os.getenv("USER")
DATABASE = os.getenv("DATABASE")
USER_PASSWORD = os.getenv("USER_PASSWORD")
SCHEMA = os.getenv("SEMANTIC_VIEW_SCHEMA")
ROLE = os.getenv("USER_ROLE")
WAREHOUSE = os.getenv("WAREHOUSE")
CONNECTION_MODE = os.getenv("CONNECTION_MODE")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT")
SEMANTIC_MODEL_SEARCH_SERVICE = os.getenv("SEMANTIC_MODEL_SEARCH_SERVICE")
SEMANTIC_MODEL_SEMANTIC_VIEW = os.getenv("SEMANTIC_MODEL_SMV")
SEARCH_SERVICE = os.getenv("SEARCH_SERVICE")
RSA_PRIVATE_KEY_PATH = os.getenv("RSA_PRIVATE_KEY_PATH")
RSA_PRIVATE_KEY_PASSPHRASE = os.getenv("RSA_PRIVATE_KEY_PASSPHRASE")
MODEL = os.getenv("MODEL")

DEBUG = True

# Initializes App
app = App(token=SLACK_BOT_TOKEN)
messages = []

service_type = os.getenv("SERVICE_TYPE")
SEMANTIC_MODEL = {
    "SEMANTIC_VIEW": SEMANTIC_MODEL_SEMANTIC_VIEW,
    "SEARCH_SERVICE": SEMANTIC_MODEL_SEARCH_SERVICE,
}.get(service_type, SEMANTIC_MODEL_SEARCH_SERVICE)

# ===== Snowflake Connection Helpers =====
def get_snowflake_conn():
    """Create a fresh Snowflake connection using JWT."""
    return snowflake.connector.connect(
        host=HOST,
        account=ACCOUNT,
        warehouse=WAREHOUSE,
        role=ROLE,
        user=USER,
        authenticator="SNOWFLAKE_JWT",  
        private_key_file=RSA_PRIVATE_KEY_PATH,
        private_key_file_pwd=RSA_PRIVATE_KEY_PASSPHRASE,
        client_fetch_use_mp=True, # Enables multiprocessing for fetching query results in parallel.
        client_prefetch_threads=8, # Number of threads to download the result set.
        session_parameters={"CLIENT_TELEMETRY_ENABLED": True},
        reuse_results=True,
        disable_query_context_cache=False,
        enable_retry_reason_in_query_response=True,
        login_timeout=60,
        network_timeout=600,
        socket_timeout=600
    )

def execute_sql(sql: str):
    """Execute SQL with automatic reconnect on token expiration."""
    global CONN
    try:
        df = pd.read_sql(sql, CONN)
        return df
    except snowflake.connector.errors.ProgrammingError as e:
        if "08001" in str(e):  # Token expired
            print("Snowflake token expired, reconnecting...")
            CONN.close()
            CONN = get_snowflake_conn()
            df = pd.read_sql(sql, CONN)
            return df
        else:
            raise

# ===== Cortex Chat Helpers =====
def ask_agent(prompt):
    resp = CORTEX_APP.chat(prompt)
    return resp

def display_agent_response(content,say):
    if content['sql']:
        sql = content['sql']
        df = execute_sql(sql)
        say(
            text = "Answer:",
            blocks=[
                {
                    "type": "rich_text",
                    "elements": [
                        {
                            "type": "rich_text_quote",
                            "elements": [
                                {
                                    "type": "text",
                                    "text": "Answer:",
                                    "style": {
                                        "bold": True
                                    }
                                }
                            ]
                        },
                        {
                            "type": "rich_text_preformatted",
                            "elements": [
                                {
                                    "type": "text",
                                    "text": f"{df.to_string()}"
                                }
                            ]
                        }
                    ]
                }
            ]
        )
        if len(df.columns) > 1:
            chart_img_url = None
            try:
                chart_img_url = None #plot_chart(df) Not required for now
            except Exception as e:
                error_info = f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}"
                print(f"Warning: Data likely not suitable for displaying as a chart. {error_info}")
            if chart_img_url is not None:
                say(
                    text = "Chart",
                    blocks=[
                        {
                            "type": "image",
                            "title": {
                                "type": "plain_text",
                                "text": "Chart"
                            },
                            "block_id": "image",
                            "slack_file": {
                                "url": f"{chart_img_url}"
                            },
                            "alt_text": "Chart"
                        }
                    ]
                )
    else:
        say(
            text = "Answer:",
            blocks = [
                {
                    "type": "rich_text",
                    "elements": [
                        {
                            "type": "rich_text_quote",
                            "elements": [
                                {
                                    "type": "text",
                                    "text": f"Answer: {content['text']}",
                                    "style": {
                                        "bold": True
                                    }
                                }
                            ]
                        },
                        {
                            "type": "rich_text_quote",
                            "elements": [
                                {
                                    "type": "text",
                                    "text": f"* Citation: {content['citations']}",
                                    "style": {
                                        "italic": True
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]                
        )

# ===== Slack Event Handler =====
@app.event("message")
def handle_message_events(ack, body, say):
    try:
        ack()
        prompt = body['event']['text']
        say(
            text = "Snowflake Cortex AI is generating a response",
            blocks=[
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": ":snowflake: Snowflake Cortex AI is generating a response. Please wait...",
                    }
                },
                {
                    "type": "divider"
                },
            ]
        )
        response = ask_agent(prompt)

        # Optional Debug
        # print(response)

        display_agent_response(response,say)
    except Exception as e:
        error_info = f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}"
        print(error_info)
        say(
            text = "Request failed...",
            blocks=[
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "plain_text",
                        "text": f"{error_info}",
                    }
                },
                {
                    "type": "divider"
                },
            ]
        )        

# ===== Optional Charting =====
def plot_chart(df):
    plt.figure(figsize=(10, 6), facecolor='#333333')

    # plot pie chart with percentages, using dynamic column names
    plt.pie(df[df.columns[1]], 
            labels=df[df.columns[0]], 
            autopct='%1.1f%%', 
            startangle=90, 
            colors=['#1f77b4', '#ff7f0e'], 
            textprops={'color':"white",'fontsize': 16})

    # ensure equal aspect ratio
    plt.axis('equal')
    # set the background color for the plot area to dark as well
    plt.gca().set_facecolor('#333333')   
    plt.tight_layout()

    # save the chart as a .jpg file
    file_path_jpg = 'pie_chart.jpg'
    plt.savefig(file_path_jpg, format='jpg')
    file_size = os.path.getsize(file_path_jpg)

    # upload image file to slack
    file_upload_url_response = app.client.files_getUploadURLExternal(filename=file_path_jpg,length=file_size)
    if DEBUG:
        print(file_upload_url_response)
    file_upload_url = file_upload_url_response['upload_url']
    file_id = file_upload_url_response['file_id']
    with open(file_path_jpg, 'rb') as f:
        response = requests.post(file_upload_url, files={'file': f})

    # check the response
    img_url = None
    if response.status_code != 200:
        print("File upload failed", response.text)
    else:
        # complete upload and get permalink to display
        response = app.client.files_completeUploadExternal(files=[{"id":file_id, "title":"chart"}])
        if DEBUG:
            print(response)
        img_url = response['files'][0]['permalink']
        time.sleep(2)
    
    return img_url

# ===== Init Function =====
def init():
    conn,jwt,cortex_app = None,None,None

    conn = snowflake.connector.connect(
        host=HOST,
        account=ACCOUNT,
        warehouse=WAREHOUSE,
        role=ROLE,
        user=USER,
        authenticator="SNOWFLAKE_JWT",  
        private_key_file=RSA_PRIVATE_KEY_PATH,
        private_key_file_pwd=RSA_PRIVATE_KEY_PASSPHRASE,
        login_timeout=60,
        network_timeout=600,
        socket_timeout=600
    )
    if not conn.rest.token:
        print(">>>>>>>>>> Snowflake connection unsuccessful!")

    cortex_app = cortex_chat.CortexChat(
        AGENT_ENDPOINT, 
        SEARCH_SERVICE,
        SEMANTIC_MODEL,
        MODEL, 
        ACCOUNT,
        USER,
        RSA_PRIVATE_KEY_PATH
    )

    print(">>>>>>>>>> Init complete")
    return conn,jwt,cortex_app

# Start App Server
if __name__ == "__main__":
    CONN,JWT,CORTEX_APP = init()
    Root = Root(CONN)
    mode = CONNECTION_MODE.lower()
    if mode == "socket":
        SocketModeHandler(app, SLACK_APP_TOKEN).start()
    else:
        app.start(port=int(os.environ.get("PORT", 3000)))
    