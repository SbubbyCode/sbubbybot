FROM python:3.8

# set work directory
WORKDIR /opt/api

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install postgres client
RUN apt update && \
      apt install postgresql-client -y && \
      rm -rf /var/cache/apt/archives

# install dependencies
RUN pip install --upgrade pip
RUN pip install pipenv
COPY ./Pipfile .
RUN export LDFLAGS="-L/usr/local/opt/openssl/lib"
RUN pipenv install --system --skip-lock --dev --deploy

# Setup a Development User
RUN useradd -ms /bin/bash sbubby 
USER sbubby

# copy project
COPY . .

# Run Commands
ENTRYPOINT ["/opt/api/cmds/entrypoint.sh"]
CMD ["python", "main.py"]