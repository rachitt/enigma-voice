# LiveKit SIP Setup

Use this walkthrough to wire Twilio SIP trunks into LiveKit Cloud for inbound
and outbound calling.

## 1. Install the LiveKit CLI

Install the LiveKit CLI with pip:

```bash
pip install livekit-cli
```

Alternatively, download it from
[github.com/livekit/livekit-cli](https://github.com/livekit/livekit-cli).

## 2. Authenticate with LiveKit Cloud

```bash
lk cloud auth
```

## 3. Create the inbound trunk

Create `inbound-trunk.yaml`:

```yaml
trunk:
  name: enigma-voice-inbound
  numbers: ["+15555550123"] # your Twilio number
  auth_username: ""
  auth_password: ""
```

Create the trunk:

```bash
lk sip inbound create inbound-trunk.yaml
# returns SIP_INBOUND_TRUNK_ID, paste into .env
```

## 4. Create the outbound trunk

Create `outbound-trunk.yaml`:

```yaml
trunk:
  name: enigma-voice-outbound
  address: <twilio-trunk-termination-uri>.pstn.twilio.com
  numbers: ["+15555550123"]
  auth_username: <twilio-trunk-cred-username>
  auth_password: <twilio-trunk-cred-password>
```

Create the trunk:

```bash
lk sip outbound create outbound-trunk.yaml
# returns SIP_OUTBOUND_TRUNK_ID
```

## 5. Create the inbound dispatch rule

Create `dispatch-rule.yaml`:

```yaml
rule:
  dispatch_rule_individual:
    room_prefix: inbound-
trunk_ids: ["<SIP_INBOUND_TRUNK_ID>"]
room_config:
  agents:
    - agent_name: enigma-voice
```

Create the dispatch rule:

```bash
lk sip dispatch create dispatch-rule.yaml
```

## 6. Verify inbound calling

Place a test call to the Twilio number. LiveKit logs should show an inbound SIP
participant and an agent dispatch.
