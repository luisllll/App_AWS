import boto3
import json
import zipfile
import os
import time
import uuid
import tempfile
from botocore.exceptions import ClientError

AWS_REGION = "eu-west-1"
IAM_ROLE_NAME = "LambdaDynamoDBRole"
LAMBDA_FOLDER = "funciones_lambda"
API_NAME = "AnunciosAPI"

# Crear clientes AWS
iam_client = boto3.client("iam", region_name=AWS_REGION)
lambda_client = boto3.client("lambda", region_name=AWS_REGION)
dynamodb_client = boto3.client("dynamodb", region_name=AWS_REGION)
apigateway_client = boto3.client("apigateway", region_name=AWS_REGION)
sts_client = boto3.client('sts')

# Obtener ID de cuenta dinámicamente
account_id = sts_client.get_caller_identity()['Account']

# 📌 1️⃣ Crear Tablas en DynamoDB
def create_dynamodb_table(table_name, key_schema, attribute_definitions):
    try:
        print(f"🔹 Creando tabla {table_name}...")
        response = dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            BillingMode="PAY_PER_REQUEST",
        )
        print(f"✅ Tabla {table_name} creada. Esperando hasta que esté activa...")
        
        # Esperar hasta que la tabla esté activa
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        
        print(f"✅ Tabla {table_name} activa y lista para usar.")
        return True
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"⚠️ Tabla {table_name} ya existe.")
        return True
    except Exception as e:
        print(f"❌ Error al crear tabla {table_name}: {e}")
        return False

# Crear tablas y verificar creación exitosa
tables_created = True
tables_created &= create_dynamodb_table(
    "Anuncios", 
    [{"AttributeName": "id", "KeyType": "HASH"}], 
    [{"AttributeName": "id", "AttributeType": "S"}]
)
tables_created &= create_dynamodb_table(
    "Comentarios", 
    [{"AttributeName": "anuncio_id", "KeyType": "HASH"}, {"AttributeName": "comentario_id", "KeyType": "RANGE"}], 
    [{"AttributeName": "anuncio_id", "AttributeType": "S"}, {"AttributeName": "comentario_id", "AttributeType": "S"}]
)

if not tables_created:
    print("❌ Error al crear tablas DynamoDB. Abortando despliegue.")
    exit(1)

# 📌 2️⃣ Crear un Rol IAM para Lambda con manejo de errores mejorado
def create_iam_role():
    role_arn = None
    try:
        # Verificar si el rol ya existe
        try:
            role = iam_client.get_role(RoleName=IAM_ROLE_NAME)
            role_arn = role['Role']['Arn']
            print(f"⚠️ Rol {IAM_ROLE_NAME} ya existe.")
        except iam_client.exceptions.NoSuchEntityException:
            # Crear el rol si no existe
            assume_role_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                ],
            }
            
            print(f"🔹 Creando rol IAM {IAM_ROLE_NAME}...")
            response = iam_client.create_role(
                RoleName=IAM_ROLE_NAME, 
                AssumeRolePolicyDocument=json.dumps(assume_role_policy)
            )
            role_arn = response["Role"]["Arn"]
            print(f"✅ Rol {IAM_ROLE_NAME} creado con ARN: {role_arn}")
            
            # Agregar tiempo para propagación de roles
            print(f"⏳ Esperando 45 segundos para propagación del rol...")
            time.sleep(45)
        
        # Añadir políticas necesarias
        print("🔹 Asignando políticas básicas al rol...")
        policies = [
            "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            "arn:aws:iam::aws:policy/AmazonDynamoDBReadOnlyAccess",
            "arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess"
        ]
        
        for policy in policies:
            try:
                iam_client.attach_role_policy(RoleName=IAM_ROLE_NAME, PolicyArn=policy)
            except Exception as e:
                print(f"⚠️ Error al adjuntar política {policy}: {e}")
        
        print("✅ Políticas adjuntadas al rol.")
        
        return role_arn
    except Exception as e:
        print(f"❌ Error al crear rol IAM: {e}")
        return None

role_arn = create_iam_role()
if not role_arn:
    print("❌ Error al crear/obtener rol IAM. Abortando despliegue.")
    exit(1)

