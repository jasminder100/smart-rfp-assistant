import os
import boto3
from dotenv import load_dotenv, find_dotenv

print(".env file found at:", find_dotenv() or "NOT FOUND")
load_dotenv()

region = os.getenv("AWS_REGION")
print("AWS_REGION   =", repr(region))
print("LLM_MODEL_ID =", repr(os.getenv("LLM_MODEL_ID")))
print("EMBED_MODEL_ID =", repr(os.getenv("EMBED_MODEL_ID")))

bedrock = boto3.client("bedrock", region_name=region)
print("Client region in use:", bedrock.meta.region_name)

print("\n--- Nova inference profiles (use these for LLM_MODEL_ID) ---")
for p in bedrock.list_inference_profiles()["inferenceProfileSummaries"]:
    if "nova" in p["inferenceProfileId"]:
        print(p["inferenceProfileId"])

print("\n--- Amazon text models (direct IDs) ---")
for m in bedrock.list_foundation_models(byProvider="amazon")["modelSummaries"]:
    if "nova" in m["modelId"] or "embed" in m["modelId"]:
        print(m["modelId"], "|", m.get("modelLifecycle", {}).get("status"))