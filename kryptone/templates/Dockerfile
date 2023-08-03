FROM ubuntu:latest

# Update the package lists 
# in the container
RUN apt-get update -y

# Install Python and pip
RUN apt-get install -y python3 python3-pip

# Install Selenium dependencies
RUN apt-get install -y chromium-chromedriver

# RUN ln -s /usr/lib/chromium-browser/chromedriver

# RUN apt-get install curl

RUN ln -s /usr/bin/chromedriver

WORKDIR /app

# Clone the Kryptone framework
RUN curl -sL https://github.com/Zadigo/kryptone/archive/refs/tags/v1.0.0.tar.gz

RUN pip install -r kryptone-1.0.0/requirements.txt

# Add the directory to the PYTHONPATH
ENV PYTHONPATH="${PYTHONPATH}:/app"

ENV PYTHONPATH="${PYTHONPATH}:/kryptone"

COPY . /app

EXPOSE 80 443 5589

CMD [ "python", "manage.py", "start" ]