# 📌 3️⃣ Crear Funciones Lambda con manejo de errores mejorado - CORREGIDO PARA WINDOWS
def create_lambda_function(function_name, lambda_code):
    try:
        print(f"🔹 Creando función Lambda {function_name}...")
        
        # Verificar si la función ya existe
        try:
            lambda_client.get_function(FunctionName=function_name)
            print(f"⚠️ Función Lambda {function_name} ya existe. Actualizando código...")
            
            # Crear directorio temporal usando tempfile para compatibilidad multiplataforma
            temp_dir = tempfile.gettempdir()
            zip_file = os.path.join(temp_dir, f"{function_name}_{uuid.uuid4()}.zip")
            
            # Crear archivo ZIP
            with zipfile.ZipFile(zip_file, "w") as z:
                z.writestr("lambda_function.py", lambda_code)
            
            # Leer el archivo ZIP
            with open(zip_file, "rb") as f:
                zipped_code = f.read()
            
            # Actualizar la función Lambda
            lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zipped_code
            )
            
            # Limpiar archivo temporal
            try:
                os.remove(zip_file)
            except Exception as e:
                print(f"⚠️ No se pudo eliminar el archivo temporal {zip_file}: {e}")
                
            print(f"✅ Función Lambda {function_name} actualizada.")
            
        except lambda_client.exceptions.ResourceNotFoundException:
            # Crear nueva función Lambda
            temp_dir = tempfile.gettempdir()
            zip_file = os.path.join(temp_dir, f"{function_name}_{uuid.uuid4()}.zip")
            
            # Crear archivo ZIP
            with zipfile.ZipFile(zip_file, "w") as z:
                z.writestr("lambda_function.py", lambda_code)
            
            # Leer el archivo ZIP
            with open(zip_file, "rb") as f:
                zipped_code = f.read()
            
            # Crear la función Lambda
            lambda_client.create_function(
                FunctionName=function_name,
                Runtime="python3.12",
                Role=role_arn,
                Handler="lambda_function.lambda_handler",
                Code={"ZipFile": zipped_code},
                Timeout=10,
                MemorySize=128,
            )
            
            # Limpiar archivo temporal
            try:
                os.remove(zip_file)
            except Exception as e:
                print(f"⚠️ No se pudo eliminar el archivo temporal {zip_file}: {e}")
                
            print(f"✅ Función Lambda {function_name} creada.")
            
            # Esperar a que la función sea creada y esté lista
            print(f"⏳ Esperando a que la función {function_name} esté lista...")
            time.sleep(5)
        
        # Dar permiso a API Gateway para invocar Lambda
        try:
            lambda_client.add_permission(
                FunctionName=function_name,
                StatementId=f"apigateway-invoke-{function_name}-{int(time.time())}",
                Action="lambda:InvokeFunction",
                Principal="apigateway.amazonaws.com",
                SourceArn=f"arn:aws:execute-api:{AWS_REGION}:{account_id}:*/*/*/*"
            )
            print(f"✅ Permisos de invocación añadidos a {function_name}.")
        except lambda_client.exceptions.ResourceConflictException:
            print(f"⚠️ Los permisos de invocación ya existen para {function_name}.")
        
        return True
    except Exception as e:
        print(f"❌ Error al crear/actualizar función Lambda {function_name}: {e}")
        return False

# Código de cada función Lambda
lambda_functions = {
    "listar_anuncios": '''
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
''',
    "ver_anuncio": '''
import json
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Anuncios')

def lambda_handler(event, context):
    try:
        # Verificar si 'pathParameters' está presente antes de acceder a 'id'
        anuncio_id = event.get('pathParameters', {}).get('id')

        if not anuncio_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "El ID del anuncio no fue proporcionado correctamente"})
            }

        # Buscar el anuncio en DynamoDB
        response = table.get_item(Key={'id': anuncio_id})

        # Si no existe, devolver un error 404
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
''',
    "crear_anuncio": '''
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
''',
    "listar_comentarios": '''
import json
import boto3

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
        
        response = table.query(
            KeyConditionExpression='anuncio_id = :anuncio_id',
            ExpressionAttributeValues={':anuncio_id': anuncio_id}
        )

        return {
            "statusCode": 200,
            "body": json.dumps(response.get('Items', []))
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
''',
    "crear_comentario": '''
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
'''
}

# Crear cada función Lambda
all_lambdas_created = True
for function_name, code in lambda_functions.items():
    all_lambdas_created &= create_lambda_function(function_name, code)

if not all_lambdas_created:
    print("❌ Error al crear/actualizar algunas funciones Lambda. Continuando con precaución...")

# 📌 4️⃣ Crear API Gateway con manejo de errores mejorado
def create_api_gateway():
    try:
        # Verificar si la API ya existe
        apis = apigateway_client.get_rest_apis()
        for api in apis.get('items', []):
            if api['name'] == API_NAME:
                print(f"⚠️ API Gateway {API_NAME} ya existe. Usando existente.")
                return api['id']

        # Crear nueva API
        print(f"🔹 Creando API Gateway {API_NAME}...")
        response = apigateway_client.create_rest_api(
            name=API_NAME, 
            description="API para anuncios con comentarios", 
            endpointConfiguration={"types": ["REGIONAL"]}
        )
        print(f"✅ API Gateway {API_NAME} creada con ID: {response['id']}")
        return response["id"]
    except Exception as e:
        print(f"❌ Error al crear API Gateway: {e}")
        return None

