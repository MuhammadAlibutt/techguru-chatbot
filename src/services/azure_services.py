from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    BingGroundingTool,
    BingGroundingSearchToolParameters,
    BingGroundingSearchConfiguration
)
import os
import importlib.util
import requests
import time
from azure.identity import DefaultAzureCredential

# ── Load paths.py ─────────────────────────────
current_file = os.path.abspath(__file__)
services_dir = os.path.dirname(current_file)
src_dir      = os.path.dirname(services_dir)
paths_file   = os.path.join(src_dir, 'paths.py')

spec  = importlib.util.spec_from_file_location("paths", paths_file)
paths = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paths)

# ── Load config.py ─────────────────────────────
spec2  = importlib.util.spec_from_file_location("config", paths.CONFIG_PATH)
config = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(config)


class TechAgent:

    def __init__(self):
        # ── Read values ───────────────────────
        # WHY os.environ first?
        # main_ui.py injects st.secrets into os.environ
        # BEFORE loading this module and calling TechAgent()
        # So os.environ always has the most current values
        self.AZURE_ENDPOINT        = os.environ.get("AZURE_ENDPOINT")        or config.AZURE_ENDPOINT
        self.MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME") or config.MODEL_DEPLOYMENT_NAME
        self.BING_CONNECTION_NAME  = os.environ.get("BING_CONNECTION_NAME")  or config.BING_CONNECTION_NAME
        self.AZURE_API_KEY         = os.environ.get("AZURE_API_KEY")         or config.AZURE_API_KEY
        self.AGENT_NAME            = config.AGENT_NAME
        self.SYSTEM_PROMPT         = config.SYSTEM_PROMPT

        # ── Detect environment ─────────────────
        # WHY check API key?
        # If API key exists we use REST directly
        # If no API key we use SDK with az login (local)
        self.is_cloud = bool(self.AZURE_API_KEY) and \
                        os.environ.get("HOME") == "/home/adminuser"

        print(f"Environment  : {'Cloud' if self.is_cloud else 'Local'}")
        print(f"API Key      : {bool(self.AZURE_API_KEY)}")
        print(f"Endpoint     : {bool(self.AZURE_ENDPOINT)}")
        print(f"Agent Name   : {self.AGENT_NAME}")

        if self.is_cloud:
            # ── Cloud: Use REST API directly ──
            # WHY REST instead of SDK?
            # Azure AI Foundry accepts "api-key" header
            # but the SDK sends "Bearer token" which fails
            # REST call with api-key header works perfectly
            # (verified with test_api_key.py → Status 400
            #  meaning auth PASSED, just missing api-version)
            print("Cloud mode: Using REST API with api-key header")
            self._history = []
            self._setup_rest_headers()

        else:
            # ── Local: Use SDK with az login ──
            # WHY SDK locally?
            # Local machine has az login session
            # DefaultAzureCredential uses it automatically
            print("Local mode: Using SDK with DefaultAzureCredential")
            self.client = AIProjectClient(
                endpoint=self.AZURE_ENDPOINT,
                credential=DefaultAzureCredential()
            )
            print("✅ Connected!")

            # Get Bing connection
            bing_conn = self.client.connections.get(
                name=self.BING_CONNECTION_NAME
            )
            bing_id = bing_conn._data['id']

            bing_tool = BingGroundingTool(
                bing_grounding=BingGroundingSearchToolParameters(
                    search_configurations=[
                        BingGroundingSearchConfiguration(
                            project_connection_id=bing_id
                        )
                    ]
                )
            )
            print("✅ Bing tool ready!")

            # Delete old and create fresh agent
            try:
                versions = list(self.client.agents.list_versions(
                    agent_name=self.AGENT_NAME
                ))
                for v in versions:
                    self.client.agents.delete_version(
                        agent_name=self.AGENT_NAME,
                        agent_version=v.version
                    )
                    print(f"   Deleted v{v.version}")
            except Exception:
                print("   No existing versions found")

            self.agent = self.client.agents.create_version(
                agent_name=self.AGENT_NAME,
                definition={
                    "kind": "prompt",
                    "model": self.MODEL_DEPLOYMENT_NAME,
                    "instructions": self.SYSTEM_PROMPT,
                    "tools": [bing_tool]
                }
            )
            print(f"✅ Agent created: {self.agent.name}")

            # Create conversation
            self.openai_client = self.client.get_openai_client()
            self.conversation   = self.openai_client.conversations.create(
                items=[]
            )
            print(f"✅ Ready! Conv: {self.conversation.id[:20]}...")


    def _setup_rest_headers(self):
        """
        WHY separate method?
        Clean way to set up REST headers once.
        Used by all REST-based methods.
        """
        self._headers = {
            "api-key": self.AZURE_API_KEY,
            "Content-Type": "application/json"
        }
        # Create conversation via REST
        url = f"{self.AZURE_ENDPOINT}/openai/v1/conversations?api-version=2025-05-01-preview"
        response = requests.post(url, headers=self._headers, json={})
        
        if response.status_code in [200, 201]:
            data = response.json()
            self._conversation_id = data.get("id")
            print(f"✅ REST conversation created: {self._conversation_id}")
        else:
            # If conversation creation fails, use stateless mode
            print(f"⚠️ Conversation creation returned {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            self._conversation_id = None
            print("Using stateless mode (no conversation history)")


    def chat(self, user_message: str) -> str:
        if self.is_cloud:
            return self._chat_rest(user_message)
        return self._chat_sdk(user_message)


    def _chat_rest(self, user_message: str) -> str:
        """
        WHY direct REST?
        Cloud uses api-key auth via direct HTTP requests.
        No SDK needed — pure requests library.
        """
        try:
            # Add to history
            self._history.append({
                "role": "user",
                "content": user_message
            })

            url = f"{self.AZURE_ENDPOINT}/openai/v1/responses?api-version=2025-05-01-preview"

            body = {
                "model": self.MODEL_DEPLOYMENT_NAME,
                "input": self._history,
                "agent_reference": {
                    "name": self.AGENT_NAME,
                    "type": "agent_reference"
                }
            }

            # Add conversation if we have one
            if self._conversation_id:
                body["conversation"] = self._conversation_id

            response = requests.post(
                url,
                headers=self._headers,
                json=body
            )

            print(f"REST response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                reply = data.get("output_text", "")

                if not reply:
                    # Try alternative response format
                    output = data.get("output", [])
                    for item in output:
                        if item.get("type") == "message":
                            content = item.get("content", [])
                            for c in content:
                                if c.get("type") == "output_text":
                                    reply = c.get("text", "")
                                    break

                # Save to history
                self._history.append({
                    "role": "assistant",
                    "content": reply
                })
                return reply

            else:
                return f"API Error {response.status_code}: {response.text[:300]}"

        except Exception as e:
            import traceback
            return f"Error: {traceback.format_exc()}"


    def _chat_sdk(self, user_message: str) -> str:
        """
        WHY separate SDK method?
        Local uses full SDK with conversation memory.
        Cleaner to separate REST and SDK logic.
        """
        try:
            self.openai_client.conversations.items.create(
                conversation_id=self.conversation.id,
                items=[{
                    "type": "message",
                    "role": "user",
                    "content": user_message
                }]
            )

            response = self.openai_client.responses.create(
                conversation=self.conversation.id,
                extra_body={
                    "agent_reference": {
                        "name": self.AGENT_NAME,
                        "type": "agent_reference"
                    }
                }
            )
            return response.output_text

        except Exception as e:
            import traceback
            return f"Error: {traceback.format_exc()}"


    def clean(self):
        try:
            if not self.is_cloud:
                self.openai_client.conversations.delete(
                    conversation_id=self.conversation.id
                )
            print("✅ Cleaned up!")
        except Exception as e:
            print(f"Cleanup note: {e}")