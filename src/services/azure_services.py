import os
import importlib.util
from azure.identity import DefaultAzureCredential

# ── Load paths.py ─────────────────────────────
current_file = os.path.abspath(__file__)
services_dir = os.path.dirname(current_file)
src_dir      = os.path.dirname(services_dir)
paths_file   = os.path.join(src_dir, 'paths.py')

spec  = importlib.util.spec_from_file_location("paths", paths_file)
paths = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paths)

spec2  = importlib.util.spec_from_file_location("config", paths.CONFIG_PATH)
config = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(config)


class TechAgent:

    def __init__(self):
        self.AZURE_ENDPOINT        = os.environ.get("AZURE_ENDPOINT")        or config.AZURE_ENDPOINT
        self.MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME") or config.MODEL_DEPLOYMENT_NAME
        self.BING_CONNECTION_NAME  = os.environ.get("BING_CONNECTION_NAME")  or config.BING_CONNECTION_NAME
        self.AZURE_API_KEY         = os.environ.get("AZURE_API_KEY")         or config.AZURE_API_KEY
        self.AGENT_NAME            = config.AGENT_NAME
        self.SYSTEM_PROMPT         = config.SYSTEM_PROMPT

        # WHY check HOME?
        # Streamlit Cloud always runs as /home/adminuser
        # Local Windows machine never has this path
        self.is_cloud = os.environ.get("HOME") == "/home/adminuser"

        print(f"Mode      : {'Cloud' if self.is_cloud else 'Local'}")
        print(f"API Key   : {bool(self.AZURE_API_KEY)}")

        if self.is_cloud:
            self._setup_cloud()
        else:
            self._setup_local()


    def _setup_cloud(self):
        """
        WHY OpenAI SDK on cloud?
        AIProjectClient ONLY supports Entra ID — no API key.
        But the /openai/v1 endpoint DOES support API key.
        We use OpenAI SDK pointed at Azure endpoint with API key.
        TechGuru agent already exists — we reference it by name.
        No need to create/manage agents at all on cloud.
        """
        from openai import OpenAI

        # WHY this endpoint format?
        # Azure OpenAI v1 endpoint accepts api-key authentication
        # This is different from the projects endpoint
        base_url = self.AZURE_ENDPOINT.replace(
            "/api/projects/ai-tutor-agent",
            "/openai/v1"
        )

        self.openai_client = OpenAI(
            api_key=self.AZURE_API_KEY,
            base_url=base_url
        )

        self._history = []
        print(f"✅ Cloud ready! Endpoint: {base_url}")


    def _setup_local(self):
        """
        WHY AIProjectClient locally?
        Local machine has az login — Entra ID works.
        Full SDK gives us agent management + Bing search.
        """
        from azure.ai.projects import AIProjectClient
        from azure.ai.projects.models import (
            BingGroundingTool,
            BingGroundingSearchToolParameters,
            BingGroundingSearchConfiguration
        )

        self.client = AIProjectClient(
            endpoint=self.AZURE_ENDPOINT,
            credential=DefaultAzureCredential()
        )
        print("✅ Local connected!")

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

        try:
            versions = list(self.client.agents.list_versions(
                agent_name=self.AGENT_NAME
            ))
            for v in versions:
                self.client.agents.delete_version(
                    agent_name=self.AGENT_NAME,
                    agent_version=v.version
                )
        except Exception:
            pass

        self.agent = self.client.agents.create_version(
            agent_name=self.AGENT_NAME,
            definition={
                "kind": "prompt",
                "model": self.MODEL_DEPLOYMENT_NAME,
                "instructions": self.SYSTEM_PROMPT,
                "tools": [bing_tool]
            }
        )

        self.openai_client = self.client.get_openai_client()
        self.conversation   = self.openai_client.conversations.create(items=[])
        print(f"✅ Local ready!")


    def chat(self, user_message: str) -> str:
        if self.is_cloud:
            return self._chat_cloud(user_message)
        return self._chat_local(user_message)


    def _chat_cloud(self, user_message: str) -> str:
        """
        WHY input array with history?
        OpenAI Responses API accepts conversation history
        as an array of messages — this gives us memory.
        """
        try:
            self._history.append({
                "role": "user",
                "content": user_message
            })

            response = self.openai_client.responses.create(
                model=self.MODEL_DEPLOYMENT_NAME,
                input=self._history,
                extra_body={
                    "agent_reference": {
                        "name": self.AGENT_NAME,
                        "type": "agent_reference"
                    }
                }
            )

            reply = response.output_text
            self._history.append({
                "role": "assistant",
                "content": reply
            })
            return reply

        except Exception as e:
            import traceback
            return f"Error: {traceback.format_exc()}"


    def _chat_local(self, user_message: str) -> str:
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
            print("✅ Cleaned!")
        except Exception as e:
            print(f"Cleanup: {e}")