## Database on OSX
1. install Postgres.app and pgadmin
2. create database on localhost called 'LitScenes'
3. in app directory run `python -m alembic init alembic`
4. in app directory run `python -m alembic revision --autogenerate -m "description_of_changes"`
5. `python -m alembic upgrade head`