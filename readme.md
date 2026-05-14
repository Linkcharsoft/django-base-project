
# General information
 
  

Pre-config Django with django-rest-framework and docker.

This project includes the next functionalities:

- Login, logout, signup

- Password reset, password recovery

- Email confirmation and resend email

- Custom User model and Profile model

- user/me endpoint to get user information and update it

  

And the next libraries (plus the ones that the frameworks include):

- django-cors-headers

- django-debug-toolbar

- django-filter

- django-environ

- django-extensions

- drf-writable-nested


## For AWS-Logs

Add this lines in docker-compose-production in the selected service at build level:

  

logging:

driver: awslogs

options:

awslogs-group: ecs-cluster-licensing

awslogs-region: us-east-1

awslogs-stream-prefix: web-aws-test

  
  

## For Ngnix

Add this lines in docker-compose-production as a new service
```
nginx:

build: nginx

restart: always

volumes:

- static_volume:/code/static

- media_volume:/code/media

ports:

- "80:80"

depends_on:

- web

networks:

- django-network

```

In addition add the ngnix folder in the root of your project with this two files.

  

#### default.conf

  

The proxy_pass in some cases must be changed to the name of the service in the docker-compose file instead of the ip address. Ej:
```
proxy_pass http://web:8000;
server {
	listen 80 default_server;
	server_name _;
	location / {
		proxy_pass http://127.0.0.1:8000;
		proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
		proxy_set_header Host $host;
		proxy_redirect off;
	}
	location /static/ {
		alias /code/static/;
	}

	location /media/ {
		alias /code/media/;
	}

}
```
  
  

#### Dockerfile

```
FROM nginx:stable-alpine

COPY default.conf /etc/nginx

COPY default.conf /etc/nginx/conf.d

EXPOSE 80

```


## Installation

  

Recommended Python version: 3.10.7

  
  

**Use the git clone command:**

  

```bash

git  clone  https://github.com/Linkcharsoft/base_django_rest_project  .

```

  

## Without docker

  

