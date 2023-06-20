FROM ubuntu:latest

RUN echo export PYTHONPATH="${PYTHONPATH}:/home/kryptone" >> ~/.bashrc

RUN echo export PYTHONPATH="${PYTHONPATH}:/home/kryptone" >> ~/.bash_profile

RUN source ~/.bashrc && source ~/.bash_profile

RUN echo $PYTHONPATH

COPY . home/app

WORKDIR home/app

EXPOSE 5589

ENTRYPOINT [ "python", "manage.py" ]