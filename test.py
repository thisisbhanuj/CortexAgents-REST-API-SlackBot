import os
import json
import requests
from dotenv import load_dotenv
import generate_jwt
from generate_jwt import JWTGenerator
import jwt as pyjwt

# Load environment variables from .env
load_dotenv()

if not os.path.isfile(os.getenv("RSA_PRIVATE_KEY_PATH")):
    raise FileNotFoundError("Private key file not found")

# Instantiate JWT generator and get token
jwt = JWTGenerator(
    os.getenv("ACCOUNT"),
    os.getenv("USER"),
    os.getenv("RSA_PRIVATE_KEY_PATH")
    )
jwt_token = jwt.get_token()
# Debug JWT
# print("JWT Token:", jwt_token)
# print("JWT token (first 100 chars):", jwt_token[:100], "...")

# Build the payload
payloadForCortexSearch = {
    "model": os.getenv("MODEL"),
    "response_instruction": "You will always maintain a friendly tone and provide concise response.",
    "tools": [
        {
            "tool_spec": {
                "type": "cortex_search",
                "name": "vehicles_info_search"
            }
        },
        {
            "tool_spec": {
                "type": "cortex_analyst_text_to_sql",
                "name": "supply_chain"
            }
        }
    ],
    "tool_resources": {
        "vehicles_info_search": {
            "name": os.getenv("SEARCH_SERVICE"),
            "max_results": 1,
            "title_column": "title",
            "id_column": "relative_path"
        },
        "supply_chain": {
            "semantic_model_file": os.getenv("SEMANTIC_MODEL_SEARCH_SERVICE")
        }
    },
    "tool_choice": {
        "type": "auto"
    },
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Can you show me a breakdown of customer support tickets by service type cellular vs business internet?"
                }
            ]
        }
    ]
}

payloadForCortexAgentOnSematicView = {
    "model": os.getenv("MODEL"),
    "response_instruction": "You will always maintain a friendly tone and provide concise response.",
    "tools": [
        {
            "tool_spec": {
                "type": "cortex_analyst_text_to_sql",
                "name": "supply_chain"
            }
        }
    ],
    "tool_resources": {
        "supply_chain": {
            "semantic_model_file": os.getenv("SEMANTIC_MODEL_SMV")
        }
    },
    "tool_choice": {
        "type": "auto"
    },
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Show me the top selling brands in by total sales quantity in the state ‘TX' in the ‘Books' category in the year 2003"
                }
            ]
        }
    ]
}

payload_map = {
    "SEMANTIC_VIEW": payloadForCortexAgentOnSematicView,
    "SEARCH_SERVICE": payloadForCortexSearch
}

payload = payload_map.get(os.getenv("SERVICE_TYPE"), payloadForCortexSearch)

print(payload)

# Send the POST request
headers = {
    "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
    "Authorization": f"Bearer {jwt_token}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Optional: Decode header/payload to confirm structure
# decoded_header = pyjwt.get_unverified_header(jwt_token)
# decoded_payload = pyjwt.decode(jwt_token, options={"verify_signature": False})
# print("JWT header:", decoded_header)
# print("JWT payload:", decoded_payload)
try:
    response = requests.post(
        os.getenv("AGENT_ENDPOINT"),
        headers=headers,
        data=json.dumps(payload)
    )
    response.raise_for_status()
    print("✅ Cortex Agents Response:\n\n", response.text)

except requests.exceptions.RequestException as e:
    error_info = f"{type(e).__name__} at line {e.__traceback__.tb_lineno} of {__file__}: {e}"
    print("❌ Curl Error:", error_info)
