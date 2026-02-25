# NEWS PORTAL – CAPSTONE PROJECT

## PROJECT OVERVIEW

News Portal is a Django-based web application that allows:

- Journalists to create and manage articles

- Readers to subscribe to publishers or journalists

- Automatic email notifications when new articles are published

- Optional integration with the X (formerly Twitter) API for article sharing

- REST API endpoints for third-party access

This project demonstrates full-stack Django development, database integration with MariaDB, REST API implementation, and third-party API integration.

## FEATURES

### User Roles

- Admin – Full system control

- Journalist – Create and manage articles

- Reader – Subscribe to publishers/journalists

### Article Management

- Create, edit, delete articles

- Articles linked to publishers or independent journalists

- Approval system before publishing (if implemented)

### Email Notifications

When an article is published:

- Publisher subscribers receive email notifications

- Journalist subscribers receive email notifications

- Emails are sent using Django’s email backend

### X (Twitter) Integration

- Approved articles can be shared to X

- If API permissions are restricted, posting is simulated

- No API keys are stored in the repository (environment variables used)

### REST API

- Token-based authentication

- Endpoints return articles based on reader subscriptions

- Tested using Postman

## TECHNOLOGIES USED

- Python

- Django

- Django REST Framework

- MariaDB

- Tweepy (X API integration)

- Flake8 (Code linting)

- Postman (API testing)

## DATABASE

This project uses MariaDB.

Make sure MariaDB is installed and running before starting the project.

## INSTALLATION INSTRUCTIONS

```bash
1. Clone the Repository
git clone <your-repository-url>
cd news_portal

2. Create Virtual Environment
python -m venv venv

Activate it:

Windows (Git Bash):

source venv/Scripts/activate

Windows (CMD):

venv\Scripts\activate

3. Install Dependencies
pip install -r requirements.txt

If no requirements file exists:

pip install django djangorestframework mysqlclient tweepy python-decouple flake8

4. Configure Environment Variables

Create a .env file in the project root:

TWITTER_API_KEY=your_key
TWITTER_API_SECRET=your_secret
TWITTER_ACCESS_TOKEN=your_token
TWITTER_ACCESS_SECRET=your_access_secret

⚠️ Do NOT commit this file.

5. Configure Database

In settings.py, ensure:

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "news_portal_db",
        "USER": "news_user",
        "PASSWORD": "your_password",
        "HOST": "localhost",
        "PORT": "3306",
    }
}

6. Run Migrations
python manage.py migrate

7. Create Superuser
python manage.py createsuperuser

8. Run Development Server
python manage.py runserver

Visit:

http://127.0.0.1:8000/

Admin panel:

http://127.0.0.1:8000/admin/
bash'''

## API AUTHENTICATION

The API uses Token Authentication.

To generate a token:

python manage.py drf_create_token <username>

Include the token in Postman headers:

Authorization: Token your_token_here

## API ENDPOINTS

Method	Endpoint	Description
GET	/api/articles/	Returns articles based on user subscriptions
POST	/api/token/	Obtain authentication token

## RUNNING TESTS

Run:

python manage.py test

Includes:

Model tests

View tests

API tests

X API integration tests (simulated)

## CODE QUALITY

Linting is enforced using:

flake8

All major linting issues have been resolved before submission.

## PROJECT STRUCTURE

news_portal/
│
├── news/                # Main app
│   ├── models.py
│   ├── views.py
│   ├── services.py      # Email + X API integration
│   ├── tests.py
│   ├── test_x_api.py
│
├── news_portal/
│   ├── settings.py
│   ├── urls.py
│
└── manage.py

## DESIGN DECISIONS

Used a service layer (services.py) to separate side effects from views.

Implemented subscription-based filtering for REST API.

Used environment variables for secure API key handling.

Simulated X API posting when permissions are restricted.
