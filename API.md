# API Documentation

## Authentication

### Login (Get Token)
*   **URL**: `/api/token/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
        "username": "your_username",
        "password": "your_password"
    }
    ```
*   **Response**:
    ```json
    {
        "access": "access_token_string",
        "refresh": "refresh_token_string"
    }
    ```

### Refresh Token
*   **URL**: `/api/token/refresh/`
*   **Method**: `POST`
*   **Body**:
    ```json
    {
        "refresh": "refresh_token_string"
    }
    ```
*   **Response**:
    ```json
    {
        "access": "new_access_token_string"
    }
    ```

## Items

### List Items
*   **URL**: `/api/items/`
*   **Method**: `GET`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Response**: List of items belonging to the user.

### Create Item
*   **URL**: `/api/items/`
*   **Method**: `POST`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Body**:
    ```json
    {
        "title": "Item Title",
        "description": "Item Description"
    }
    ```
*   **Response**: Created item object.

### Delete Item
*   **URL**: `/api/items/{id}/`
*   **Method**: `DELETE`
*   **Headers**: `Authorization: Bearer <access_token>`
*   **Response**: 204 No Content
