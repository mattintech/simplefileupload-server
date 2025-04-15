import os
import subprocess

cert = os.getenv("SSL_CERT", "cert.pem")
key = os.getenv("SSL_KEY", "key.pem")

use_ssl = os.path.exists(cert) and os.path.exists(key)

base_cmd = [
    "gunicorn", "wsgi:app", "--bind", "0.0.0.0:7777"
]

if use_ssl:
    print("🟢 Starting with HTTPS")
    base_cmd += ["--certfile", cert, "--keyfile", key]
else:
    print("🟡 Starting with HTTP (no certs found)")

subprocess.run(base_cmd)
