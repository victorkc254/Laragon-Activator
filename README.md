Laragon License Activator

> **⚠️ EDUCATIONAL PURPOSES ONLY**
>
> This tool is provided strictly for educational and research purposes. It demonstrates how local DNS redirection and HTTPS interception work at a technical level. The author does not condone software piracy or circumvention of licensing mechanisms. Use this tool only on software you legally own and have the right to modify. The author assumes no liability for misuse.

---

## Overview

A local fake API server that intercepts `api.laragon.org` to demonstrate HTTPS certificate handling, DNS hosts file manipulation, and local server proxying on Windows.

This tool creates a local HTTPS server on `api.laragon.org:443` that mimics a license API. It:

- Redirects `api.laragon.org` to `127.0.0.1` via Windows hosts file
- Generates a self-signed TLS certificate for `api.laragon.org`
- Serves mock license activation responses
- Automatically cleans up after use

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.8+ | Tested with Python 3.14 |
| Windows | 10/11 | Administrator rights required |
| Port 443 | Free | No other service listening |

**Required Python packages:**

```cmd
pip install cryptography
