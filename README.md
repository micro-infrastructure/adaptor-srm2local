# SRM copy adaptor

## Functions
This adaptor exposes one functions: copy and status. 

Reachable on `/copy` and `/status` via HTTP, or `functions.srm2local.copy` and `functions.srm2local.status` via AMQP.

### `copy`
Use the following request payload, with `paths` containing SURLs:

```json
{
    "cmd": {
        "src": {
            "paths": [
                "...", 
                "..."
            ]
        },
        "dest": {
            "host": "...",
            "path": "..."
        },
        "credentials": {
            "hpcUsername": "...",
            "hpcPassword": "...",
            "srmCertificate": "..."
        }
    }
}
```

### `status`
Use the following request payload:

```json
{
    "identifier": "..."
}
```

In case of AMQP, wrap the payload in the following JSON:

```json
{
    "id": "...",
    "replyTo": "...",
    "body": "<payload>"
}
```
