# IB Gateway Setup Guide

1.  **Enable API Socket Connections:**
    *   In IB Gateway, go to `Configuration > API > Settings`.
    *   Check the box for `Enable ActiveX and Socket Clients`.

2.  **Set Socket Port:**
    *   Ensure the `Socket port` is set to `4002` for paper trading accounts.

3.  **Use Read-Only API (Initially):**
    *   For initial setup and testing, check `Read-Only API` to prevent accidental trades.

4.  **Configure Trusted IPs:**
    *   Add `127.0.0.1` to the `Trusted IP Addresses`. This is crucial for the application to connect.
