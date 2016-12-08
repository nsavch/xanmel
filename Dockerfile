FROM python:3-onbuild

ADD config.yaml /etc/xanmel_config.yaml
CMD ["python", "./run.py"]
