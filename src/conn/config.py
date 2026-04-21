import os 
from dotenv import load_dotenv


load_dotenv()


AZURE_ENDPOINT =os.getenv('AZURE_ENDPOINT')

AZURE_API_KEY =os.getenv('AZURE_API_KEY') 


MODEL_DEPLOYMENT_NAME = os.getenv('MODEL_DEPLOYMENT_NAME')
BEING_CONNECTION_NAME = os.getenv('BING_CONNECTION_NAME')


AGENT_NAME ='TechGuru'

curr_dir = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(curr_dir , 'agent_instruction.txt')
with open(path , 'r') as rules:
    system_prompt = rules.read()

SYSTEM_PROMPT = system_prompt