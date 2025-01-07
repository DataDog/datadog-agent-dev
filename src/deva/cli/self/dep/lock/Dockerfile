ARG PYTHON_VERSION=3
FROM python:${PYTHON_VERSION}-slim

RUN apt update && apt install -y libvirt-dev pkg-config
RUN pip install uv

WORKDIR /app
# https://github.com/astral-sh/uv/issues/7533#issuecomment-2578130122
ENV SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0
ENTRYPOINT ["uv", "lock"]
