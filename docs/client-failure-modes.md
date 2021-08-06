# Possible outcomes

For a list, get etc:

- retryable error (dns, tcp, tls, http 429/5xx)
- non-retryable error (4xx)

For a watch:

- watch timeout
    - client's timeout fires: `asyncio.exceptions.TimeoutError`
    - server's timeout fires: `aiohttp.client_exceptions.ClientPayloadError: Response payload is not completed` after `4m59.372s`
- retryable error (dns, tcp, tls, http 429/5xx)
- non-retryable error (4xx)


## Classification of exceptions

A watch operation has completed successfully after n number of minutes:
- `aiohttp.ClientPayloadError`
- `asyncio.TimeoutError` (if client timeout is set to minutes)

It's best to double check that this wasn't a fail-fast by checking the duration
of the request and comparing it to the timeout interval we expect to be in
force. If it completed very quickly then it probably was an error.

We don't think the request has any chance of succeeding so we don't retry:
- `aiohttp.InvalidURL` - the url is malformed and the client rejected it
- `asyncio.TimeoutError` (if client timeout set to seconds then it's probably too aggressive)
- HTTP 4xx excl 429

We think the request could succeed if retried so we will retry:
- `aiohttp.TooManyRedirects` - http (server could be misbehaving?)
- `aiohttp.ClientConnectorError` - dns or tcp
- `aiohttp.ServerTimeoutError` - tcp read timeout (server is being slow)
    - could also be that the timeout is too aggressive - could we bump it maybe?
- `aiohttp.ClientOSError` - tcp (some kind of) timeout
- `aiohttp.ClientConnectorCertificateError` - tls
    - retrying most likely won't help if the server is misconfigured
    - retrying may help if the server is just misbehaving
- `aiohttp.ClientConnectorSSLError` - tls (same rationale as previous)
- HTTP 429/5xx


## Inheritance hierarchies for relevant exceptions

- asyncio.TimeoutError

- [aiohttp].InvalidURL
    - ClientError
    - ValueError

- [aiohttp].TooManyRedirects
    - ClientResponseError
        - ClientError

- [aiohttp].ClientPayloadError
    - ClientError

- [aiohttp].ClientConnectorError
    - ClientOSError
        - ClientConnectionError
            - ClientError

- [aiohttp].ServerTimeoutError
    - ServerConnectionError
        - ClientConnectionError
            - ClientError
    - asyncio.exceptions.TimeoutError

- [aiohttp].ClientOSError
    - ClientConnectionError
        - ClientError

- [aiohttp].ClientConnectorCertificateError
    - ClientSSLError
        - ClientConnectorError
            - ClientOSError
                - ClientConnectionError
                    - ClientError

- [aiohttp].ClientConnectorSSLError
    - ClientSSLError
        - ClientConnectorError
            - ClientOSError
                - ClientConnectionError
                    - ClientError


# Failure modes

## DNS resolution (invalid domain name)


### AsyncResolver
- inner: OSError: Domain name not found
- outer: aiohttp.client_exceptions.ClientConnectorError: Cannot connect to host zskdjf.gov:80 ssl:default [None]

### ThreadedResolver:
- inner: socket.gaierror: [Errno -2] Name or service not known   # subclass of OSError
- outer: aiohttp.client_exceptions.ClientConnectorError: Cannot connect to host zskdjf.gov:80 ssl:default [Name or service not known]

ClientConnectorError stores the inner exc object.


## TCP connect error (no process listening on port)

- inner: ConnectionRefusedError: [Errno 111] Connect call failed ('127.0.0.1', 8001)  # from stdlib
- outer: aiohttp.client_exceptions.ClientConnectorError: Cannot connect to host 127.0.0.1:8001 ssl:default [Connect call failed ('127.0.0.1', 8001)]


## TCP timeout (the host exists but the timeout is too aggressive)

### timeout = ClientTimeout(sock_connect=0.001)

json.decoder.JSONDecodeError: Extra data: line 1 column 5 (char 4)

This one seems flaky, should probably avoid it.

### timeout = ClientTimeout(sock_read=0.001)

aiohttp.client_exceptions.ServerTimeoutError: Timeout on reading data from socket

### timeout = ClientTimeout(connect=0.001)

aiohttp.client_exceptions.ClientOSError: [Errno 32] Broken pipe

### ClientTimeout(total=0.001)

asyncio.exceptions.TimeoutError


## TLS

### cert does not match host

aiohttp.client_exceptions.ClientConnectorCertificateError: Cannot connect to host wrong.host.badssl.com:443 ssl:True [SSLCertVerificationError: (1, "[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: Hostname mismatch, certificate is not valid for 'wrong.host.badssl.com'. (_ssl.c:1131)")]

### self signed cert
aiohttp.client_exceptions.ClientConnectorCertificateError: Cannot connect to host self-signed.badssl.com:443 ssl:True [SSLCertVerificationError: (1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: self signed certificate (_ssl.c:1131)')]

### expired cert

aiohttp.client_exceptions.ClientConnectorCertificateError: Cannot connect to host expired.badssl.com:443 ssl:True [SSLCertVerificationError: (1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: certificate has expired (_ssl.c:1131)')]

### weak cipher

aiohttp.client_exceptions.ClientConnectorSSLError: Cannot connect to host rc4.badssl.com:443 ssl:default [[SSL: SSLV3_ALERT_HANDSHAKE_FAILURE] sslv3 alert handshake failure (_ssl.c:1131)]

### handshake timeout

Don't know how to reproduce this...


## HTTP

### 404

<ClientResponse(http://127.0.0.1:8001/zz/api/v1/namespaces) [404 Not Found]>
