# Example call 2: the clerk hands out the market-location number

An illustrative transcript of a Nomos clearing call, so you can hear what a good call sounds
like. All identifiers are synthetic.

This is `CASE-C` from `fixtures.json`. The automated identification never gave us a usable
market-location number (the MaLo) for this address, because the building has several connections.
We had already emailed about it, with a subject line containing the market-location number we held
and the word Nomos, but got no reply. So we call, and the clerk reads out the correct number.

---

**[Automated phone menu]** Willkommen bei der Elbe Energienetze GmbH. Für Fragen zur
Marktkommunikation drücken Sie die 2.

> The agent recognises it is a menu, not a person, and presses 2 on the keypad.

**[Sachbearbeiterin]** Elbe Energienetze, Marktkommunikation, mein Name ist Petra Brandt, guten
Tag.

**[Agent]** Guten Tag, hier spricht ein KI-Assistent im Auftrag des Stromlieferanten Nomos. Wir
wollen einen Kunden bei Ihnen anmelden, aber die Marktlokation, die wir haben, passt nicht zur
Adresse, und wir bekommen über die automatische Identifikation keine eindeutige zurück. Wir hatten
Ihnen dazu auch schon geschrieben, Betreff mit der MaLo sieben, eins, null, null, fünf, fünf,
zwei, drei, vier, neun, acht und Nomos, aber leider noch keine Rückmeldung erhalten.

> The agent says it is an artificial intelligence first, explains the problem, and points to the
> earlier email so the clerk can find the case.

**[Sachbearbeiterin]** Kein Problem, das klären wir kurz. Um welche Adresse geht es?

**[Agent]** Musterweg 28a, zweiter Stock links, in Hamburg-Altona. Das Haus hat wohl mehrere
Lieferstellen, deshalb ist die Adresse allein nicht eindeutig. Ich habe aber die Zählernummer des
Kunden: eins, E, S, Y, neun, null, null, null, null, drei, null, null, null, drei.

**[Sachbearbeiterin]** Ah, mit der Zählernummer finde ich es. Die richtige Marktlokation ist die
sieben, eins, null, null, fünf, fünf, zwei, drei, neun, eins, eins.

**[Agent]** Darf ich kurz zurücklesen, sieben, eins, null, null, fünf, fünf, zwei, drei, neun,
eins, eins?

**[Sachbearbeiterin]** Genau, die ist richtig.

**[Agent]** Wunderbar, vielen Dank. Dann melden wir den Kunden mit dieser Marktlokation neu an.
Schönen Tag noch, Tschüss!

---

**Why this is a win.** The automated channel and the email both failed, but on the phone the
agent gave the clerk the one detail that disambiguates the building (the meter number), walked
away with the correct market-location number, and read it back one digit at a time to be sure. The
next step is clear: re-send the registration against the corrected number.
