# Test jwt token generation

curl \

> -X POST \
> -H "Content-Type: application/json" \
> -d '{"email": "mitchellkalenda@gmail.com", "password": "12345678"}' \
> http://localhost:8000/api/token/

will use cloudinary cdn for image storage:
https://console.cloudinary.com/app/c-3d345127982880773860f81a3dcb2d/image/getting-started
