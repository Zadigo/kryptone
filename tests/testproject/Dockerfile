FROM python

WORKDIR /app

RUN pip install --upgrade pip
RUN pip3 install pipenv

COPY Pipfile .
COPY Pipfile.lock .

RUN pipenv install --system --deploy

RUN pip install Kryptone

COPY . .

EXPOSE 8000
