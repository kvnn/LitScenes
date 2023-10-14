## Database on OSX
`docker compose up`
`docker-compose run web alembic revision --autogenerate -m "description_of_changes"`
`docker-compose run web alembic upgrade head`