api_id = create_api_gateway()
if not api_id:
    print("❌ Error al crear API Gateway. Abortando despliegue.")
    exit(1)

print(f"⏳ Esperando a que la API esté lista...")
time.sleep(10)

# Obtener el ID raíz de la API
try:
    api_resources = apigateway_client.get_resources(restApiId=api_id)
    root_id = [res["id"] for res in api_resources["items"] if res["path"] == "/"][0]
    print(f"✅ Recurso raíz de la API encontrado: {root_id}")
except Exception as e:
    print(f"❌ Error al obtener recurso raíz de la API: {e}")
    exit(1)

def create_resource(parent_id, path_part):
    try:
        # Verificar si el recurso ya existe
        resources = apigateway_client.get_resources(restApiId=api_id)
        for resource in resources['items']:
            if resource.get('parentId') == parent_id and resource.get('pathPart') == path_part:
                print(f"⚠️ Recurso /{path_part} ya existe. Usando existente.")
                return resource['id']
        
        # Crear nuevo recurso
        print(f"🔹 Creando recurso /{path_part}...")
        response = apigateway_client.create_resource(
            restApiId=api_id, 
            parentId=parent_id, 
            pathPart=path_part
        )
        print(f"✅ Recurso /{path_part} creado con ID: {response['id']}")
        return response["id"]
    except Exception as e:
        print(f"❌ Error al crear recurso /{path_part}: {e}")
        return None

# Crear recursos en API Gateway
anuncios_id = create_resource(root_id, "anuncios")
if not anuncios_id:
    print("❌ Error al crear recurso /anuncios. Abortando despliegue.")
    exit(1)

anuncio_id = create_resource(anuncios_id, "{id}")
if not anuncio_id:
    print("❌ Error al crear recurso /anuncios/{id}. Abortando despliegue.")
    exit(1)

comentarios_id = create_resource(anuncio_id, "comentarios")
if not comentarios_id:
    print("❌ Error al crear recurso /anuncios/{id}/comentarios. Abortando despliegue.")
    exit(1)

# 📌 5️⃣ Configurar Métodos y Aplicar la Plantilla de Mapeo con manejo de errores mejorado
def create_method(resource_id, method, function_name, request_template):
    """
    Crea un método HTTP en API Gateway, lo asocia con una función Lambda
    y aplica una plantilla de asignación para el request.
    """
    try:
        # Verificar si el método ya existe
        try:
            apigateway_client.get_method(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod=method
            )
            print(f"⚠️ Método {method} ya existe en el recurso. Omitiendo creación.")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] != 'NotFoundException':
                raise e
        
        print(f"🔹 Creando método {method}...")
        
        # Crear método
        apigateway_client.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=method,
            authorizationType="NONE",
            apiKeyRequired=False
        )
        
        # Crear integración con Lambda
        lambda_arn = f"arn:aws:lambda:{AWS_REGION}:{account_id}:function:{function_name}"
        
        apigateway_client.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=method,
            type="AWS",
            integrationHttpMethod="POST",
            uri=f"arn:aws:apigateway:{AWS_REGION}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations",
            requestTemplates={"application/json": request_template}
        )
        
        # Configurar respuesta del método
        apigateway_client.put_method_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=method,
            statusCode="200",
            responseModels={"application/json": "Empty"}
        )
        
        # Configurar respuesta de la integración
        apigateway_client.put_integration_response(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=method,
            statusCode="200",
            responseTemplates={"application/json": ""}  # Plantilla vacía para no modificar la respuesta
        )
        
        # Añadir CORS (importante para acceso desde navegadores)
        try:
            # Verificar si OPTIONS ya existe
            try:
                apigateway_client.get_method(
                    restApiId=api_id,
                    resourceId=resource_id,
                    httpMethod="OPTIONS"
                )
                print(f"⚠️ Método OPTIONS ya existe para este recurso.")
            except ClientError as e:
                if e.response['Error']['Code'] == 'NotFoundException':
                    # Crear método OPTIONS para CORS
                    apigateway_client.put_method(
                        restApiId=api_id,
                        resourceId=resource_id,
                        httpMethod="OPTIONS",
                        authorizationType="NONE"
                    )
                    
                    apigateway_client.put_method_response(
                        restApiId=api_id,
                        resourceId=resource_id,
                        httpMethod="OPTIONS",
                        statusCode="200",
                        responseParameters={
                            "method.response.header.Access-Control-Allow-Origin": True,
                            "method.response.header.Access-Control-Allow-Methods": True,
                            "method.response.header.Access-Control-Allow-Headers": True
                        },
                        responseModels={"application/json": "Empty"}
                    )
                    
                    apigateway_client.put_integration(
                        restApiId=api_id,
                        resourceId=resource_id,
                        httpMethod="OPTIONS",
                        type="MOCK",
                        requestTemplates={"application/json": '{"statusCode": 200}'}
                    )
                    
                    apigateway_client.put_integration_response(
                        restApiId=api_id,
                        resourceId=resource_id,
                        httpMethod="OPTIONS",
                        statusCode="200",
                        responseParameters={
                            "method.response.header.Access-Control-Allow-Origin": "'*'",
                            "method.response.header.Access-Control-Allow-Methods": "'GET,POST,OPTIONS'",
                            "method.response.header.Access-Control-Allow-Headers": "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
                        },
                        responseTemplates={"application/json": ""}
                    )
                else:
                    raise e
            
        except Exception as e:
            print(f"⚠️ Error al configurar CORS para {method}: {e}")
        
        print(f"✅ Método {method} creado y configurado correctamente.")
        return True
    except Exception as e:
        print(f"❌ Error al crear método {method}: {e}")
        return False

