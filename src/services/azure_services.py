from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    BingGroundingTool,
    BingGroundingSearchToolParameters,
    BingGroundingSearchConfiguration
)
import os
import importlib.util
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
# from src.conn.config import(
#     AZURE_ENDPOINT,
#     AGENT_NAME,
#     BEING_CONNECTION_NAME,
#     MODEL_DEPLOYMENT_NAME,
#     SYSTEM_PROMPT
# )

# ── Step 1: Find and load paths.py ────────────
current_file = os.path.abspath(__file__)       # .../src/services/azure_services.py
services_dir = os.path.dirname(current_file)   # .../src/services/
src_dir      = os.path.dirname(services_dir)   # .../src/
paths_file   = os.path.join(src_dir, 'paths.py')

# Load paths.py directly
spec   = importlib.util.spec_from_file_location("paths", paths_file)
paths  = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paths)

# ── Step 2: Load config.py using path from paths.py ──
spec2   = importlib.util.spec_from_file_location("config", paths.CONFIG_PATH)
config  = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(config)

# ── Step 3: Extract all values ─────────────────


class TechAgent:


    def __init__(self):
        AZURE_ENDPOINT        = config.AZURE_ENDPOINT
        MODEL_DEPLOYMENT_NAME = config.MODEL_DEPLOYMENT_NAME
        BING_CONNECTION_NAME  = config.BING_CONNECTION_NAME
        AGENT_NAME            = config.AGENT_NAME
        SYSTEM_PROMPT         = config.SYSTEM_PROMPT
        AZURE_API_KEY         = os.environ.get("AZURE_API_KEY") or config.AZURE_API_KEY
        api_key = AZURE_API_KEY
        is_cloud = os.environ.get("HOME") == "/home/adminuser"

        def get_credential():
            if is_cloud and AZURE_API_KEY:
                print("🔐 Using AzureKeyCredential")
                return AzureKeyCredential(AZURE_API_KEY)
            print("🔐 Using DefaultAzureCredential")
            return DefaultAzureCredential()
        
        if is_cloud:
            self.client = AIProjectClient(
                endpoint=AZURE_ENDPOINT,
                credential=get_credential()
                )
            print("Connecting to Azure in Cloud")
        else:
            self.client = AIProjectClient(
                endpoint=AZURE_ENDPOINT,
                credential=DefaultAzureCredential()
                )
            print("Connecting to Azure in Locally")



        #Getting Being Connection ID

        bing_conn = self.client.connections.get(
            name = BING_CONNECTION_NAME
        )

        # now retriving the connection id 
        bing_id = bing_conn._data['id']

        

        # building the Bing Toll
        # the syntx is same as it only change change the bing_id for everytime
        bing_tool = BingGroundingTool(
            bing_grounding=BingGroundingSearchToolParameters(
                search_configurations=[
                    BingGroundingSearchConfiguration(
                        project_connection_id= bing_id
                    )
                ]
            )
        )


       
        # Creating Agent
        
        if is_cloud:
            print('Cloud Agent')
            self.agent = self.client.agents.get(
                agent_name='TechGuru'
            )
        else:
            try:
                versions = list(
                    self.client.agents.list_versions(agent_name=AGENT_NAME)
                    )
                for v in versions:
                    self.client.agents.delete_version(
                        agent_name=AGENT_NAME,
                        agent_version=v.version
                        )
                    print(f"{v.version} : Deleted")
            except Exception as e:
                print(f"Deleting Exception: {e}")
                print(f"DEBUG — model: '{MODEL_DEPLOYMENT_NAME}', agent: '{AGENT_NAME}'")
            self.agent = self.client.agents.create_version(
                agent_name=AGENT_NAME,
                definition={
                    "kind": "prompt",
                    "model": MODEL_DEPLOYMENT_NAME,
                    "instructions":SYSTEM_PROMPT,
                    "tools":[bing_tool]
                    }
                )
        print(f"System Prompt:    {SYSTEM_PROMPT}")
        print("Connecting to Azure23")
        print(f'Agent Created{self.agent.id}')
         

        # now we get openai_client as well just like we get client above 
        # it is because it latest version we use openai for conversation and the above client is for managing resources
        self.openai_client = self.client.get_openai_client()

        

        # creating conversation
        self.conversation = self.openai_client.conversations.create(
            items=[]
        )

        print(f"conversation read {self.conversation.id}")
    



    # the chat method which will be called everytime
    def chat(self, user_message:str) -> str:

        #adding user previous messages so agent know history
        self.openai_client.conversations.items.create(
            conversation_id=self.conversation.id,
            items=[{
                'type':"message",
                "role":"user",
                "content":user_message
            }]
        )


        # ── Generate response ─────────────────────
            # WHY agent_reference?
            # Tells the Responses API which agent to use.
            # Our agent brings the system prompt + Bing tool.
            # Without this it would just be a plain GPT call
        response = self.openai_client.responses.create(
            conversation=self.conversation.id,
            extra_body={
                "agent_reference":{
                    "name": AGENT_NAME,
                    "type": "agent_reference"
                }
            }
        )

        return response.output_text
    
    def clean(self):
        try:
            self.openai_client.conversations.delete(
                conversation_id=self.conversation.id
            )
            self.client.agents.delete_version(
                agent_name=self.agent.name,
                agent_version=self.agent.version
            )

            print("Cleaned")
        except Exception as e :
            print(f"Error: {e}")