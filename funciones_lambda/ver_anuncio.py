import json
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Anuncios')

def lambda_handler(event, context):
    try:
        # 🔹 Verificar si 'pathParameters' está presente antes de acceder a 'id'
        anuncio_id = event.get('pathParameters', {}).get('id')

        if not anuncio_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "El ID del anuncio no fue proporcionado correctamente"})
            }

        # 🔹 Buscar el anuncio en DynamoDB
        response = table.get_item(Key={'id': anuncio_id})

        # 🔹 Si no existe, devolver un error 404
        if 'Item' not in response:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Anuncio no encontrado"})
            }

        return {
            "statusCode": 200,
            "body": json.dumps(response['Item'])
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
