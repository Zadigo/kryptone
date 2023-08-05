FROM ubuntu:latest

ARG package=v2.0.0

# Update the package lists 
# in the container
RUN apt-get update -y

RUN apt-get install curl -y

# Install Python and pip
RUN apt-get install -y python3 python3-pip

# Install Selenium dependencies
RUN apt-get install -y chromium-chromedriver

RUN ln -s /usr/lib/chromium-browser/chromedriver

# RAISES ERROR
# RUN ln -s /usr/bin/chromedriver

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

# Download the Kryptone released package
RUN curl -L https://github.com/Zadigo/kryptone/archive/refs/tags/${package}.tar.gz > kryptone.tar.gz

# Add the directory to the PYTHONPATH
ENV PYTHONPATH "${PYTHONPATH}:/app"

ENV PYTHONPATH "${PYTHONPATH}:/kryptone/kryptone"

COPY . /app

EXPOSE 80 443 5589

CMD [ "python3", "manage.py", "start" ]
