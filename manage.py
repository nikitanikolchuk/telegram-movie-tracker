import sys

from settings import init_django


if __name__ == '__main__':
    from django.core.management import execute_from_command_line

    init_django()
    execute_from_command_line(sys.argv)
