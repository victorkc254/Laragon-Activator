# Usage Guide

## Step 1: Install Dependencies

python -m pip install cryptography

Step 2: Full Setup (Run as Administrator)
Right-click CMD → "Run as administrator"

cd your folder with activator i.e cd C:\User\Desktop

python activator.py --setup

Expected output:
============================================================
  Laragon License Activator
============================================================
[+] Added hosts redirect: api.laragon.org -> 127.0.0.1
[+] DNS cache flushed.
[+] DNS check OK: api.laragon.org -> 127.0.0.1
[+] Generated self-signed certificate for api.laragon.org

[+] Fake license server running on https://0.0.0.0:443
[+] Cert: C:\Users\User\AppData\Local\Temp\laragon_activator_certs\server.pem

[+] INSTRUCTIONS:
    1. Open Laragon
    2. Go to the license
    3. Enter any license key in format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    4. Click 'Verify license'
    5. Watch this console for requests

[+] Waiting for requests... (Ctrl+C to stop)

Step 3: Trust the Certificate (First Time Only)
Open a new CMD as Administrator:

certutil -addstore -f "ROOT" C:\Users\User\AppData\Local\Temp\laragon_activator_certs\server.pem

Expected output:

ROOT "Trusted Root Certification Authorities"
Signature matches Public Key
Certificate "api.laragon.org" added to store.
CertUtil: -addstore command completed successfully.

Step 4: Activate Laragon
While the server is running:
Open Laragon
Go to Menu → License or Help → Activate
Enter any license key in UUID format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Example: aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
Example: 12345678-1234-1234-1234-123456789abc
Example: deadbeef-cafe-babe-feed-facefaceface
Click "Verify license"
Server console should show the activation request and response.
Step 5: Stop the Server
Press Ctrl+C in the server console.
Step 6: Cleanup

python activator.py --cleanup

Expected output:
Text
[+] Removed hosts redirect.
[+] DNS cache flushed.

Full Cleanup (Remove Certificate)
cmd
certutil -delstore "ROOT" api.laragon.org
rmdir /S /Q %TEMP%\laragon_activator_certs

Troubleshooting
Port 443 Already in Use
cmd
netstat -ano | findstr :443 | findstr LISTENING
taskkill /F /PID [PID]
Or kill all Python processes:
cmd
taskkill /F /IM python.exe
"Run as Administrator" Error
Right-click CMD → "Run as administrator"
"Response is EMPTY" (AV Blocked)
Trust the certificate (Step 3)
Add AV exclusions for:
C:\Python314\python.exe
C:\Users\User\Desktop\activator.py
C:\Users\User\AppData\Local\Temp\laragon_activator_certs\
Invalid License Key Format
Must match: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx (hex characters only)
Table
Valid	Invalid
aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee	short-key
12345678-1234-1234-1234-123456789abc	no-dashes-here
deadbeef-cafe-babe-feed-facefaceface	gggggggg-gggg-gggg-gggg-gggggggggggg
DNS Check Failed
cmd
ipconfig /flushdns
License Key Format
The server accepts any license key matching this pattern:
regex
^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$
Valid examples:
aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
12345678-1234-1234-1234-123456789abc
deadbeef-cafe-babe-feed-facefaceface
Invalid examples:
short-key — too short
no-dashes-here — missing dashes
gggggggg-gggg-gggg-gggg-gggggggggggg — g is not hexadecimal
