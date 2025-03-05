import json
import boto3
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Comentarios')

def lambda_handler(event, context):
    try:
        
        anuncio_id = event.get('pathParameters', {}).get('id')
        if not anuncio_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "El ID del anuncio no fue proporcionado correctamente"})
            }


        body = event.get('body', {})
        if isinstance(body, str):
            data = json.loads(body)  # Si es string, convertir a diccionario
        else:
            data = body  # Si ya es diccionario, usarlo directamente

        usuario = data.get('usuario')
        mensaje = data.get('mensaje')
        if not usuario or not mensaje:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Faltan datos en la solicitud"})
            }

 
        comentario = {
            'anuncio_id': anuncio_id,
            'comentario_id': str(uuid.uuid4()),
            'usuario': usuario,
            'mensaje': mensaje,
            'fecha': datetime.utcnow().isoformat()
        }

        #Guardar en DynamoDB
        table.put_item(Item=comentario)

        return {
            "statusCode": 200,
            "body": json.dumps(comentario)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
