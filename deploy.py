import boto3
import json
import zipfile
import os
import time

AWS_REGION = "eu-west-1"
IAM_ROLE_NAME = "LambdaDynamoDBRole"
LAMBDA_FOLDER = "funciones_lambda"
API_NAME = "AnunciosAPI"

# Crear clientes AWS
iam_client = boto3.client("iam", region_name=AWS_REGION)
lambda_client = boto3.client("lambda", region_name=AWS_REGION)
dynamodb_client = boto3.client("dynamodb", region_name=AWS_REGION)
apigateway_client = boto3.client("apigateway", region_name=AWS_REGION)

# 📌 1️⃣ Crear Tablas en DynamoDB
def create_dynamodb_table(table_name, key_schema, attribute_definitions):
    try:
        dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions,
            BillingMode="PAY_PER_REQUEST",
        )
        print(f"✅ Tabla {table_name} creada.")
        time.sleep(5)
    except dynamodb_client.exceptions.ResourceInUseException:
        print(f"⚠️ Tabla {table_name} ya existe.")

create_dynamodb_table("Anuncios", [{"AttributeName": "id", "KeyType": "HASH"}], [{"AttributeName": "id", "AttributeType": "S"}])
create_dynamodb_table("Comentarios", [{"AttributeName": "anuncio_id", "KeyType": "HASH"}, {"AttributeName": "comentario_id", "KeyType": "RANGE"}], [{"AttributeName": "anuncio_id", "AttributeType": "S"}, {"AttributeName": "comentario_id", "AttributeType": "S"}])

