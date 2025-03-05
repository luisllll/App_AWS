import json
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Comentarios')

def lambda_handler(event, context):
    anuncio_id = event['pathParameters']['id']
    
    response = table.query(
        KeyConditionExpression='anuncio_id = :anuncio_id',
        ExpressionAttributeValues={':anuncio_id': anuncio_id}
    )

    return {
        "statusCode": 200,
        "body": json.dumps(response.get('Items', []))
    }

