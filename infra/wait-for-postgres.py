import subprocess
import sys
import time


def check_postgres():
    result = subprocess.run(
        ['docker', 'exec', 'postgres-dev', 'pg_isready', '--host', 'localhost'],
        check=False,
        capture_output=True,
        text=True,
    )
    if 'accepting connections' not in result.stdout:
        sys.stdout.write('.')
        sys.stdout.flush()
        time.sleep(1)
        check_postgres()
    else:
        print('\n🟢 Postgres is ready!')


if __name__ == '__main__':
    print('\n\n🔴 Waiting for Postgres to accept connections...')
    check_postgres()
