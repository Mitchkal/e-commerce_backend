# Test jwt token generation

curl \

> -X POST \
> -H "Content-Type: application/json" \
> -d '{"email": "mitchellkalenda@gmail.com", "password": "12345678"}' \
> http://localhost:8000/api/token/
