# dining_cryptocoryne

Crypto project implementing open veto network (OV-net). Also a melancholy,
get-back-together story.

To run:

```bash
pipenv install
pipenv shell
(...) bash run_securocracy.sh
```

cert gen:
```bash
openssl req -x509 -newkey rsa:4096 -keyout securocracy_key.pem -out securocracy_cert.pem -sha256 -days 365 -nodes -subj '/CN=localhost'
```