It is highly recommended to use a **[VirtualEnv](https://towardsdatascience.com/virtual-environments-104c62d48c54)**

You can specify the python version you want to use with the following command:

  

```bash

virtualenv  --python=python3.10  venv

```

  

Create and complete a .env file with your app info (there is already a .env.example file).

  

**Env aclarations**:

- In order to complete the "SECRET_KEY" field, you can use the default on .env.example but then you must run the following command and copy the given value on the .env file:

```bash

python manage.py generate_secret_key

```

- In the "settings/db_settings.py", you can select the database you want to use. If you choose "sqlite3", no further configuration is necessary.


- In the "Email Settings" section, you can select the email provider. If you choose "console," no further configuration is necessary. However, if you select "aws," you must specify your credentials.



**Install all requirements:**

```bash

pip  install  -r  requirements.txt

```

**Run migrations:**

```bash

python  manage.py  migrate

```

  

## With docker

Then for development run:

```bash

sudo  docker-compose  build

sudo  docker-compose  up  -d

```

  

Or for production run:

```bash

sudo  docker  compose  -f  docker-compose-production.yml  build

sudo  docker-compose  -f  docker-compose-production.yml  up  -d

```

  

**Hooks**

This project uses [pre-commit](https://pre-commit.com) to run [ruff](https://docs.astral.sh/ruff/) (format + lint) and other small checks before every commit. After cloning, install it once:

```bash
pip install pre-commit
pre-commit install
```

To bypass a single commit: `git commit --no-verify`.

To run all hooks manually over the whole repo: `pre-commit run --all-files`.

For a clean `git blame` that skips the bulk-format commits, run once:

```bash
git config blame.ignoreRevsFile .git-blame-ignore-revs
```


**Running Tests and Generating Coverage Report with pytest**

Pytest, coverage and pytest-django are configured in `pyproject.toml`. To run tests and generate an HTML coverage report:

```bash
pytest
pytest --cov --cov-report=html   # full project coverage
```


- *2. Interpreting the Coverage Report*

Terminal Coverage: After running the above command, you will see a summary in the terminal indicating the coverage percentage for each file, along with the lines of code that were not covered.

HTML Report: Open the htmlcov/index.html file in your browser to view an interactive report. This report allows you to explore the project's files and see which lines of code were executed during the tests and which were not.

- *3. Excluding Code from Coverage*

If there are parts of the code that you do not want to include in the coverage report (e.g., code that only runs in specific environments), you can mark them using the # pragma: no cover comment on the corresponding line.

  
**Runcommands**

We also have a `runcommands.py` file in the project's root directory. This file contains some useful commands that can be executed from the command line. It has an interactive menu that allows you to select the desired command.

Keep in mind that Docker Compose must be running to use it.
  
  

## Operation and how to use

  

The migrations will automatically generate an admin user with the following credentials when the "DEBUG" environment variable is set to True:

- Username: useradmin

- Email: admin@admin.com

- Password: admin123123

  

This means that you already have access to the admin panel.

  

**Base models and serializers**

In `django_base/base_utils/base_models.py` you'll find `BaseModel`, an abstract model with `created_at` and `updated_at` fields. Inherit from it whenever you want those timestamps.

  

`django_base/base_utils/base_serializers.py` provides `BaseSerializer`, a `ModelSerializer` that exposes `created_at` and `updated_at` in the response.

  

The project includes a custom paginator (`CustomPagination`) used by ViewSets. When using a list action, you can pass the `page_size` parameter to specify the number of elements you want per page (capped at 100).

  

Some additions:

- We have added some extra password validators to the ones already provided by Django.

  

## Translations

The project includes a translation system. The default language is English, but you can add more languages as needed in the "LANGUAGES" variable in the .env file.

  
  

To make it work you need to mark the strings that you want to translate with the "gettext_lazy" function. For example:

```python

from django.utils.translation import gettext_lazy as _

_('Hello world')

```

  

Then you need to run the following command:

```bash

python  manage.py  makemessages  -a

```

Or use the `runcommands.py` file and select the "Make messages" option. (Recomended)

  

This will generate a "django.po" file in the "locale" folder. You can then add the translations to this file.

  

Finally, you need to run the following command:

```bash
python  manage.py  compilemessages
```
Now if the client sends the "Accept-Language" header with the desired language, the system will automatically return the translated strings.


## Redis
To activate it in the project just uncomment the `redis` service in the `docker-compose.yml` file.
This allows you to use it in env configurations as `BROKER_SERVER`.

I you are using our infrastructure in AWS, you can uncomment all the lines in the terraform file `elasticache.tf` and it will create everything you need to use it and show `redis_service_host` as output this will be the value for `BROKER_SERVER`. (The redis port is almost always 6379)

## Async functionalities
This template includes pre-configurations for implementing asynchronous functionalities, particularly useful for features like web sockets.

To enable async functionalities, follow these steps:
- Change the default server from Gunicorn (which supports only WSGI) to Daphne, which is compatible with ASGI configurations. Modify the `entrypoint.sh` file to reflect this change.
	 ```
	#!/bin/bash
	python  manage.py  migrate
	#gunicorn  -w  3  -b  :8000  django_base.wsgi:application
	daphne -b 0.0.0.0 -p 8000 django_base.asgi:application
	 ```
- Uncomment "daphne" in the THIRD_APPS section of the`settings/custom_settings.py` file. **Ensure that it remains at the top of the list.***
	```
	THIRD_APPS = [
	'daphne',
	...
	``` 
## Web Sockets
This template supports WebSocket connections using the [**Channles library**](https://channels.readthedocs.io/en/latest/).

Please follow these steps:
- Ensure Async Functionalities are Enabled:
	- Confirm that you have enabled async functionalities in your project, as described in the "Async Functionalities" section of the documentation.
- Uncomment "channels" on the THIRD_APPS section. Ensure that it is included in the list of installed apps.
	```
	THIRD_APPS = [
	...
	'channels',
	...
	``` 
- Uncomment "ASGI_APPLICATION" from THIRD_APPS in the `settings/custom_settings.py` file.
- Fill in the values for `BROKER_SERVER` and `BROKER_SERVER_PORT` within the `.env` file and make sure to use `USE_WEB_SOCKET` in True.
	- You can use the default configuration for Redis. In that case, confirm that you have enabled redis in your project, as described in the **Redis** section of the documentation.
		- `BROKER_SERVER='redis'`
		- `BROKER_SERVER_PORT='6379'`

You've successfully set up the default configuration. Now, customize your WebSocket settings by making adjustments in the `routing.py` and `consumers.py` files within the `django_base` folder.

## Celery
We have a default configuration for celery to activate it, follow this steps:
- Fill in the values for `BROKER_SERVER` and `BROKER_SERVER_PORT` within the `.env` file and make sure to use `USE_CELERY` in True.
	- You can use the default configuration for Redis. In that case, confirm that you have enabled redis in your project, as described in the **Redis** section of the documentation.
		- `BROKER_SERVER='redis'`
		- `BROKER_SERVER_PORT='6379'`

- Uncomment the `celery` service in the `docker-compose.yml` file.

## Libraries
[**django-cors-headers**](https://pypi.org/project/django-cors-headers/)

"A Django App that adds Cross-Origin Resource Sharing (CORS) headers to responses. This allows in-browser requests to your Django application from other origins."

  

Within the .env file, you will find a variable named "CORS_ALLOWED_URLS."

The URLs specified in this variable will be utilized in both the "CORS_ALLOWED_ORIGINS" and "CORS_ORIGIN_WHITELIST" settings. (The value for FRONT_URL will automatically be added to the list of allowed URLs.)

  

[**django-debug-toolbar**](https://django-debug-toolbar.readthedocs.io/en/latest/)

"The Django Debug Toolbar is a configurable set of panels that display various debug information about the current request/response and when clicked, display more details about the panel's content."

  

This library will helps with debugging and optimizing Django projects during development.

It is pre-configured by default, but you can modify its settings as needed. The library is designed to assist you in identifying and resolving issues related to performance, database queries, template rendering, and caching.

  

[**django-filter**](https://django-filter.readthedocs.io/en/stable/)

"Django-filter provides a simple way to filter down a queryset based on parameters a user provides."

  

"Integration with Django Rest Framework is provided through a DRF-specific FilterSet and a filter backend. These may be found in the rest_framework sub-package."

  

By simply adding a few lines when defining the aspects of our view set, we can leverage the pre-defined models to handle filtering, ordering, and searching of our queryset.

```python

from django_filters import rest_framework as filters

from rest_framework import filters as rest_filters

  

filter_backends = (

filters.DjangoFilterBackend,

rest_filters.OrderingFilter,

rest_filters.SearchFilter

)

filterset_fields = ('FIELDS', 'TO', 'FILTER')

  

ordering_fields = ('FIELDS', 'TO', 'ORDER')

ordering = ('DEFAULT_ORDER',)

  

search_fields = ('FIELDS', 'TO', 'SEARCH')

```

You can also create custom models to fulfill more specific purposes.

  

[**django-environ**](https://django-environ.readthedocs.io/en/latest/)

"django-environ is the Python package that allows you to use Twelve-factor methodology to configure your Django application with environment variables."

  

[**django-extensions**](https://django-extensions.readthedocs.io/en/latest/)

"Django Extensions is a collection of custom extensions for the Django Framework.

These include management commands, additional database fields, admin extensions and much more."

  

We included the "django-extensions" library in our project because it provides a wide range of useful tools, such as the "shell-plus" feature.

For more detailed information about the "django-extensions" library and its various tools, I recommend referring to the official documentation


[drf-writable-nested](https://pypi.org/project/drf-writable-nested/)

"This is a writable nested model serializer for Django REST Framework which allows you to create/update your models with related nested data."

  

This library provides an excellent solution for handling nested serializers. It simplifies the process by inheriting from their serializers, you can take advantage of the library's functionality, making the development process more streamlined and time-efficient.

  

Additionally, the library offers other useful serializer functionalities, such as managing unique fields. This feature can be beneficial when dealing with models that require uniqueness constraints on certain fields.

  
  

[**django-crontab**](https://pypi.org/project/django-crontab/)

"Django-crontab is a Django application that allows you to register cron tasks from the Django admin interface or a crontab file."

  

This library allows you to schedule tasks to be executed at specific times. It is a very useful tool for automating tasks that need to be performed at regular intervals.

  

## Endpoints

To access detailed information about the endpoints in the project, you can utilize the Swagger or Redoc endpoints. Both of these endpoints are included in the project and offer interactive documentation for the API.

  

Swagger endpoint: swagger/

Redoc endpoint: redoc/

  

## Example

**Filters, orders, search, paginator in ModelViewSet**

  

```python

from django_filters import rest_framework as filters

from rest_framework import filters as rest_filters

  

class  UserViewSet(ModelViewSet):

permission_classes = [IsAuthenticated]

queryset = get_user_model().objects.all()

serializer_class = UserSerializer

  

filter_backends = (filters.DjangoFilterBackend, rest_filters.OrderingFilter, rest_filters.SearchFilter)

filterset_fields = ('is_staff',)

  

ordering_fields = ('first_name', 'last_name')

ordering = ('id',)

  

search_fields = ('first_name', 'last_name', 'email')

  

page_size_query_param = 'page_size'

```

  

## Contributing

- [Luca Cittá Giordano](https://www.linkedin.com/in/lucacittagiordano/)

- [Matias Girardi](https://www.linkedin.com/in/matiasgirardi)

- [Juan Ignacio Borrelli](https://www.linkedin.com/in/juan-ignacio-borrelli/)

- [Francesco Silvetti](https://www.linkedin.com/in/francescosilvetti/)

  
  

All of us working on [Linkchar Software Development](https://linkchar.com/)

  
  

## License

[MIT](https://choosealicense.com/licenses/mit/)

