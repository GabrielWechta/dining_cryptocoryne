FROM python:3.8 AS server

WORKDIR /usr/src/app

# Copy required modules
COPY server server
COPY common common

# Install the modules
RUN pip install -e server
RUN pip install -e common

# Make the log directory
RUN mkdir log

# Copy resources
COPY resources/certs/securocracy_cert.pem resources/certs/securocracy_cert.pem
COPY resources/certs/securocracy_key.pem resources/certs/securocracy_key.pem

CMD ["python", "-u", "-m", "server"]

FROM python:3.8 AS client

WORKDIR /usr/src/app

# Copy required modules
COPY client client
COPY common common

# Install the modules
RUN pip install -e client
RUN pip install -e common

# Make the log directory
RUN mkdir log

# Copy resources
COPY resources/certs/securocracy_cert.pem resources/certs/securocracy_cert.pem
CMD ["python", "-u", "-m", "client"]
