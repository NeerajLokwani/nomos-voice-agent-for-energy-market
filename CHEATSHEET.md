# Market communication in 5 minutes

A cheat-sheet for non-German, non-energy builders. You don't need to understand the German
energy market. You need to understand **one phone call**: who you are, which case you're
chasing, and what you want to walk away with.

## The one-sentence model

A customer signed up for electricity with **Nomos** (the supplier). To actually deliver power,
Nomos has to register that customer's connection with the **local grid operator** by exchanging
automated messages. This exchange is "MaKo" (Marktkommunikation). Sometimes a message bounces or
goes silent. When the automation can't fix it, a human (now: your agent) phones the grid operator
and talks it out. That call is the whole task.

## Who's who on the call

| Term | Say it as | What it is |
|---|---|---|
| Lieferant | supplier | Nomos. You call on behalf of Nomos. |
| Netzbetreiber / VNB | grid operator | Owns the wires and the meter. The company you phone. |
| Kunde | customer | The household that signed up with Nomos. |

## The IDs you're chasing

| Term | Say it as | What it is |
|---|---|---|
| Marktlokation / MaLo-ID | the market location / its 11-digit ID | The official ID of the delivery point. This is the case number you read out. |
| Zähler / Zählernummer | the physical meter / its serial | The metal box on the wall. A meter can be swapped, or removed (ausgebaut). Different format from a MaLo. |
| Lieferstelle / Lieferadresse | the delivery address | Where the power goes. The clerk uses it to find the case. |

## What's gone wrong (the cases)

| Term | Plain English |
|---|---|
| (Netz-)Anmeldung | The registration you sent to start supplying the customer. The thing that's stuck. |
| Lieferantenwechsel | The customer switching supplier (to Nomos). Usually the right option in the phone menu. |
| "Marktlokation nimmt nicht teil" | "This market location is not participating." Your registration bounced. Find out why. |
| APERAK | The automated "message received / rejected" receipt. Got an APERAK but no confirmation means processing stalled. |
| Baustromzähler | A temporary construction-site meter. Removed when the building is done, so the connection then needs a brand-new setup. |
| Zähler ausgebaut | "Meter removed." If the meter behind your MaLo is ausgebaut, that MaLo is effectively dead. |
| neue Anlage | A new installation/connection has to be created. Often the real next step. |
| Klärfall | A clarification case, flagged for manual handling. |
| Vorgangsnummer | A ticket / reference number. Nice to get, but not always the win. |

## What "winning the call" means

The win is usually a **diagnosis plus a next step, not a ticket number**. Example: "the meter
was a construction-site meter, it's been removed, so the connection needs a new setup, go back to
the customer." Your agent should walk away with (1) the real reason the case is stuck, and (2)
the correct next step. An agent that hangs up with "okay danke" but no reason and no next step has
failed, however good it sounded.

## The identity gate is light

The clerk asks a few simple things and then volunteers the system info: which delivery town, the
MaLo, when the registration was sent, the requested start date. No Marktpartner-ID, no password,
no security interrogation. Walk in with those four facts and offer them proactively.

## Call texture

German, polite, brisk (about two minutes). Professional register ("Guten Tag", "Darf ich
kurz...", "Schönen Tag noch, Tschüss"). The clerk is helpful, not adversarial. There's an
automated phone menu first ("für Lieferantenwechsel drücken Sie die 1") that your agent navigates
by pressing the right number on the keypad before a human answers.

## Two rules, non-negotiable

- Your agent says it's an AI as its first words to a human (EU AI Act).
- Synthetic data only. Every name and ID in `fixtures.json` is fake. Never use real customer data,
  and only ever dial the clerk-agent number we give you, never a real grid operator.
