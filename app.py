import json
import asyncio
import httpx


def lambda_handler(event, context):
    print(event)
    # TODO implement
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
