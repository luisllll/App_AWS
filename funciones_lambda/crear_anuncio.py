import json
import boto3
import uuid

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Anuncios')

def lambda_handler(event, context):
    try:
        # Revisar si el body ya es un diccionario o si es string JSON
        if isinstance(event['body'], str):
            data = json.loads(event['body'])  # Si es string, convertir a diccionario
        else:
            data = event['body']  # Si ya es diccionario, usarlo directamente

        # Crear anuncio con ID único
        anuncio = {
            'id': str(uuid.uuid4()),
            'titulo': data.get('titulo', 'Sin título'),
            'descripcion': data.get('descripcion', 'Sin descripción')
        }

        # Guardar en DynamoDB
        table.put_item(Item=anuncio)

        return {
            "statusCode": 200,
            "body": json.dumps(anuncio)
        }
    except Exception as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)})
        }

