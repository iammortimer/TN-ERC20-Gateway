FROM python:alpine3.7
COPY . /TN-ERC20-Gateway
WORKDIR /TN-ERC20-Gateway
RUN apk update
RUN apk upgrade
RUN apk add build-base 
RUN pip install -r requirements.txt
EXPOSE 5000
CMD python ./start.py