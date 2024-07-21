import json
import boto3
import time
import urllib.parse
from botocore.exceptions import ClientError
import threading


# Create a DynamoDB Client
dynamodb = boto3.resource('dynamodb')
lambda_client = boto3.client('lambda')

# sns = boto3.client('sns')


def get_existing_user(dynamodb, user_id):
    """Get an existing number from DynamoDB"""
    table = dynamodb.Table('user_data')
    try:
        response = table.get_item(
            Key={
                'user_id': user_id
            }
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
        return None
    else:
        return response.get('Item')


def handle_unauthorized():
    """Handle unauthorized requests"""
    return {
        'statusCode': 403,
        'body': json.dumps('Unauthorized')
    }


def handle_quota_reached_subscription():
    """Handle maximum message number reached"""
    return {
        'statusCode': 403,
        'body': json.dumps('Maximum number of messages used')
    }


def call_lambda(lambda_client, message, user_id):
    message_object = {
        "message": message,
        "user_id": user_id
    }
    try:
        response = lambda_client.invoke(
            FunctionName='message-processor',
            InvocationType='RequestResponse',
            Payload=json.dumps(message_object)
        )
        
        # Read the response payload and ensure it's a dictionary
        response_payload = json.loads(response['Payload'].read().decode('utf-8'))
        print("Response from invoked lambda:", response_payload)
        return response_payload
    except Exception as e:
        print(f"Error invoking Lambda: {str(e)}")
        raise e

# def publish_successful_message(sns, message, user_id):
#     """Publish a message to an SNS FIFO topic and a standard SNS topic in parallel using threading.

#     Args:
#         sns: An AWS SNS client instance.
#         message_body: The body of the message to publish.
#         user_id: The originating number which is used as the MessageGroupId for the FIFO topic.

#     Raises:
#         Exception: If the message fails to publish to either topic.
#     """
#     print(f'Publishing message: {message} to {user_id}')

#     deduplication_id = str(time.time())
#     message_process_topic_arn1 = 'arn:aws:sns:us-east-1:507037884969:incomming-messages.fifo'
#     message_process_topic_arn2 = 'arn:aws:sns:us-east-1:507037884969:incomming-message'

#     message_object = {
#         "message": message,
#         "userId": user_id
#     }

#     def publish_to_topic(topic_arn, is_fifo):
#         publish_params = {
#             "TopicArn": topic_arn,
#             "Message": json.dumps(message_object)
#         }
#         if is_fifo:
#             publish_params.update({
#                 "MessageDeduplicationId": deduplication_id,
#                 "MessageGroupId": user_id
#             })
#         try:
#             response = sns.publish(**publish_params)
#             return response
#         except Exception as e:
#             print(f"Failed to publish to {topic_arn}: {e}")
#             raise

#     thread1 = threading.Thread(target=publish_to_topic, args=(
#         message_process_topic_arn1, True))
#     thread2 = threading.Thread(target=publish_to_topic, args=(
#         message_process_topic_arn2, False))

#     thread1.start()
#     thread2.start()

#     thread1.join()
#     thread2.join()


def lambda_handler(event, context):
    """Main Lambda authorizer function"""

    # Try to get the number from the incoming request
    try:
        if isinstance(event['body'], str):
            body = json.loads(event['body'])  # Parse the JSON string
        elif isinstance(event['body'], dict):
            body = event['body']  # Use the dict directly
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid body format'})
            }
        user_id = body['userId']
        message = body['message']
    except KeyError:
        return {
            'statusCode': 400,
            'body': json.dumps('Missing User Id')
        }

    existing_user = get_existing_user(dynamodb, user_id)
    
    print(existing_user)

    # If the number is not registered, deny the request
    if not existing_user:
        return handle_unauthorized()

     # If the number is not active, deny the request
    if not ('status' in existing_user):
        return handle_unauthorized()

     # If the number is not active, deny the request
    if existing_user['status'] != 'active':
        return handle_quota_reached_subscription()
        
        
    if existing_user['available_messages'] <= 0:
        return handle_quota_reached_subscription()
        
     # Publish the message to the SNS topic
    # publish_successful_message(sns, message, user_id)
    
    print({
        message,
        user_id
    })
    
    # When returning the final result:
    invoke_result = call_lambda(lambda_client, message, user_id)
    print(invoke_result)

    # Check if the invoke_result is a string, decode it if so
    if isinstance(invoke_result, str):
        try:
            # Attempt to decode the JSON string into a dictionary
            invoke_result = json.loads(invoke_result)
        except json.JSONDecodeError:
            # If it's not JSON, wrap it in a dictionary
            invoke_result = {"message": invoke_result}
    elif not isinstance(invoke_result, dict):
        # If it's neither string nor dict, make sure it's treated as a plain message
        invoke_result = {"message": str(invoke_result)}
        
    return {
       'statusCode': 200,
        'headers': {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True,
        },
        'body': json.dumps({"message": invoke_result.get("message", "")})
    }
