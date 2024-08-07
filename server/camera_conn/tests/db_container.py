import docker

env = {
    'POSTGRES_DB': 'test_base',
    'POSTGRES_USER': 'test_user',
    'POSTGRES_PASSWORD': 'test_password',
    'POSTGRES_HOST': 'test',
    'POSTGRES_PORT': '10000',
    }


def main():
    client = docker.from_env()
    container = client.containers.run('postgres:15',
                                      environment=env,
                                      name='test_db',
                                      ports={'5432/tcp': 10000})
    return container

cont = main()