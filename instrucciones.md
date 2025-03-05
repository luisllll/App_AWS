#PASOS A SEGUIR#


1. ##Crear tablas en DYNAMODB##
 Tabla "Anuncios" que almacena anuncios y comentarios.
  - partition_key: id tipo String.

 Tabla "Comentarios" que almacena anuncios y comentarios.
  - partition_key: anuncio_id tipo String.
  - sort_key: comentario_id tipo String.



2. ##Crear las Funciones Lambda##
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


2. ##Configurar API Gateway##
    Conectamos los endpoints con las funciones lambda.

    1. Crear API CON API Gateway.
        - Seleccionar 'API REST' llamándola 'AnunciosAPI'.
    




