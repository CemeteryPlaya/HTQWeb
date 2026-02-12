# React + Django Integration Project

This project integrates a React frontend with a Django backend using REST API (Django REST Framework) and JWT authentication.

## Setup

### Backend
1.  Navigate to `backend`: `cd backend`
2.  Install dependencies: `pip install django djangorestframework djangorestframework-simplejwt django-cors-headers`
3.  Migrate database: `python manage.py migrate`
4.  Run server: `python manage.py runserver`

### Frontend
1.  Navigate to `frontend`: `cd frontend`
2.  Install dependencies: `npm install`
3.  Run dev server: `npm run dev`

## Features

*   **User Profile**: `/myprofile` page with avatar upload, display name, and bio editing. Protected by Auth Guard.
*   **JWT Authentication**: Secure login/access using SimpleJWT.
*   **Items API**: Create and list items protected by authentication.
*   **React Integration**: Axios client with interceptors for token management.

## Configuration

### Frontend
Create `.env` file in `frontend` directory based on `.env.example`:
```
VITE_API_BASE_URL="http://localhost:8000/api/"
```

## Testing
*   Backend: `python manage.py test mainView`
*   Frontend: `npm test`
