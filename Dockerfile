FROM ubuntu:latest

WORKDIR /home

# RUN touch ubuntu/.bashrc

# RUN ls -la

COPY . /kryptone

# RUN echo "export PYTHONPATH=${PYTHONPATH}:/home/kryptone" >> /ubuntu/.bashrc
RUN echo "export PYTHONPATH=${PYTHONPATH}:/home/kryptone" >> /etc/bash.bashrc

# RUN source /ubuntu/.bashrc
RUN source /etc/bash.bashrc

RUN echo $PYTHONPATH

WORKDIR /home/kryptone

EXPOSE 5589

ENTRYPOINT [ "python", "manage.py" ]
