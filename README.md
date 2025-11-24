# Django Ninja Boilerplate

This project is a boilerplate for building REST APIs using Django and Django Ninja.

## Features
- Django 4+ project structure
- Example app structure (`myapi/core`)
- Ready for testing with pytest
- Pre-configured for SQLite (easy to change)
- Poetry for dependency management

## Getting Started

### Requirements
- Python 3.10+
- Poetry

### Installation
1. Clone the repository:
   ```sh
   git clone https://github.com/brunononogaki/django-ninja-boilerplate.git
   cd django-ninja-boilerplate
   ```
2. Install dependencies:
   ```sh
   poetry install
   ```
3. Run migrations:
   ```sh
   poetry run python manage.py migrate
   ```
4. Run the development server:
   ```sh
   poetry run python manage.py runserver
   ```

### Running Tests
```sh
poetry run pytest
```

## Project Structure
```
myapi/
    core/
        models.py
        views.py
        api.py
        ...
    settings.py
    urls.py
    ...
manage.py
pyproject.toml
```
