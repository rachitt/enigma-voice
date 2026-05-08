# LiveKit SIP Setup

Wire Telnyx SIP into LiveKit Cloud for inbound + outbound calling. Pairs with `docs/telnyx-setup.md` (run that first).

## 1. Install the LiveKit CLI

```bash
brew install livekit-cli
# or: curl -sSL https://get.livekit.io/cli | bash
```

## 2. Authenticate with LiveKit Cloud

```bash
lk cloud auth
```

## 3. Find your LiveKit SIP signaling URI

```bash
lk project list
lk sip status
```
Copy the **SIP URI** (looks like `<project>.sip.livekit.cloud`). Paste into Telnyx SIP Connection's FQDN field (`docs/telnyx-setup.md` step 5).

## 4. Create the inbound trunk

`inbound-trunk.yaml`:

```yaml
trunk:
  name: enigma-voice-inbound
  numbers: ["+1XXXXXXXXXX"]   # your Telnyx number
  auth_username: ""
  auth_password: ""
```

```bash
lk sip inbound create inbound-trunk.yaml
# returns SIP_INBOUND_TRUNK_ID -> paste into .env
```

## 5. Create the outbound trunk

`outbound-trunk.yaml`:

```yaml
trunk:
  name: enigma-voice-outbound
  address: sip.telnyx.com
  numbers: ["+1XXXXXXXXXX"]
  auth_username: <TELNYX_SIP_USERNAME>   # from telnyx-setup.md step 6
  auth_password: <TELNYX_SIP_PASSWORD>
  transport: TLS
```

```bash
lk sip outbound create outbound-trunk.yaml
# returns SIP_OUTBOUND_TRUNK_ID -> paste into .env
```

## 6. Create the inbound dispatch rule

`dispatch-rule.yaml`:

```yaml
rule:
  dispatch_rule_individual:
    room_prefix: inbound-
trunk_ids: ["<SIP_INBOUND_TRUNK_ID>"]
room_config:
  agents:
    - agent_name: enigma-voice
```

```bash
lk sip dispatch create dispatch-rule.yaml
```

## 7. Verify inbound

Dial your Telnyx number from your cell. LiveKit logs:
```bash
lk room list
```
Should show inbound SIP participant + agent dispatch.

## 8. Verify outbound

Run agent worker + outbound API in two shells:
```bash
python agent.py dev
uvicorn outbound.server:app --port 8000
```

Trigger a call to your own cell:
```bash
curl -X POST http://localhost:8000/calls/outbound \
  -H "X-API-Key: $OUTBOUND_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"phone":"+1YOURCELL","name":"Test","context":"smoke"}'
```

Phone rings. Agent opens with greeting + lead context.