# 📌 2️⃣ Crear un Rol IAM para Lambda
def create_iam_role():
    try:
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
        response = iam_client.create_role(RoleName=IAM_ROLE_NAME, AssumeRolePolicyDocument=json.dumps(assume_role_policy))

        # Agregar permisos básicos
        iam_client.attach_role_policy(RoleName=IAM_ROLE_NAME, PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")

        print(f"✅ Rol {IAM_ROLE_NAME} creado. Esperando 30 segundos para propagación...")
        time.sleep(30)
        return response["Role"]["Arn"]

    except iam_client.exceptions.EntityAlreadyExistsException:
        print(f"⚠️ Rol {IAM_ROLE_NAME} ya existe.")
        return f"arn:aws:iam::{boto3.client('sts').get_caller_identity()['Account']}:role/{IAM_ROLE_NAME}"

role_arn = create_iam_role()

# 📌 3️⃣ Crear Funciones Lambda
def create_lambda_function_from_folder(folder, function_name):
    try:
        zip_file = f"{function_name}.zip"
        with zipfile.ZipFile(zip_file, "w") as z:
            z.write(os.path.join(folder, f"{function_name}.py"), arcname="lambda_function.py")

        with open(zip_file, "rb") as f:
            zipped_code = f.read()

        lambda_client.create_function(
            FunctionName=function_name,
            Runtime="python3.12",
            Role=role_arn,
            Handler="lambda_function.lambda_handler",
            Code={"ZipFile": zipped_code},
            Timeout=10,
            MemorySize=128,
        )
        print(f"✅ Función Lambda {function_name} creada.")
    except lambda_client.exceptions.ResourceConflictException:
        print(f"⚠️ Función {function_name} ya existe.")

lambda_files = [f.replace(".py", "") for f in os.listdir(LAMBDA_FOLDER) if f.endswith(".py")]
for function in lambda_files:
    create_lambda_function_from_folder(LAMBDA_FOLDER, function)

# 📌 4️⃣ Asignar permisos IAM correctos a cada función Lambda
def attach_lambda_permissions():
    read_only_functions = ["listar_anuncios", "listar_comentarios", "ver_anuncio"]
    write_functions = ["crear_anuncio", "crear_comentario"]

    for function in read_only_functions:
        print(f"🔹 Asignando permiso de SOLO LECTURA a {function}")
        iam_client.attach_role_policy(RoleName=IAM_ROLE_NAME, PolicyArn="arn:aws:iam::aws:policy/AmazonDynamoDBReadOnlyAccess")

    for function in write_functions:
        print(f"🔹 Asignando permiso de ESCRITURA a {function}")
        iam_client.attach_role_policy(RoleName=IAM_ROLE_NAME, PolicyArn="arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess")

    print("✅ Permisos de IAM asignados a las funciones Lambda.")

attach_lambda_permissions()

# 📌 5️⃣ Crear API Gateway y Recursos
def create_api_gateway():
    try:
        response = apigateway_client.create_rest_api(name=API_NAME, description="API para anuncios con comentarios", endpointConfiguration={"types": ["REGIONAL"]})
        print(f"✅ API Gateway {API_NAME} creada.")
        return response["id"]
    except Exception as e:
        print(f"❌ Error al crear API Gateway: {e}")

api_id = create_api_gateway()
time.sleep(5)

# Obtener el ID raíz de la API
api_resources = apigateway_client.get_resources(restApiId=api_id)
root_id = [res["id"] for res in api_resources["items"] if res["path"] == "/"][0]

def create_resource(parent_id, path_part):
    response = apigateway_client.create_resource(restApiId=api_id, parentId=parent_id, pathPart=path_part)
    print(f"✅ Recurso creado: /{path_part}")
    return response["id"]

# Crear recursos en API Gateway
anuncios_id = create_resource(root_id, "anuncios")
anuncio_id = create_resource(anuncios_id, "{id}")
comentarios_id = create_resource(anuncio_id, "comentarios")

# 📌 6️⃣ Configurar Métodos y Aplicar la Plantilla de Mapeo

def create_method(resource_id, method, function_name, request_template):
    """
    Crea un método HTTP en API Gateway, lo asocia con una función Lambda
    y aplica una plantilla de asignación para el request.
    """
    apigateway_client.put_method(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod=method,
        authorizationType="NONE"
    )

    lambda_arn = f"arn:aws:lambda:{AWS_REGION}:476114158524:function:{function_name}"
    
    # 📌 Configurar integración con la plantilla de mapeo
    apigateway_client.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod=method,
        type="AWS",
        integrationHttpMethod="POST",
        uri=f"arn:aws:apigateway:{AWS_REGION}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations",
        requestTemplates={"application/json": request_template}  # 🔥 Se asigna la plantilla aquí
    )

    # 📌 Configurar respuesta para que API Gateway transforme los datos correctamente
    apigateway_client.put_method_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod=method,
        statusCode="200",
        responseModels={"application/json": "Empty"}
    )

    apigateway_client.put_integration_response(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod=method,
        statusCode="200",
        responseTemplates={"application/json": request_template}
    )

    print(f"✅ Método {method} /{function_name} creado con plantilla de mapeo.")

# 📌 Llamadas a la función con las plantillas correctas
create_method(anuncios_id, "GET", "listar_anuncios", '{ "body": $input.json("$") }')
create_method(anuncios_id, "POST", "crear_anuncio", '{ "body": $input.json("$") }')
create_method(anuncio_id, "GET", "ver_anuncio", '{ "pathParameters": { "id": "$input.params(\'id\')" } }')
create_method(comentarios_id, "GET", "listar_comentarios", '{ "pathParameters": { "id": "$input.params(\'id\')" } }')
create_method(comentarios_id, "POST", "crear_comentario", '{ "pathParameters": { "id": "$input.params(\'id\')" }, "body": $input.json("$") }')





# 📌 7️⃣ Implementar la API
apigateway_client.create_deployment(restApiId=api_id, stageName="prod", description="API de anuncios con comentarios")
print(f"✅ API desplegada en la etapa 'prod'.")

print("🚀 **Despliegue COMPLETO con éxito.** 🎯")

print(f"📌 API_ID: {api_id}")

