# Telnyx Setup — enigma-voice

Walkthrough for provisioning a Telnyx phone number + SIP Connection for use with LiveKit SIP. Replaces `twilio-setup.md`.

## Why Telnyx
- ~30-50% cheaper than Twilio at scale
- Owns its tier-1 carrier network
- Built-in SIP debugging (PCAP capture per call)
- $5 minimum deposit (vs Twilio's $20)

## 1. Sign up

1. Go to https://telnyx.com/sign-up
2. Verify email + phone
3. Complete identity check (required for number purchase — driver's license or passport upload, ~10 min review)
4. Mission Control Portal: https://portal.telnyx.com

## 2. Fund the account

1. Portal → **Wallet** (top-right) → **Add funds**
2. Minimum $5. Suggest $20 for dev runway.

## 3. Buy a phone number

1. Portal → **Numbers** → **My Numbers** → **Buy Numbers**
2. Country: United States. Locality: pick any (cheapest are usually OK)
3. Filter: "Voice" capability
4. Pick a number → **Add to Cart** → **Place Order**
5. Number provisioning is instant for US local

## 4. Create an Outbound Voice Profile

Required for outbound calling. One profile can serve multiple SIP Connections.

1. Portal → **Voice** → **Outbound Voice Profiles** → **Add New Profile**
2. Name: `enigma-voice-outbound`
3. Traffic type: **Conversational**
4. Service plan: **Global** (or US-only if you only call US)
5. Daily spend limit: $5 (sane dev cap)
6. Save → copy the profile id (`OVP-...`)

## 5. Create the SIP Connection (the trunk)

1. Portal → **Voice** → **SIP Connections** → **Add SIP Connection**
2. Connection type: **FQDN** (recommended — no IP whitelist headaches)
3. Name: `enigma-voice`

### Inbound tab
- **SIP Transport Protocol**: TLS (LiveKit prefers TLS)
- **Inbound options** → **Generate ringback tone**: off
- **Channel limit**: leave default (no concurrent cap for dev)

### Outbound tab
- **Outbound Voice Profile**: pick the `enigma-voice-outbound` profile from step 4
- **Localization**: US

### Authentication & Routing → FQDN
Add LiveKit's SIP signaling FQDN:
- **FQDN**: paste your LiveKit project's SIP URI domain (you'll grab this in `livekit-sip.md` step 3 — come back and add it)
- **Port**: 5060
- **DNS Record Type**: A

### Numbers tab
- Assign the phone number bought in step 3 to this connection

6. Save. Copy the **Connection ID** (numeric, shown in URL `/connections/<ID>`)

## 6. Get SIP credentials (for LiveKit outbound trunk auth)

If you chose FQDN auth in step 5, LiveKit authenticates by IP — but for outbound calls **from** LiveKit **to** Telnyx you need Telnyx-side credentials too.

Easier path: switch the SIP Connection to **Credentials** auth (same screen, **Authentication & Routing** tab):
1. Generate username + password (Telnyx auto-suggests)
2. Save them — you'll paste into LiveKit's outbound trunk yaml

If you keep FQDN: LiveKit's SIP egress IPs must be in Telnyx's allowed list (Telnyx provides default; usually no action needed).

## 7. Add to `.env`

```bash
TELNYX_API_KEY=<from Portal → API Keys → Create API Key (V2)>
TELNYX_PHONE_NUMBER=+1XXXXXXXXXX
TELNYX_SIP_CONNECTION_ID=<numeric id from step 5>
TELNYX_SIP_USERNAME=<if using credentials auth>
TELNYX_SIP_PASSWORD=<if using credentials auth>
TELNYX_OUTBOUND_VOICE_PROFILE_ID=OVP-...
```

## 8. Continue with LiveKit SIP wiring

See `docs/livekit-sip.md` — substitute Telnyx's termination URI in the outbound trunk yaml:

```yaml
address: sip.telnyx.com   # Telnyx termination FQDN
```

## Test call (smoke)

After completing `livekit-sip.md`:
```bash
# inbound: dial your Telnyx number from your cell → agent picks up
# outbound:
curl -X POST http://localhost:8000/calls/outbound \
  -H "X-API-Key: $OUTBOUND_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"phone":"+1YOURCELLNUMBER","name":"Test","context":"smoke"}'
```

## Debugging

Telnyx Portal → **Reporting** → **Debugging** → pick the call → download PCAP. Wireshark-readable. Twilio doesn't expose this without a support ticket.
