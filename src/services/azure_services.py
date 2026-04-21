# from ..conn.azure_conn import azure_conn
# import os
# import requests
# from dotenv import load_dotenv



# client = azure_conn()
# load_dotenv()
# print(client)

# curr_dirname = os.path.dirname(os.path.abspath(__file__))
# rules_path = os.path.join(curr_dirname, "agent_instruction.txt")
# with open(rules_path , "r") as rules:
#     system_instruction = rules.read()

# def get_chat_response(messages: list , search_content: str=None):

#     if search_content:
#         messages = messages.copy()

#         messages[-1]['content'] += f"\n\n[WEB SEARCH RESULT]: {search_content}"


#     full_message = [
#         {"role" : "system" , "content":system_instruction}
#     ] + messages


#    # if you pass "n" then you can ask you agent to give more then one answer like n =3 
#    # will give you three different answers
#    # by Default it is set to 1
#     response = client.chat.completions.create(
#         model=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
#         messages= full_message,
#         temperature= 0.7,
#         max_tokens= 1000,
#         stream=True
#     )

#     # the choices here is the key of the json which i get in response this key has the content we want to show 
#     for chunk in response:
#         if chunk.choices and chunk.choices[0].delta.content is not None:
#             print(chunk.choices[0].delta.content, end='',)



# search_trigger_prompt = [
#      "latest", "recent", "today", "news", "current",
#     "now", "happening", "update", "announcement",
#     "released", "launched", "2024", "2025", "this week",
#     "just", "new model", "what's new"
# ]



# # function to check should we trigger the bing search api or not 
# def should_search(user_message:str)-> bool:

#     user_msg_lower = user_message.lower()

#     return any(keyword in user_msg_lower for keyword in search_trigger_prompt)



# # Function to call Bing Search
# def bing_search(query:str, num_result: int=5) -> str:

#     endpoint = "https://api.bing.microsoft.com/v7.0/search"
#     print (os.getenv("BING_SEARCH_API_KEY"))


#    # when using the bing key we have to pass the resource api
#    # we are pass the api key as in api header it has a parameter name Ocp-Apim..... that check the auth
#     headers = {
#         "Ocp-Apim-Subscription-Key": os.getenv("BING_SEARCH_API_KEY")

#     }

#      # Query Parameters — sent as ?key=value in the URL
#     #
#     # q        → the search query
#     # count    → number of results
#     # mkt      → market/language (en-US)
#     # freshness→ only return results from last 7 days (Week)
#     #            options: Day | Week | Month
#     params = {
#         "q" : query,
#         "count": num_result,
#         "freshness": "week"
#     }

#     try:
#         response = requests.get(endpoint, headers=headers, params=params, timeout=10)


#         response.raise_for_status()

#         data = response.json()


#         results = data.get("webpages", {}).get("value", [])


#         if not results:
#             return "No Recent Result Found"
        
#         formatted = []
#         for i, result in enumerate(results, start=1):
#             title = result.get("name", "No title")
#             snippet = results.get("snippet", "NO description")
#             url = result.get("url", "")

#             formatted.append(
#                 f"{i}.{title}\n"
#                 f" {snippet}\n"
#                 f" Source: {url}\n"
#             )

#         return "\n\n".join(formatted)
#     except requests.exceptions.Timeout:
#         return "Search Timed Out"
#     except requests.exceptions.HTTPError as e:
#         return f"Searh API error: {e}"
#     except Exception as e:
#         return f"unExpected Error: {e}"
    


# # Function to check and calling both function should_search() and bing_search() same time 
# def get_search_content(user_message:str) -> str | None:

#     if not should_search(user_message):
#         return None
    
#     search_query = f"{user_message} technology news"
#     return bing_search(search_query)




from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    BingGroundingTool,
    BingGroundingSearchToolParameters,
    BingGroundingSearchConfiguration
)
from azure.identity import DefaultAzureCredential
from ..conn.config import(
    AZURE_ENDPOINT,
    AGENT_NAME,
    AZURE_API_KEY,
    BEING_CONNECTION_NAME,
    MODEL_DEPLOYMENT_NAME,
    SYSTEM_PROMPT
)
import streamlit as st



class TechAgent:


    def __init__(self):
        
        self.client = AIProjectClient(
            endpoint=AZURE_ENDPOINT,
            credential=DefaultAzureCredential()
        )
        print("Connecting to Azure2")



        #Getting Being Connection ID

        bing_conn = self.client.connections.get(
            name = BEING_CONNECTION_NAME
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
        # Creating Agent
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