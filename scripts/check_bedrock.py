import json, os
import boto3
from dotenv import load_dotenv

load_dotenv()
client = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_REGION"))

# Test 1: the LLM (this will write our answers)
resp = client.converse(
    modelId=os.getenv("LLM_MODEL_ID"),
    messages=[{"role": "user", "content": [{"text": "Say hello in one short sentence."}]}],
    inferenceConfig={"maxTokens": 50},
)
print("LLM says:", resp["output"]["message"]["content"][0]["text"])
print("Tokens used:", resp["usage"])

# Test 2: embeddings (this turns text into numbers for search)
resp = client.invoke_model(
    modelId=os.getenv("EMBED_MODEL_ID"),
    body=json.dumps({"inputText": "What is your data encryption policy?", "dimensions": 512}),
)
vector = json.loads(resp["body"].read())["embedding"]
print("Embedding length:", len(vector), "| first 3 values:", vector[:3])