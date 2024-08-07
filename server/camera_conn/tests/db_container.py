import docker

env = {
    'POSTGRES_DB': 'hello_django_prod',
    'POSTGRES_USER': 'hello_django',
    'POSTGRES_PASSWORD': 'hello_django',
    'POSTGRES_HOST': 'db',
    'POSTGRES_PORT': '5432',
    }

client = docker.from_env()
client.containers.run('postgres:15', environment=env)
#client.containers.run('alpine', 'echo hello world')

