# At top of file — outside class
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    BingGroundingTool,
    BingGroundingSearchToolParameters,
    BingGroundingSearchConfiguration
)
from azure.core.credentials import AccessToken, AccessTokenInfo
from azure.identity import DefaultAzureCredential
import os
import importlib.util
import time

# ── API Key Credential Wrapper ────────────────
class ApiKeyCredential:
    def __init__(self, key: str):
        self.key = key

    def get_token(self, *scopes, **kwargs):
        return AccessToken(self.key, int(time.time()) + 3600)

    def get_token_info(self, *scopes, **kwargs):
        return AccessTokenInfo(self.key, int(time.time()) + 3600)


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
        # Read values fresh — os.environ first then config
        self.AZURE_ENDPOINT        = os.environ.get("AZURE_ENDPOINT")        or config.AZURE_ENDPOINT
        self.MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME") or config.MODEL_DEPLOYMENT_NAME
        self.BING_CONNECTION_NAME  = os.environ.get("BING_CONNECTION_NAME")  or config.BING_CONNECTION_NAME
        self.AZURE_API_KEY         = os.environ.get("AZURE_API_KEY")         or config.AZURE_API_KEY
        self.AGENT_NAME            = config.AGENT_NAME
        self.SYSTEM_PROMPT         = config.SYSTEM_PROMPT

        is_cloud = os.environ.get("HOME") == "/home/adminuser"

        print(f"Environment : {'Cloud' if is_cloud else 'Local'}")
        print(f"API Key     : {bool(self.AZURE_API_KEY)}")

        # ── Credential ────────────────────────
        if self.AZURE_API_KEY:
            credential = ApiKeyCredential(self.AZURE_API_KEY)
            print("Using ApiKeyCredential")
        else:
            credential = DefaultAzureCredential()
            print("Using DefaultAzureCredential")

        # ── Connect ───────────────────────────
        self.client = AIProjectClient(
            endpoint=self.AZURE_ENDPOINT,
            credential=credential
        )
        print("Connected!")

        # ── Bing Tool ─────────────────────────
        bing_conn = self.client.connections.get(name=self.BING_CONNECTION_NAME)
        bing_id   = bing_conn._data['id']

        bing_tool = BingGroundingTool(
            bing_grounding=BingGroundingSearchToolParameters(
                search_configurations=[
                    BingGroundingSearchConfiguration(
                        project_connection_id=bing_id
                    )
                ]
            )
        )
        print("Bing ready!")

        # ── Agent ─────────────────────────────
        if is_cloud:
            print("Cloud: Getting TechGuru...")
            self.agent = self.client.agents.get(agent_name=self.AGENT_NAME)
            print(f"Agent: {self.agent.name}")
        else:
            print("Local: Recreating agent...")
            try:
                versions = list(self.client.agents.list_versions(
                    agent_name=self.AGENT_NAME
                ))
                for v in versions:
                    self.client.agents.delete_version(
                        agent_name=self.AGENT_NAME,
                        agent_version=v.version
                    )
                    print(f"Deleted v{v.version}")
            except Exception:
                print("No existing versions")

            self.agent = self.client.agents.create_version(
                agent_name=self.AGENT_NAME,
                definition={
                    "kind": "prompt",
                    "model": self.MODEL_DEPLOYMENT_NAME,
                    "instructions": self.SYSTEM_PROMPT,
                    "tools": [bing_tool]
                }
            )
            print(f"Agent created: {self.agent.name}")

        # ── Conversation ──────────────────────
        self.openai_client = self.client.get_openai_client()
        self.conversation  = self.openai_client.conversations.create(items=[])
        print(f"Ready!")


    def chat(self, user_message: str) -> str:
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
            self.openai_client.conversations.delete(
                conversation_id=self.conversation.id
            )
            print("Cleaned!")
        except Exception as e:
            print(f"Cleanup: {e}")