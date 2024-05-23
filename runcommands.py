import os
import argparse
import subprocess

from django_base.settings.configurations import LANGUAGES

DJANGO_CONTAINER_NAME = "web"
POSTGRES_CONTAINER_NAME = "db"


def get_env_value(key, filename=".env"):
    """
    Get the value of a given key from the .env file.
    """
    try:
        with open(filename, "r") as file:
            for line in file:
                line = line.strip()  # Remove any whitespace
                if line.startswith(key + "="):
                    value = line.split("=")[1]
                    return value.strip("'")  # Remove single quotes
    except FileNotFoundError:
        print(f"Could not find the environment file {filename}.")
    return None

def extract_language_codes(languages):
    codes = []
    for lenguage in languages:
        codes.append(lenguage[0])
    return codes

def check_language_directories_exist(language_codes):
    locale_directory = "locale"  # Replace with the actual path to your "locale" directory

    missing_directories = []

    for code in language_codes:
        language_directory = os.path.join(locale_directory, code)
        if not os.path.exists(language_directory):
            missing_directories.append(code)

    return missing_directories


DB_USER = get_env_value("DB_USER")
DB_NAME = get_env_value("DB_NAME")


def run_django_command(command):
    cmd = f"docker compose exec {DJANGO_CONTAINER_NAME} python manage.py {command}"
    subprocess.run(cmd, shell=True)


def enter_django_shell():
    run_django_command("shell_plus")


def run_make_migrations():
    run_django_command("makemigrations")


def run_migrations():
    run_django_command("migrate")


def run_makemessages():
    command = "makemessages"

    language_codes = extract_language_codes(LANGUAGES)
    missing_directories = check_language_directories_exist(language_codes)

    if missing_directories:
        for code in missing_directories:
            command += f" -l {code}"
    else:
        command += " -a"

    run_django_command(f"{command} --ignore=venv/*")



def run_compilemessages():
    run_django_command("compilemessages --ignore=venv/*")


def run_other_django_command():
    command = input("Enter Django command: ")
    run_django_command(command)


def enter_container(container_name):
    cmd = f"docker compose exec -it {container_name} /bin/bash"
    subprocess.run(cmd, shell=True)


def enter_postgres_shell():
    cmd = (
        f"docker compose exec -it {POSTGRES_CONTAINER_NAME} psql -U {DB_USER} {DB_NAME}"
    )
    subprocess.run(cmd, shell=True)

def run_tests():
    cmd = f"docker compose exec {DJANGO_CONTAINER_NAME} python manage.py test"
    subprocess.run(cmd, shell=True)


def interactive_menu():
    while True:
        print("\nOptions:")
        print("\n--- Comandos Generales ---")
        print("1. Enter Django shell")
        print("2. Run make migrations")
        print("3. Run migrations")
        print("4. Run Make messages")
        print("5. Run Compile messages")
        print("6. Run other Django command")
        print("7. Enter Django container")
        print("8. Enter PostgreSQL container")
        print("9. Enter PostgreSQL shell (psql)")
        print("10. Run tests")
        print("11. Quit")

        # print("\n--- Comandos de Proyecto Específico ---")
        choice = input("Enter your choice: ")

        if choice == "1":
            enter_django_shell()
            break
        elif choice == "2":
            run_make_migrations()
            break
        elif choice == "3":
            run_migrations()
            break
        elif choice == "4":
            run_makemessages()
            break
        elif choice == "5":
            run_compilemessages()
            break
        elif choice == "6":
            run_other_django_command()
            break
        elif choice == "7":
            enter_container(DJANGO_CONTAINER_NAME)
            break
        elif choice == "8":
            enter_container(POSTGRES_CONTAINER_NAME)
            break
        elif choice == "9":
            enter_postgres_shell()
            break
        elif choice == "10":
            run_tests()
            break
        elif choice == "11":
            break
        else:
            print("Invalid choice. Please try again.")


def main():
    parser = argparse.ArgumentParser(
        description="Manage Django and PostgreSQL inside Docker."
    )

    parser.add_argument("--shell", action="store_true", help="Enter Django shell")
    parser.add_argument(
        "--makemigrations", action="store_true", help="Run make migrations"
    )
    parser.add_argument("--migrate", action="store_true", help="Run migrations")
    parser.add_argument("--makemessages", action="store_true", help="Run make messages")
    parser.add_argument(
        "--compilemessages", action="store_true", help="Run compile messages"
    )
    parser.add_argument(
        "--django-container", action="store_true", help="Enter the Django container"
    )
    parser.add_argument(
        "--django-command", action="store_true", help="Run other Django command"
    )
    parser.add_argument(
        "--postgres-container",
        action="store_true",
        help="Enter the PostgreSQL container",
    )
    parser.add_argument(
        "--postgres-shell", action="store_true", help="Enter PostgreSQL shell (psql)"
    )
    parser.add_argument("--tests", action="store_true", help="Run tests")

    args = parser.parse_args()

    # Check if any arguments were provided
    if any(vars(args).values()):
        if args.shell:
            enter_django_shell()
        elif args.makemigrations:
            run_make_migrations()
        elif args.migrate:
            run_migrations()
        elif args.makemessages:
            run_makemessages()
        elif args.compilemessages:
            run_compilemessages()
        elif args.django_container:
            enter_container(DJANGO_CONTAINER_NAME)
        elif args.django_command:
            run_other_django_command()
        elif args.postgres_container:
            enter_container(POSTGRES_CONTAINER_NAME)
        elif args.postgres_shell:
            enter_postgres_shell()
        elif args.tests:
            run_tests()
    else:
        # No arguments provided, show interactive menu
        interactive_menu()


if __name__ == "__main__":
    main()