# Configurar métodos y plantillas - con control de errores
all_methods_created = True

# Para /anuncios
all_methods_created &= create_method(
    anuncios_id, 
    "GET", 
    "listar_anuncios", 
    '{ "body": $input.json("$") }'
)
all_methods_created &= create_method(
    anuncios_id, 
    "POST", 
    "crear_anuncio", 
    '{ "body": $input.json("$") }'
)

# Para /anuncios/{id}
all_methods_created &= create_method(
    anuncio_id, 
    "GET", 
    "ver_anuncio", 
    '{ "pathParameters": { "id": "$input.params(\'id\')" } }'
)

# Para /anuncios/{id}/comentarios
all_methods_created &= create_method(
    comentarios_id, 
    "GET", 
    "listar_comentarios", 
    '{ "pathParameters": { "id": "$input.params(\'id\')" } }'
)
all_methods_created &= create_method(
    comentarios_id, 
    "POST", 
    "crear_comentario", 
    '{ "pathParameters": { "id": "$input.params(\'id\')" }, "body": $input.json("$") }'
)

if not all_methods_created:
    print("⚠️ Algunos métodos no se pudieron crear correctamente. Continuando con precaución...")

# 📌 6️⃣ Implementar la API con manejo de errores
try:
    print("🔹 Desplegando API en la etapa 'prod'...")
    deployment = apigateway_client.create_deployment(
        restApiId=api_id, 
        stageName="prod", 
        description="API de anuncios con comentarios"
    )
    print(f"✅ API desplegada en la etapa 'prod' con ID de despliegue: {deployment['id']}")
except Exception as e:
    print(f"❌ Error al desplegar la API: {e}")

# Mostrar información final
print("\n" + "="*50)
print("🚀 **Despliegue completado** 🎯")
print("="*50)
print(f"📌 API_ID: {api_id}")
print(f"📌 URL de la API: https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com/prod/")
print("📌 Endpoints disponibles:")
print(f"   - GET    https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com/prod/anuncios")
print(f"   - POST   https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com/prod/anuncios")
print(f"   - GET    https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com/prod/anuncios/{{id}}")
print(f"   - GET    https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com/prod/anuncios/{{id}}/comentarios")
print(f"   - POST   https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com/prod/anuncios/{{id}}/comentarios")
print("="*50)
print("Ejemplos de uso con curl:")
print(f"curl -X POST \"https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com/prod/anuncios\" -H \"Content-Type: application/json\" -d \"{{\\\"titulo\\\": \\\"Prueba 1\\\", \\\"descripcion\\\": \\\"Esta es una descripción de prueba.\\\"}}\"")
print(f"curl -X GET \"https://{api_id}.execute-api.{AWS_REGION}.amazonaws.com/prod/anuncios\"")
print(f"curl -X GET \"https://[API_ID].execute-api.eu-west-1.amazonaws.com/prod/anuncios/[ID_DEL_ANUNCIO]\"")
print(f"curl -X GET \"https://[API_ID].execute-api.eu-west-1.amazonaws.com/prod/anuncios/[ID_DEL_ANUNCIO]/comentarios" \
-H "Content-Type: application/json" \
-d '{"usuario": "Maria", "mensaje": "¿Podría ver el coche este fin de semana?"}'")"
print(f"curl -X GET \"https://[API_ID].execute-api.eu-west-1.amazonaws.com/prod/anuncios/[ID_DEL_ANUNCIO]/comentarios\"")