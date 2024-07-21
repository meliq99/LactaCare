import json
import boto3
import time
from openai_client import get_openai_client
from secrets import openai_secrets
from botocore.exceptions import ClientError

LACTA_CARE_ASSISTANT_ID = "asst_c4N9UmFt0bvn2dfb6XeqfQMP"

dynamodb = boto3.resource("dynamodb")
clients_table = dynamodb.Table("user_data")


# OpenAI API Configuration
openai_api_key = openai_secrets["openai_api_key"]
openai = get_openai_client()
openai_client = openai(api_key=openai_api_key)


def get_user_data(user_id):
    try:
        response = clients_table.get_item(Key={"user_id": user_id})
        if "Item" in response:
            return response["Item"]
        else:
            return None
    except ClientError as e:
        print(e.response["Error"]["Message"])
        return None


def lambda_handler(event, context):
    try:
        user_id = event['user_id']
        user_message = event['message']
    except KeyError:
        print("Error: Missing userId or message in the payload")
        return json.dumps("Error: Missing userId or message in the payload")

    user_data = get_user_data(user_id)
    
    print(user_data)
    
    # Get user_thread from user_data if it exists
    if user_data:
        user_thread = user_data.get("user_thread")
    else:
        user_thread = None
        
        
    if not user_thread:
        conversation_thread = openai_client.beta.threads.create()
        thread_id = conversation_thread.id
        clients_table.put_item(
            Item={"user_id": user_id, 
            "status": user_data.get("status"), 
            "user_thread": thread_id, 
            "available_messages": user_data.get("available_messages"),
            "country": user_data.get('country'),
            }
        )
    else:
        thread_id = user_thread

        
    # Add message to the conversation thread
    openai_client.beta.threads.messages.create(
        thread_id=thread_id, role="user", content=user_message
    )

    # Create a new run
    run = openai_client.beta.threads.runs.create(
        thread_id=thread_id, assistant_id=LACTA_CARE_ASSISTANT_ID
    )

    # Optimized polling
    while run.status != "completed":
        time.sleep(2)
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=thread_id, run_id=run.id
        )

    messages = openai_client.beta.threads.messages.list(
        thread_id=thread_id)

    first_option_message = messages.data[0].content[0].text.value
    
    reponse = {
        "message": first_option_message
    }
    
    clients_table.put_item(
            Item={"user_id": user_id, 
            "status": user_data.get("status"), 
            "user_thread": thread_id, 
            "available_messages": user_data.get("available_messages") - 1,
            "country": user_data.get('country'),
            }
        )
    
    print(first_option_message)
    
    return json.dumps(reponse)
