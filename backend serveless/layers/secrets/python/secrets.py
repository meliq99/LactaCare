import boto3
import json
from botocore.exceptions import ClientError

def get_openai_secret(secret_key):
    secret_name = "prod/openai_api_key"
    region_name = "us-east-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name="secretsmanager", region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name)
    except ClientError as e:
        raise e
    else:
        if "SecretString" in get_secret_value_response:
            secret = json.loads(get_secret_value_response["SecretString"])
            return secret[secret_key]
        else:
            raise ValueError("Secret string not found")

openai_secrets = {
    "openai_api_key": get_openai_secret('openai_api_key')
}
