FROM python:3.10
WORKDIR /scripts
COPY requirements.txt /scripts
COPY scripts/* /scripts
ADD remoteexec.tar /scripts
RUN pip install -r requirements.txt
CMD ['python', 'server.py']