ARG PYTHON_VERSION=3
FROM python:${PYTHON_VERSION}

RUN apt update && apt install -y libvirt-dev pkg-config
RUN pip install uv

WORKDIR /app
ENTRYPOINT ["uv", "lock"]
