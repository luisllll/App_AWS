# PASOS A SEGUIR #


1. ## Crear tablas en DYNAMODB ##
 Tabla "Anuncios" que almacena anuncios y comentarios.
  - partition_key: id tipo String.

 Tabla "Comentarios" que almacena anuncios y comentarios.
  - partition_key: anuncio_id tipo String.
  - sort_key: comentario_id tipo String.



2. ## Crear las Funciones Lambda ##
    Cada función Lambda manejará a un endpoint de la API.

    1. Crear función 'listar_anuncios'
    - im1
    - im2

    2. Crear función 'ver_anuncio'
    - im2

    3. Crear la función 'crear_anuncio'
    - im2

    4. Crear la función 'listar_comentarios'
    - im2

    5. Crear la función 'crear_comentario'
    - im2


3. ## Configurar API Gateway ##
    Conectamos los endpoints con las funciones lambda.

    1. Crear API CON API Gateway.
        - Seleccionar 'API REST' llamándola 'AnunciosAPI'.

    2. Crear los endpoints.
     - Crear recurso.
        - Nombre: anuncios
        - path: /anuncios
        - Crear método GET
            - Click en 'crear método'
            - Tipo de método: GET
            - Click en 'Función de Lambda'
            - Función de Lambda: 'listar_anuncios'
            - Click en 'crear método' 
        - Crear Método POST
            - Click en 'crear método'
            - Tipo de método: POST
            - Click en 'Función de Lambda'
            - Función de Lambda: 'crear_anuncio'
            - En 'Plantillas de Mapeo', añadir el siguiente contenido:
                {
                    "body": $input.json('$')
                }
            - Click en 'crear método'


        - Crear recurso {id} dentro de 'anuncios'
            - Crear método GET y conectarlo a la función 'ver_anuncio'.
                - En 'Plantillas de Mapeo', añadir el siguiente contenido:
                    {
                        "pathParameters": {
                            "id": "$input.params('id')"
                        }
                    }

        - Crear recurso 'comentarios' dentro de anuncios/{id}
            - Crear método GET y conectarlo a la función 'listar_comentarios'.
                - En 'Plantillas de Mapeo', añadir el siguiente contenido:
                    {
                        "pathParameters": {
                            "id": "$input.params('id')"
                        }
                    }

            - Crear método POST y conectarlo a la función 'crear_comentario'.
                - En 'Plantillas de Mapeo', añadir el siguiente contenido:
                    {
                        "pathParameters": {
                            "id": "$input.params('id')"
                        },
                        "body": $input.json('$')
                    }


    2. Desplegar API.
        - Desde 'AnunciosAPI', click en 'Implementar API'
        - 'Etapa' -> 'Nueva Etapa'
        - 'Nombre' -> prod
        - Descripción -> 'Api Anuncios'


5. ## Asignar permisos ##
    1. usando 'IAM' pulsar en 'roles', seleccionar 'crear_anuncio', pulsar 'agregar permisos' y seleccionar 'AmazonDynamoDBFullAccess'. Pulsar en 'Agregar permisos'

    2. usando 'IAM' pulsar en 'roles', seleccionar 'listar_anuncios', pulsar 'agregar permisos' y seleccionar 'AmazonDynamoDBReadOnlyAccess'. Pulsar en 'Agregar permisos'

    3. usando 'IAM' pulsar en 'roles', seleccionar 'listar_comentarios', pulsar 'agregar permisos' y seleccionar 'AmazonDynamoDBReadOnlyAccess'. Pulsar en 'Agregar permisos'

    4. usando 'IAM' pulsar en 'roles', seleccionar 'ver_anuncio', pulsar 'agregar permisos' y seleccionar 'AmazonDynamoDBReadOnlyAccess'. Pulsar en 'Agregar permisos'

    5. usando 'IAM' pulsar en 'roles', seleccionar 'crear_comentario', pulsar 'agregar permisos' y seleccionar 'AmazonDynamoDBFullAccess'. Pulsar en 'Agregar permisos'



4. ## Probar la API ##
    1. Copiar la url de la api.

    2. Probar POST /anuncios

    curl -X POST "https://7d82ges3t7.execute-api.eu-west-1.amazonaws.com/prod/anuncios" -H "Content-Type: application/json" -d "{\"titulo\": \"Prueba 1\", \"descripcion\": \"Esta es una descripción de prueba.\"}"


    3. Probar GET /anuncios

    curl -X GET "https://7d82ges3t7.execute-api.eu-west-1.amazonaws.com/prod/anuncios"

    4. Probar GET /anuncios/{id}

    curl -X GET "https://7d82ges3t7.execute-api.eu-west-1.amazonaws.com/prod/anuncios/9fd2c650-bd90-4d4a-b10c-9f59d89acd6b"


    5. Probar POST /anuncios/{id}/comentarios

    curl -X POST "https://7d82ges3t7.execute-api.eu-west-1.amazonaws.com/prod/anuncios/9fd2c650-bd90-4d4a-b10c-9f59d89acd6b/comentarios" -H "Content-Type: application/json" -d "{\"usuario\": \"Usuario prueba post comentario\", \"mensaje\": \"prueba de comentario 2\"}"



    6. Probar GET /anuncios/{id}/comentarios

    curl -X GET "https://7d82ges3t7.execute-api.eu-west-1.amazonaws.com/prod/anuncios/9fd2c650-bd90-4d4a-b10c-9f59d89acd6b/comentarios"






        
    




