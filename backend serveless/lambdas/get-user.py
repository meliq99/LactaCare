import json
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal

# Create a DynamoDB Client
dynamodb = boto3.resource('dynamodb')

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)  # or use int(o) if you are sure it's an integer
        return super(DecimalEncoder, self).default(o)

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

def create_user(dynamodb, user_id):
    """Create a new user in DynamoDB"""
    table = dynamodb.Table('user_data')
    try:
        # Example user data; customize as necessary
        user_data = {
            'user_id': user_id,
            'status': 'active',
            'user_thread': '',
            'available_messages': Decimal(10),
            'country': '',
        }
        table.put_item(Item=user_data)
        return user_data
    except ClientError as e:
        print(e.response['Error']['Message'])
        return None

def lambda_handler(event, context):
    # Extract headers from the event
    headers = event.get('headers', {})
    
    # Get the Authorization header, default to None if not present
    auth_header = headers.get('Authorization', None)

    # Get user from DynamoDB
    user = get_existing_user(dynamodb, auth_header)

    #Create user if not present
    if not user:
        print(f"No existing user found for ID {auth_header}, creating one.")
        user = create_user(dynamodb, auth_header)
    
    return {
        'statusCode': 200,
        'headers': {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": True,
        },
        'body': json.dumps(user, cls=DecimalEncoder)
    }
