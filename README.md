# App_AWS
Ejercico de creación de una aplicación de anuncios usando AWS



## Estructura del proyecto ##

📌 Estructura Final del Proyecto y Guía Paso a Paso
Dado que el chat/comentarios asociados a los anuncios es obligatorio, hemos diseñado una arquitectura serverless que cumple con todos los requisitos de la práctica, asegurando bajo costo, escalabilidad y facilidad de implementación.

1️⃣ Estructura del Proyecto
Usaremos tres servicios principales de AWS para una solución completamente serverless:

Servicio AWS	Función en el Proyecto	Motivo de Elección
API Gateway	Expone la API REST con los endpoints para anuncios y comentarios.	Servicio gestionado que permite recibir y redirigir solicitudes sin servidores.
AWS Lambda	Procesa la lógica de negocio para manejar anuncios y comentarios.	Se ejecuta solo cuando es necesario, sin costos en reposo.
DynamoDB	Almacena los anuncios y comentarios en una base de datos NoSQL.	Escalable, de bajo costo y sin necesidad de administración.
2️⃣ Arquitectura del Sistema
La siguiente arquitectura representa el flujo de datos y los servicios utilizados:

plaintext
Copiar
[ Cliente (Frontend o Postman) ]
        |
        v
[ API Gateway ] --(Requests)--> [ AWS Lambda ]
        |
        v
[ DynamoDB (Anuncios y Comentarios) ]
Cada solicitud HTTP que hace el cliente (usuario o navegador) se recibe en API Gateway, el cual activa una función Lambda. Esta función lee o escribe en DynamoDB, donde almacenamos anuncios y comentarios.

3️⃣ Endpoints de la API
Definimos cinco endpoints en API Gateway:

Método	Ruta	Descripción
GET	/anuncios	Obtiene la lista de anuncios.
GET	/anuncios/{id}	Obtiene los detalles de un anuncio.
POST	/anuncios	Publica un nuevo anuncio.
GET	/anuncios/{id}/comentarios	Obtiene los comentarios de un anuncio.
POST	/anuncios/{id}/comentarios	Agrega un comentario a un anuncio.
4️⃣ Pasos para la Creación
Ahora te guiaré paso a paso para construir el sistema en AWS.

📌 Paso 1: Crear la Base de Datos en DynamoDB
Ir a AWS DynamoDB en la consola de AWS.

Crear una nueva tabla llamada Anuncios:

Partition Key: id (tipo String).
Atributos: titulo, descripcion.
Crear otra tabla llamada Comentarios:

Partition Key: anuncio_id (tipo String).
Sort Key: comentario_id (tipo String).
Atributos: usuario, mensaje, fecha.
📌 Paso 2: Crear las Funciones AWS Lambda
Cada función Lambda se encarga de gestionar una parte del backend.

1️⃣ Obtener la lista de anuncios (GET /anuncios)
python
Copiar
import json
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Anuncios')

def lambda_handler(event, context):
    response = table.scan()
    return {
        "statusCode": 200,
        "body": json.dumps(response['Items'])
    }
2️⃣ Ver detalles de un anuncio (GET /anuncios/{id})
python
Copiar
import json
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Anuncios')

def lambda_handler(event, context):
    anuncio_id = event['pathParameters']['id']
    response = table.get_item(Key={'id': anuncio_id})
    return {
        "statusCode": 200,
        "body": json.dumps(response.get('Item', {}))
    }
3️⃣ Publicar un anuncio (POST /anuncios)
python
Copiar
import json
import boto3
import uuid

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Anuncios')

def lambda_handler(event, context):
    data = json.loads(event['body'])
    anuncio = {
        'id': str(uuid.uuid4()),
        'titulo': data['titulo'],
        'descripcion': data['descripcion']
    }
    table.put_item(Item=anuncio)
    return {
        "statusCode": 200,
        "body": json.dumps(anuncio)
    }
4️⃣ Obtener comentarios de un anuncio (GET /anuncios/{id}/comentarios)
python
Copiar
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
5️⃣ Agregar un comentario a un anuncio (POST /anuncios/{id}/comentarios)
python
Copiar
import json
import boto3
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Comentarios')

def lambda_handler(event, context):
    anuncio_id = event['pathParameters']['id']
    data = json.loads(event['body'])

    comentario = {
        'anuncio_id': anuncio_id,
        'comentario_id': str(uuid.uuid4()),
        'usuario': data['usuario'],
        'mensaje': data['mensaje'],
        'fecha': datetime.utcnow().isoformat()
    }

    table.put_item(Item=comentario)

    return {
        "statusCode": 200,
        "body": json.dumps(comentario)
    }
📌 Paso 3: Configurar API Gateway
Ir a API Gateway en AWS y crear una nueva API REST.
Crear los endpoints y asociarlos a las funciones Lambda.
Activar CORS en cada endpoint para permitir peticiones desde cualquier frontend.
Desplegar la API.
📌 Paso 4: Probar la API
Usar Postman o cURL para enviar solicitudes HTTP.
Ejemplo para publicar un anuncio (POST /anuncios):
json
Copiar
{
  "titulo": "Vendo bicicleta",
  "descripcion": "Bicicleta en buen estado, poco uso."
}
Ejemplo para agregar un comentario (POST /anuncios/{id}/comentarios):
json
Copiar
{
  "usuario": "Carlos",
  "mensaje": "¿Sigue disponible?"
}
Ver la lista de anuncios y comentarios (GET endpoints).






