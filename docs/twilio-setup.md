# Twilio Setup

Use this walkthrough to create the Twilio side of the SIP connection for
`enigma-voice`.

## 1. Create a Twilio account

1. Sign up at [twilio.com](https://www.twilio.com/).
2. Verify your email address.
3. Verify your phone number.

TODO add screenshot

## 2. Add trial credit

Add $10 of trial credit to the Twilio account so you can buy a phone number and
place test calls.

TODO add screenshot

## 3. Buy a US local number

1. In the Twilio Console, go to **Phone Numbers > Buy a Number**.
2. Filter for **United States** local numbers.
3. Make sure the number has **Voice** capability.
4. Buy the number. A US local number is typically about $1 per month.

TODO add screenshot

## 4. Create a SIP trunk

1. Go to **Elastic SIP Trunking > Trunks**.
2. Create a new trunk named `enigma-voice`.
3. Leave **Origination** blank because inbound calls are received through
   LiveKit.
4. Under **Termination**, set the SIP URI to `<your-livekit-sip-uri>`. Get this
   value from the LiveKit Cloud SIP settings.
5. Configure **Authentication** with either:
   - IP ACL containing LiveKit's IP ranges.
   - Credential list. This is recommended for local development.

TODO add screenshot

## 5. Associate the number with the trunk

1. Open the `enigma-voice` trunk.
2. Go to the **Numbers** tab.
3. Add the US local number you bought in step 3.

TODO add screenshot

## 6. Copy values into `.env`

Copy these Twilio values and put them in `.env`:

- Account SID
- Auth Token
- Trunk SID
- Phone number

TODO add screenshot
