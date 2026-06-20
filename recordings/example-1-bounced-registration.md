# Example call 1: a registration that bounced

An illustrative transcript of a Nomos clearing call, so you can hear what a good call sounds
like. All identifiers are synthetic.

This is `CASE-A` from `fixtures.json`: a registration that bounced with "Marktlokation nimmt
nicht teil" (this market location is not taking part).

---

**[Automated phone menu]** Willkommen bei der Bayern Werknetz GmbH. Bitte wählen Sie eine der
folgenden Optionen. Für Fragen zum Lieferantenwechsel drücken Sie die 1.

> The agent recognises it is a menu, not a person, and presses 1 on the keypad. No one is on the
> line yet.

**[Sachbearbeiterin]** Guten Tag, Sie sprechen mit Sandra Jerke.

**[Agent]** Guten Tag, hier spricht ein KI-Assistent im Auftrag des Stromlieferanten Nomos. Wir
versuchen, einen Kunden in Ihrem Netz anzumelden. Wir haben die MaLo von Ihnen bekommen, aber die
Netzanmeldung wird mit "Marktlokation nimmt nicht teil" abgelehnt. Darf ich die MaLo kurz
ansagen? Das wäre die fünf, null, drei, eins, zwei, vier, sieben, acht, neun, null, eins.

> The agent says it is an artificial intelligence first, states the case in two sentences, and
> offers the market-location number up front, read out one digit at a time.

**[Sachbearbeiterin]** Bei welcher Lieferstelle sollten wir denn rauskommen?

**[Agent]** In Mainz-Kastel, Musterstraße 4.

**[Sachbearbeiterin]** Und zu wann haben Sie die Anmeldung geschickt?

**[Agent]** Zuletzt am 12. Juni, gewünschter Lieferbeginn der 14. Juli 2027.

**[Sachbearbeiterin]** Moment, ich schaue mal. Die MaLo finde ich. Aber der Zähler dazu ist laut
meinem System am 18.05. ausgebaut worden. Das war nämlich ein Baustromzähler. Da muss eine
komplett neue Anlage angelegt werden, auf die alte MaLo können Sie nichts mehr anmelden.

**[Agent]** Verstanden. Also: der Baustromzähler wurde am 18. Mai ausgebaut, und es braucht eine
komplett neue Anlage. Dann melden wir uns beim Kunden und klären das. Vielen Dank, schönen Tag
noch, Tschüss!

---

**Why this is a win.** It did not end with a reference number. It ended with the real reason (the
meter was a temporary construction-site meter, removed on 18.05, so the old market location is
dead and a new connection is needed) and the next step (go back to the customer). That is a fully
cleared case.
