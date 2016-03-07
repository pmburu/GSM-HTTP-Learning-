FROM alpine:3.3

RUN apk add --no-cache python py-pip
ADD requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt
ADD . /opt/app
EXPOSE 80
CMD gunicorn server:app -b 0.0.0.0:80 --reload --access-logfile - --error-logfile - --timeout 120
