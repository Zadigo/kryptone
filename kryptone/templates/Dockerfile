FROM ubuntu:latest

# Update the package lists in the container
RUN apt-get update

# Install Python and pip
RUN apt-get install -y python3 python3-pip

WORKDIR /home/app

COPY requirements.txt .

RUN pip install -r requirements.txt

# Add the directory to the PYTHONPATH
ENV PYTHONPATH="${PYTHONPATH}:/home/app"

COPY ./my_script.py .

EXPOSE 5589

CMD [ "my_script" ]

ENTRYPOINT [ "python3", "-m" ]
