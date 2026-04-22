# create_permanent_agent.py
# Run once locally to create permanent agent on Azure

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    BingGroundingTool,
    BingGroundingSearchToolParameters,
    BingGroundingSearchConfiguration
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
import os

load_dotenv()

client = AIProjectClient(
    endpoint=os.getenv("AZURE_ENDPOINT"),
    credential=DefaultAzureCredential()
)

# ── Get Bing ──────────────────────────────────
bing_connection = client.connections.get(name=os.getenv("BING_CONNECTION_NAME"))
bing_id = bing_connection._data['id']
print(f"✅ Bing ID found")

bing_tool = BingGroundingTool(
    bing_grounding=BingGroundingSearchToolParameters(
        search_configurations=[
            BingGroundingSearchConfiguration(
                project_connection_id=bing_id
            )
        ]
    )
)

# ── Load system prompt ────────────────────────
with open('src/conn/agent_instruction.txt', 'r', encoding='utf-8') as f:
    system_prompt = f.read()
print(f"✅ Prompt loaded: {len(system_prompt)} chars")

# ── Delete existing TechGuru versions ─────────
print("Cleaning up old versions...")
try:
    versions = list(client.agents.list_versions(agent_name="TechGuru"))
    for v in versions:
        client.agents.delete_version(
            agent_name="TechGuru",
            agent_version=v.version
        )
        print(f"   Deleted version: {v.version}")
except Exception as e:
    print(f"   No existing versions: {e}")

# ── Create permanent agent ────────────────────
print("Creating TechGuru agent...")
agent = client.agents.create_version(
    agent_name="TechGuru",
    definition={
        "kind": "prompt",
        "model": os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4o-mini"),
        "instructions": system_prompt,
        "tools": [bing_tool]
    }
)

print(f"\n🎉 SUCCESS!")
print(f"   Name    : {agent.name}")
print(f"   Version : {agent.version}")
print(f"   ID      : {agent.id}")
print(f"\nNow go to ai.azure.com → Agents and verify TechGuru is there!")