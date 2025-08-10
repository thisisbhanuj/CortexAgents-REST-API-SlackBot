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
# print("JWT token length:", len(jwt_token))
# print("JWT token (first 50 chars):", jwt_token[:50], "...")

# Build the payload
payload = {
    "model": os.getenv("MODEL"),
    "response_instruction": "You will always maintain a friendly tone and provide concise response.",
    "experimental": {},
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
    ],
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
            "semantic_model_file": os.getenv("SEMANTIC_MODEL")
        }
    }
}

# Send the POST request
headers = {
    "X-Snowflake-Authorization-Token-Type": "KEYPAIR_JWT",
    "Authorization": f"Bearer {jwt_token}",
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream"
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
    print("✅ Cortex Agents response:\n\n", response.text)

except requests.exceptions.RequestException as e:
    print("❌ Curl Error:", str(e))
