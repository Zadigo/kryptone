FROM ubuntu:latest

WORKDIR /home

RUN ls -la

COPY . /kryptone

RUN echo "export PYTHONPATH=${PYTHONPATH}:/home/kryptone" >> /ubuntu/.bashrc

RUN source /ubuntu/.bashrc

RUN echo $PYTHONPATH

WORKDIR /home/kryptone

EXPOSE 5589

ENTRYPOINT [ "python", "manage.py" ]
