import os
import importlib.util
from openai import OpenAI
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
            BingGroundingTool,
            BingGroundingSearchToolParameters,
            BingGroundingSearchConfiguration
        )

# ── Load paths.py ─────────────────────────────
# just getting the path to path.py
current_file = os.path.abspath(__file__)
services_dir = os.path.dirname(current_file)
src_dir      = os.path.dirname(services_dir)
paths_file   = os.path.join(src_dir, 'paths.py')

# making a modudle (first make a path, secound create empty module, put value in that module from path.py file)
spec  = importlib.util.spec_from_file_location("paths", paths_file)
paths = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paths)

# reading data from config value 
spec2  = importlib.util.spec_from_file_location("config", paths.CONFIG_PATH)
config = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(config)


class TechAgent:

    def __init__(self):


        # os.environ first → catches Streamlit secrets injected by main_ui.py
        # config fallback  → catches local .env values
        self.AZURE_ENDPOINT        = os.environ.get("AZURE_ENDPOINT")        or config.AZURE_ENDPOINT
        self.MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME") or config.MODEL_DEPLOYMENT_NAME
        self.BING_CONNECTION_NAME  = os.environ.get("BING_CONNECTION_NAME")  or config.BING_CONNECTION_NAME
        self.AZURE_API_KEY         = os.environ.get("AZURE_API_KEY")         or config.AZURE_API_KEY
        self.AGENT_NAME            = config.AGENT_NAME
        self.SYSTEM_PROMPT         = config.SYSTEM_PROMPT

        #checking the envir if it local then everytime API-KEy is null because there is not api in env file
        if self.AZURE_API_KEY:
            self.is_cloud = True
            self._setup_cloud()
        else:
            print("Mode: Local → AIProjectClient with az login")
            self.is_cloud = False
            self._setup_local()


    def _setup_cloud(self):
        """
        WHY OpenAI SDK not AIProjectClient on cloud?
        Official docs confirm: AIProjectClient ONLY supports Entra ID.
        API key ONLY works on /openai/v1 endpoint.
        We use OpenAI SDK pointed at Azure /openai/v1 endpoint.
        TechGuru agent already exists — we just reference it by name.
        """
        base_url = self.AZURE_ENDPOINT.split("/api/projects/")[0] + "/openai/v1"

        self.openai_client = OpenAI(
            api_key=self.AZURE_API_KEY,
            base_url=base_url
        )

        self._history = []

    def _setup_local(self):
        """
        WHY AIProjectClient locally?
        Local machine has az login session.
        DefaultAzureCredential uses it automatically.
        Full SDK gives us agent management + Bing tool.
        """

        self.client = AIProjectClient(
            endpoint=self.AZURE_ENDPOINT,
            credential=DefaultAzureCredential()
        )
        print("✅ Local connected!")

        # Get Bing connection
        bing_conn = self.client.connections.get(
            name=self.BING_CONNECTION_NAME
        )
        bing_id = bing_conn._data['id']
        print("✅ Bing connection found!")

        bing_tool = BingGroundingTool(
            bing_grounding=BingGroundingSearchToolParameters(
                search_configurations=[
                    BingGroundingSearchConfiguration(
                        project_connection_id=bing_id
                    )
                ]
            )
        )

        # Delete old versions and create fresh
        # WHY recreate locally?
        # Ensures latest SYSTEM_PROMPT is always used
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

        self.openai_client = self.client.get_openai_client()
        self.conversation   = self.openai_client.conversations.create(
            items=[]
        )
        print(f"✅ Local ready!")


   # this function just checking if the enviroment is local or live
    def chat(self, user_message: str) -> str:
        if self.is_cloud:
            return self._chat_cloud(user_message)
        return self._chat_local(user_message)


    def _chat_cloud(self, user_message: str) -> str:
        """
        WHY input array with history?
        OpenAI Responses API accepts full message history.
        This gives conversation memory without needing
        a conversation ID or thread.
        """
        try:
            # so first we put  the message typed by user in history 
            self._history.append({
                "role": "user",
                "content": user_message
            })
            # making a proper message by adding instruction first then user message
            messages = [
                {"role": "system" , "content":self.SYSTEM_PROMPT}
            ] + self._history

            response = self.openai_client.responses.create(
                model=self.MODEL_DEPLOYMENT_NAME,
                input=messages
            )

            reply = response.output_text

            self._history.append({
                "role": "assistant",
                "content": reply
            })

            return reply

        except Exception as e:
            import traceback
            error = traceback.format_exc()
            print(f"Cloud chat error: {error}")
            return f"Error: {error}"


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
            print(f"Cleanup note: {e}")