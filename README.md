gsm-api
===

Easy-to-use gsm api server.

Quickstart
---

We can run gsm-api by running the command below.

```sh
$ docker pull hub.infoshift.co/gsm-api
$ docker run \
  -p 3000:80 \
  $(for i in /dev/ttyACM*; do echo --device $i:$i; done) \  # Mount all /dev/ttyACM*
  hub.infoshift.co/gsm-api \
```

This assumes the following:
- A modem device is connected to /dev/ttyACM0.

Let's view all the available modems.

```
MODEM_NUMS=$(curl http://localhost:3000/system/available_numbers | jq -r .numbers)
$ echo $MODEM_NUMS
```

Let's try sending an sms to our number using the available
modem.

```sh
$ RECIPIENT=091755952xx  # Replace with your number.
$ MESSAGE="Hello World"
$ curl -XPOST "http://localhost:3000/modems/$(echo $MODEM_NUMS | jq -r .[0])/send_sms" -F "number=$RECIPIENT" -F "message=$MESSAGE"
```

You should receive a `$MESSAGE` from this modem to your number (`$RECIPIENT`).

Adding Modems/Modem Detection
---

Once you have the devices connected to your server, run the container with the
devices mounted. gsm-api assumes that the devices are mounted as /dev/ttyACM*.

```sh
$ docker run \
  --device /dev/MyModem0:/dev/ttyACM0 \
  --device /dev/AnotherModem0:/dev/ttyACM1 \
  hub.infoshift.co/gsm-api
```
