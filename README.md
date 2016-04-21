gsm-api
===

Easy-to-use gsm api server.

Quickstart
---

We can run gsm-api by running the command below.

```sh
$ docker run \
  -p 3000:80 \
  $(for i in /dev/ttyACM*; do echo --device $i:$i; done) \  # Mount all /dev/ttyACM*
  hub.infoshift.co/gsm-api \
```

This assumes the following:
- A modem devices are connected to /dev/ttyACM*.

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
- modem_number: The number of the modem we'll use to initiate the call.
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

Example Request

```sh
$ curl -XPOST 'http://localhost:3000/modems/$MODEM_NUMBER/send_sms' -F 'number=09xxxxxxxxx' -F 'message=my message'
```

Example Response

```json
{
  "success": true, 
}
```

Request Parameters:
- modem_number: The number of the modem we'll use to initiate the call.
- message: The message to be sent.
- number: A 10-digit msisdn that we'll call.

Response Parameters:
- success: Boolean. Tells whether the message has been successfully sent or not.


### Sending a USSD Command

Example Request
```sh
$ curl -XPOST 'http://localhost:3000/modems/$MODEM_NUMBER/ussd' -F 'command=*143#' -F 'timeout=0'
```

Example Response
```
{
  "success": true,
  "message": "Hello World"
}
```

Request Parameters:
- modem_number: The number of the modem we'll use to initiate the call.
- command: A USSD command set. Usually starts with `*` and ends with `#`.
- timeout: Duration we wait until we consider the USSD request failed.

Response Parameters:
- success: Boolean. Tells whether the USSD command was successful.
- message: String. The final message the modem receives.
- error: String. Error that occured.

### Reading the Modem Inbox

Example Request
```sh
$ curl -XGET 'http://localhost:3000/modems/$MODEM_NUMBER/inbox'
```

Example Response
```
{
  "messages": [
        "date": "16/03/08",
        "index": 1,
        "message": "Hello world",
        "origin": "+6391755952xx",
        "status": "REC READ",
        "time": "06:28:00"
  ]
}
```

Request Parameters:
- modem_number: The number of the modem we'll use to initiate the call.

Response Parameters:
- messages[]: A list of messages.
- message[date]: String. A date string formatted as 'YY/MM/DD'
- message[index]: Number. Message position in the inbox.
- message[message]: String. The message sent.
- message[origin]: String (MSISDN). Where the message came from.
- message[status]: String. The status of the message (eg. REC READ means the message has been opened)
- message[time]: String. A time string formatted as 'HH:MM:SS'

### Clearing the Modem Inbox

Example Request
```sh
$ curl -XDELETE 'http://localhost:3000/modems/$MODEM_NUMBER/inbox'
```

Example Response:
```json
{
  "success": true
}
```

Request Parameters:
- modem_number: The number of the modem we'll use to initiate the call.

Response Parameters:
- success: Boolean. Tells whether the USSD command was successful.

### Waiting for an SMS Message

Example Request
```sh
$ curl -XGET 'http://localhost:3000/modems/$MODEM_NUMBER/wait_for_sms?origin=Globe&timeout=0'
```

Example Response:
```json
{
  "message": {
    "status": "REC UNREAD",
    "index": 1,
    "time": "14:58:19",
    "date": "03/11/16",
    "message": "Hello World",
    "origin": "GLOBE"
  },
  "error": null
}
```

Request Parameters:
- origin: The name or number where the message will be coming from.
- timeout: Number. Duration to wait until we consider the request failed.

Response Parameters:
- message: Object. Contains the details of the message.
- error: String. Error that occured.

### Data Request

This API provides a way to make a data-related request.

Example Request
```sh
$ curl -XPOST 'http://localhost:3000/modems/$MODEM_NUMBER/data -F 'url=http://m.facebook.com'
```

Example Response:
```json
{
  "error": null,
  "url": "http://m.facebook.com",
  "response_body_size": 1024,
  "response_header_size": 307,
  "response_status_code": 200
}
```

Request Parameters:
- url: A website url to make request to.
- timeout: Number. Duration to wait until we consider the request failed.

Response Parameters:
- error: String. Error that occured.
- url: String. The website url requested.
- response_body_size: Number. The size of the response body.
- response_status_code: Number. The HTTP status code we got.
