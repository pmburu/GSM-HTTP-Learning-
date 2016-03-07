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
devices mounted. gsm-api assumes that the devices are mounted as `/dev/ttyACM*`.

```sh
$ docker run \
  --device /dev/MyModem0:/dev/ttyACM0 \
  --device /dev/AnotherModem0:/dev/ttyACM1 \
  hub.infoshift.co/gsm-api
```

HTTP API
---

The HTTP API returns JSON responses and usually expects `form-urlencoded` as
POST data.

Example:

```sh
$ curl -XPOST 'http://localhost:3000/an/api/endpoint' -d 'a=1&b=2' -F 'c=3'
```

### Initiating a Call

Example Request:

```sh
$ curl -XPOST 'http://localhost:3000/modems/<modem_number>/call' -F 'number=09xxxxxxxxx' -F 'duration=0'
```

Example Response

```json
{
  "connected": true, 
  "duration": 5
}
```

Request Parameters:
- modem_number: The number of the modem we'll use to initiate the call.
- number: A 10-digit msisdn that we'll call.
- duration: How long a call should last.

Response Parameters:
- connected: Boolean. Tells whether the call has been successfully connected.
- duration: Number. How long the call actually lasted.

#### Notes:
- If `duration` is set to 0, and once the call is connected, the call lasts
indefinitely until the call is terminated by either the receiver or the network.
- If `duration` is set to 1 or so, and once the call is connected, the call
is terminated once the set `duration` is reached or the call is terminated by
either the receiver or the network.

### Receiving a Call

Example Request:

```sh
$ curl -XPOST 'http://localhost:3000/modems/<modem_number>/wait_for_call' -F 'duration=0'
```

Example Response:
```json
{
  "connected": true, 
  "duration": 5
}
```

Request Parameters:
- duration: How long a call should last.

Response Parameters:
- connected: Boolean. Tells whether the call has been successfully connected.
- duration: Number. How long the call actually lasted.

#### Notes:
- Answers any call received at that moment.
- If `duration` is set to 0, and once the call is connected, the call lasts
indefinitely until the call is terminated by either the receiver or the network.
- If `duration` is set to 1 or so, and once the call is connected, the call
is terminated once the set `duration` is reached or the call is terminated by
either the receiver or the network.


### Sending an SMS

TODO

### Sending a USSD Command

TODO
