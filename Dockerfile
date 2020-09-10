FROM python:alpine3.7
COPY . /TN-ERC20-Gateway
WORKDIR /TN-ERC20-Gateway
RUN apk update
RUN apk upgrade
RUN apk add build-base 
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install psycopg2-binary
EXPOSE 5000
CMD python ./start.py
