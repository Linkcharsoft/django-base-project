# General information

Pre-config Django with django-rest-framework.
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
- django-watchman
- drf-writable-nested


## Installation

Recommended Python version: 3.10.7


**Use the git clone command:**

```bash
git clone https://github.com/Linkcharsoft/base_django_rest_project .
```

It is highly recommended to use a **[VirtualEnv](https://towardsdatascience.com/virtual-environments-104c62d48c54)**
You can specify the python version you want to use with the following command:

```bash
virtualenv --python=python3.10 venv
```

Create and complete a .env file with your app info (there is already a .env.example file).

**Env aclarations**:
- In order to complete the "SECRET_KEY" field, you can use the default on .env.example but then you must run the following command and copy the given value on the .env file:
    ```bash
    python manage.py generate_secret_key
    ```
- In the "DB settings" sectio, you can select the database you want to use. If you choose "sqlite3", no further configuration is necessary.

- The "USE_EMAIL_FOR_AUTHENTICATION" field determines the authentication method to be used. If set to True, email addresses will be required, and validation will be necessary. Email addresses must also be unique on the platform.

- In the "Email Settings" section, you can select the email provider. If you choose "console," no further configuration is necessary. However, if you select "aws," you must specify your credentials.

- The "WATCHMAN_TOKEN" is used by the Django-watchman library to protect the system status endpoint. If this value is set to None, there will be no protection.


**Install all requirements:**
```bash
pip install -r requirements.txt
```
**Run migrations:**
```bash
python manage.py migrate
```
**Code Formater**
In the requirements file, we have included the [black](https://pypi.org/project/black/)library to ensure a high standard of code formatting.
Additionally, you will find a "pre-commit" file in the project's root directory, which should be moved to the hooks folder within the .git folder.

For Linux users, it is necessary to execute the following command to make it executable.
```bash
chmod +x .git/hooks/pre-commit
```



## Operation and how to use

The migrations will automatically generate an admin user with the following credentials when the "DEBUG" environment variable is set to True:
- Username: useradmin
- Email: admin@admin.com
- Password: admin123123

This means that you already have access to the admin panel.

**Base models and serializers**
In the "django_base/base_models.py" file, you will find some base models and managers. You should always inherit from them depending on whether you want a model with soft delete or not, as they add some fields and functionality.

If you use the "BaseSoftDeleteModel", when you access the "objects" manager, it will give you a filtered queryset. If you want to see all objects, you should use the "unfiltered_objects" manager, which will retrieve the deleted objects as well.

In adittion to this base models, you need to use ours base serializers. This ones adds some fields that you should exclude in the serializer definition. (creation_date, update_date, etc.)

We have also incorporated two new model fields, one for images (CustomImageField), and the other for files (CustomFileField). These function identically to the standard fields but have the added capability of automatically renaming the files with a unique hash.

The project includes a custom paginator to use with ViewSets. When using a list action, you can pass the "page_size" parameter to specify the number of elements you want per page. This is in addition to the predefined fields of "PageNumberPagination".

Some additions:
- We have added some extra password validators to the ones already provided by Django.
- We include a function in the "django_base/utils.py" to make aware naive datetimes.

## Libraries

[**django-cors-headers**](https://pypi.org/project/django-cors-headers/)
"A Django App that adds Cross-Origin Resource Sharing (CORS) headers to responses. This allows in-browser requests to your Django application from other origins."

Within the .env file, you will find a variable named "CORS_ALLOWED_URLS."
The URLs specified in this variable will be utilized in both the "CORS_ALLOWED_ORIGINS" and "CORS_ORIGIN_WHITELIST" settings.

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

[**django-watchman**](https://django-watchman.readthedocs.io/en/latest/)
"django-watchman exposes a status endpoint for your backing services like databases, caches, etc."

The Django Watchman library is an invaluable tool for monitoring all your services. By default, it is configured with essential checks, but you can continuously add more services to be monitored.

If you assign a value to the environment variable "WATCHMAN_TOKEN," it will add a layer of protection to the status endpoint. In this case, you will need to include the token as a query parameter in each call to the endpoint.

I highly recommend watching the presentation video available in the documentation.

[drf-writable-nested](https://pypi.org/project/drf-writable-nested/)
"This is a writable nested model serializer for Django REST Framework which allows you to create/update your models with related nested data."

This library provides an excellent solution for handling nested serializers. It simplifies the process by inheriting from their serializers, you can take advantage of the library's functionality, making the development process more streamlined and time-efficient.

Additionally, the library offers other useful serializer functionalities, such as managing unique fields. This feature can be beneficial when dealing with models that require uniqueness constraints on certain fields. 

## Endpoints
To access detailed information about the endpoints in the project, you can utilize the Swagger or Redoc endpoints. Both of these endpoints are included in the project and offer interactive documentation for the API.

Swagger endpoint: swagger/
Redoc endpoint: redoc/

## Example 
**Filters, orders, search, paginator in ModelViewSet**

```python
from django_filters import rest_framework as filters
from rest_framework import filters as rest_filters

class UserViewSet(ModelViewSet):
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
- [Luca Cittá Guiordano](https://www.linkedin.com/in/lucacittagiordano/)
- [Matias Girardi](https://www.linkedin.com/in/matiasgirardi)
- [Juan Ignacio Borrelli](https://www.linkedin.com/in/juan-ignacio-borrelli/)


All of us working on [Linkchar Software Development](https://linkchar.com/)


## License
[MIT](https://choosealicense.com/licenses/mit/)
