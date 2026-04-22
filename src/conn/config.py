import os 
from dotenv import load_dotenv
import streamlit as st
import sys


load_dotenv()
#"""so this file is what doing is
"""
-> first the get_config() function executed
->if we running line
->-> it go and extract all the secret (Azure-endpoint, Azure_apikey etc.) from streamlit secret dashboard(we put these value there)
->if running local
->-> then in the else we just get all these value from env file direclty 
"""
def get_config(key:str)->str:

    # this try is just get the secret key from streamlit secret dashboard only work when running on cloud/live
    try:
        return st.secrets[key]
    except Exception:
        pass

    # extracting the secret from environment while running in cloud
    value = os.environ.get(key)
    if value:
        return value
    # else we get it from env when running locally 
    return os.getenv(key)
    
AZURE_ENDPOINT        = get_config("AZURE_ENDPOINT")
MODEL_DEPLOYMENT_NAME = get_config("MODEL_DEPLOYMENT_NAME")
BING_CONNECTION_NAME  = get_config("BING_CONNECTION_NAME")
AZURE_API_KEY = get_config('AZURE_API_KEY')
AGENT_NAME ='TechGuru'

curr_dir = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(curr_dir , 'agent_instruction.txt')
with open(path , 'r', encoding='utf-8') as rules:
    system_prompt = rules.read()

SYSTEM_PROMPT = system_prompt