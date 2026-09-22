# Running the SIMP relay on an Oracle VM

An 8 GB Oracle Linux or Ubuntu VM is ample for this relay. The default server is
bounded to 64 live connections, 32 participants per room, and 30 incoming image
frames per 10 seconds per client.

The relay is stateless: it does not create a message database, spool, upload
directory, or chat-history files. It validates a PNG, forwards it to clients who
are currently in the same room, and releases it. Every new envelope also carries
a 24-hour expiry timestamp; the relay rejects an already-expired envelope and
will not accept a lifetime longer than seven days.

## Install

Copy this repository to `/opt/simp`, then run:

```bash
sudo useradd --system --home-dir /opt/simp --shell /sbin/nologin simp
sudo chown -R simp:simp /opt/simp
cd /opt/simp
sudo -u simp python3 -m venv .venv
sudo -u simp .venv/bin/python -m pip install .
sudo cp deploy/simp-relay.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now simp-relay
sudo systemctl status simp-relay
```

View relay logs with:

```bash
sudo journalctl -u simp-relay -f
```

## Network access

Allow inbound TCP port `45873` in the VM firewall and in the Oracle Cloud network
security rules attached to the instance. Restrict the source CIDR to the client
addresses that need access whenever possible; do not expose the port to the
whole internet merely for convenience.

Oracle Linux with `firewalld` commonly uses:

```bash
sudo firewall-cmd --permanent --add-port=45873/tcp
sudo firewall-cmd --reload
```

Ubuntu with UFW commonly uses:

```bash
sudo ufw allow from CLIENT_IP to any port 45873 proto tcp
```

In each client, enter the VM's reachable IP or DNS name as **Relay**, keep port
`45873`, and use the same room name.

## Security boundary

The expiry is embedded and validated, but it is not a cryptographic signature.
SIMP still provides no encryption or identity authentication. For remote use,
put the relay behind a private VPN such as WireGuard or restrict the firewall to
trusted IP addresses. The relay itself never needs a writable message-data
directory.
