# Mini File Transfer Server

A simple Flask web UI for transferring files between a phone and a Linux PC over the same local Wi-Fi.

## Run on Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Find the PC IP:

```bash
hostname -I
```

On your phone, open:

```text
http://PC-IP:8000
```

Uploaded files are saved in `uploads/`.

Stop the server with `Ctrl+C`.
