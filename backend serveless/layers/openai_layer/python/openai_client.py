from openai import OpenAI

def get_openai_client(): # You can also use AWS Secrets Manager to fetch this key securely
    return OpenAI
