from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity import DefaultAzureCredential
import os

load_dotenv()

client = AIProjectClient(
    endpoint=os.getenv("AZURE_ENDPOINT"),
    credential=DefaultAzureCredential()
)

# WHY try as raw dict?
# PromptAgentDefinition uses *args/**kwargs internally
# which means it might expect a raw dict instead of
# named keyword arguments — let's test both ways

print("Testing raw dict approach...")
try:
    agent = client.agents.create_version(
        agent_name="TechBotTest",
        definition={
            "kind": "prompt",
            "model": os.getenv("MODEL_DEPLOYMENT_NAME"),
            "instructions": "You are a helpful assistant."
        }
    )
    print(f"✅ Raw dict worked! Version: {agent.version}")
    client.agents.delete_version(
        agent_name=agent.name,
        agent_version=agent.version
    )
    print("✅ Cleaned up!")

except Exception as e:
    print(f"❌ Raw dict failed: {e}")

    print("\nTesting PromptAgentDefinition with model_deployment_name...")
    try:
        agent = client.agents.create_version(
            agent_name="TechBotTest",
            definition=PromptAgentDefinition(
                model_deployment_name=os.getenv("MODEL_DEPLOYMENT_NAME"),
                instructions="You are a helpful assistant."
            )
        )
        print(f"✅ Works! Version: {agent.version}")
        client.agents.delete_version(
            agent_name=agent.name,
            agent_version=agent.version
        )
    except Exception as e2:
        print(f"❌ Also failed: {e2}")