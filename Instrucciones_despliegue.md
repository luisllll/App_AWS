# PASOS A SEGUIR

## 1. instalar el SDK de AWS en python
    pip install boto3



## 2. Configurar credenciales de AWS
    aws configure

    - Ingresar AWS_ACCESS_KEY_ID
    - Ingresar AWS_SECRET_ACCESS_KEY
    - Ingresar REGIÓN (eu-west-1)


## 3. Ejecutar deploy.py
    python deploy.py



---

## 6. Probar la API con `curl`
Después de desplegar la API, prueba los endpoints usando `curl`.

### Crear un anuncio (POST /anuncios)
curl -X POST "https://7d82ges3t7.execute-api.eu-west-1.amazonaws.com/prod/anuncios" -H "Content-Type: application/json" -d "{\"titulo\": \"Prueba 1\", \"descripcion\": \"Esta es una descripción de prueba.\"}"

### Extraer anuncios (GET /anuncios)
curl -X GET "https://7d82ges3t7.execute-api.eu-west-1.amazonaws.com/prod/anuncios"

### Extraer anuncio por ID (GET /anuncios/{id})
curl -X GET "https://7d82ges3t7.execute-api.eu-west-1.amazonaws.com/prod/anuncios/9fd2c650-bd90-4d4a-b10c-9f59d89acd6b"

### Crear comentario en un anuncio (POST /anuncios/{id}/comentarios)
curl -X POST "https://7d82ges3t7.execute-api.eu-west-1.amazonaws.com/prod/anuncios/9fd2c650-bd90-4d4a-b10c-9f59d89acd6b/comentarios" \
     -H "Content-Type: application/json" \
     -d "{\"usuario\": \"Usuario prueba post comentario\", \"mensaje\": \"prueba de comentario 2\"}"

### Extraer comentarios de un anuncio particular (GET /anuncios/{id}/comentarios)
curl -X GET "https://7d82ges3t7.execute-api.eu-west-1.amazonaws.com/prod/anuncios/9fd2c650-bd90-4d4a-b10c-9f59d89acd6b/comentarios"






