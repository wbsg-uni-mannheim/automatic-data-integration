# Schreibrichtlinien für das Paper

## Zielgruppe

- **Erfahrene Reviewer** die das Feld seit 20 Jahren kennen
- Nichts Langweiliges oder Triviales schreiben - die wissen das alles schon
- **Nicht belehrend** über Grundlagen schreiben
- Workshop-Paper für Beyond SQL at ICDE 2026

## Format

- **8 Seiten PLUS References** (nicht inklusive!)
- **Kein Appendix**
- Weniger Text, mehr Tabellen ist okay
- Jeder Satz muss zählen

## Kernthese (WICHTIG!)

**Wir ersetzen NICHT die gesamte Pipeline, sondern die Human-Inputs eines Data Engineers:**

1. **Trainingsdaten** für Entity Matching
2. **Schema-Mapping** Konfiguration
3. **Value Mappings** für Normalisierung
4. **Validation-Set** für Fusion

**Traditionelle, in Code implementierte Methoden bleiben** für die effiziente Ausführung (Kosten, Skalierbarkeit). Das ist eine **bewusste Entscheidung**, kein Kompromiss.

> Das muss in der Intro/Motivation genau so stehen, sonst klingt es nach "LLM ersetzt alles"

**Titel:** "Automatic" statt "Unsupervised" — die Pipeline nutzt LLM-Wissen + Web RAG, das ist nicht unsupervised. Related Work nutzt auch "Auto", also passt der Titel besser.

**Scalability im Abstract ansprechen** — Zielgruppe sind Datenbanker. Klar machen, dass effiziente rule/code-basierte Methoden für die Transformationen verwendet werden und LLMs nur zur Konfiguration/Training.

## Stil & Ton

### DO

- **Knapp und präzise** schreiben
- **Klare Aussagen pushen** - Senior-Leute mögen das (z.B. "$4.50 vs $460")
- Im Titel darf man **etwas overclaimen**, im Abstract dann einfangen
- Originalquellen aus Google Scholar verwenden
- Zahlen und konkrete Ergebnisse in den Vordergrund
- **Selbsterklärende Begriffe verwenden** — wenn ein Term nicht selbsterklärend ist, umbenennen (z.B. "fusion validation" statt "fusion strategy" wenn es um die Validierung geht)

### DON'T

- **Niemals "--"** (Gedankenstriche) verwenden - Telltale-Sign für AI
- **Keine Semikolons (;)** verwenden - stattdessen zwei Sätze oder Komma mit Konjunktion
- Kein LLM-typischer Stil:
  - Keine Füllwörter
  - Keine generischen Formulierungen
  - Keine übertriebenen Hedging-Phrases ("it is important to note that...")
  - Keine Aufzählungen wo Fließtext besser wäre
- Nicht belehrend über Grundlagen schreiben
- Keine selbstverständlichen Dinge erklären

## Inhaltliche Prinzipien (aus Chris's Editorial-Kommentaren)

### Nur beobachtete Limitations diskutieren, keine generischen

> "Let's just discuss limitations that we have seen in the experiments, not generic ones."

Keine theoretischen Limitationen aufzählen, die wir nicht in den Experimenten gesehen haben. Beispiel: Nicht "LLM labeling fails on domain-specific codes" schreiben, wenn das in unseren Use Cases nie passiert ist.

### Keine unvalidierten Vergleiche im Detail präsentieren

> "The costs too much depend on the K=20 of the embedding based blocker which we did not validate. Thus, let's not present the comparison to the full labeling in detail, but mention it in the discussion as an argument."

Wenn ein Parameter nicht validiert wurde (z.B. K=20), keine detaillierten Kostenvergleiche darauf aufbauen. Stattdessen kurz in der Discussion erwähnen.

### Nicht zu spezifische, unerforschte Dinge erwähnen

> "Let's not mention this here as very specific and not explored yet."

Nur Dinge diskutieren, die wir tatsächlich untersucht oder zumindest beobachtet haben.

### Abschnitte kürzen, die hauptsächlich Probleme zeigen

> "The post-processing section is a candidate for shortening if we require space. We could also just mention that we clean the clusters and do not provide so many details."

Wenn ein Abschnitt hauptsächlich zeigt, dass etwas nicht optimal ist, kurz halten. Keine ausführliche Tabelle dafür, nur erwähnen.

### Signifikanz nicht übertreiben

> "Besser rausnehmen, da Schema Matching für einfache Datasets nicht labor-intensive ist."

Keine Claims machen, die die Bedeutung von etwas übertreiben. Schema Matching als "traditionally labor-intensive" bezeichnen, wenn unsere Datasets einfach sind, wäre irreführend.

### Auf den relevantesten Aspekt fokussieren

> "Rausnehmen, da für die Auswahl nicht Kosten der relevanteste Faktor sind, sondern ob das LLM die richtigen Werte kennt oder ob RAG notwendig ist."

Nicht auf Kosten fokussieren, wenn die eigentliche Frage ist, ob das LLM die richtigen Werte kennt. Den Kern des Problems identifizieren und darüber schreiben.

### Offensichtliches Engineering nicht als "Future Research" verkaufen

> "Zu offensichtlich und auch kein Research, sondern müsste man einfach machen. Daher bei future research eher nicht erwähnen."

Z.B. "temporale Metadaten an den Fusion-Generator übergeben" ist kein Research, sondern Engineering. Future Work sollte echte Forschungsfragen enthalten (Agents, Human-Agent Collaboration, Benchmarks).

### Prozesse explizit beschreiben

> "Es ist unklar wann der Prozess aufhört und warum sich 100 Paare ergeben. Bitte das Stopping-Kriterium noch explizit nennen."

Stopping-Kriterien, Parametergrößen und Entscheidungslogik immer explizit nennen. Keine vagen Beschreibungen wie "and others" wenn man die konkreten Methoden auflisten kann.

### Tabellenzahlen müssen zusammenpassen

> "There is a bug in the table. 14016 input records - 2062 clusters does not fit together with 12,768 output records. Please adjust the numbers."

Immer prüfen, ob die Zahlen in den Tabellen numerisch konsistent sind. Nicht nur die einzelnen Zellen, sondern auch die Beziehungen zwischen Tabellen und Text.

### Results-Absätze nicht zu tabellenlastig

> "Do not repeat content of table so much, but draw more generic conclusions."

Results-Absätze sollen nicht jede Zahl aus der Tabelle wiederholen. Stattdessen Ranges angeben (z.B. "27-41%") und generische Schlussfolgerungen ziehen. Der Leser hat die Tabelle vor sich.

## Related Work

- **Max. 2 Absätze pro Aufgabe**
- Eher im Kontext einweben (Diskussion, Limitations) statt als große eigene Section
- Beispiel: "Schema Matching bei uns war trivial, keine 1-zu-M Mappings" -> dann Limitation nennen
- Klar abgrenzen zu verwandten Ansätzen (z.B. KGPipes: anderes Datenmodell, LLM für weniger Tasks, teurer da LLM direkt matched)

## Limitations

**Ehrlich benennen, aber nur beobachtete:**

- Companies: Recency-Problem (Firmensitze/Umsätze ändern sich)
- Fusion Accuracy bei Duration: Null-Werte-Problem
- Schema Matching: nur einfache 1:1-Mappings getestet
- Kleine Testsets (15-23 Beispiele bei Fusion)
- LLM-Wissen hat temporale Grenzen
- Datasets sind öffentlich und wahrscheinlich in GPT-5.2's Trainingsdaten

## Tabellen-Konventionen

- **"LLM"** statt "Auto"
- **"Human"** statt "Provided"
- Subtotals raus wenn sie nichts aussagen
- **Averages statt Totals** wenn die Anzahl der Use Cases variieren könnte
- Grandtotals nur wenn informativ
- Use-Case-Namen konsistent formatieren
- **LLM-Spalten zuerst** (ist unser Beitrag), dann Human
- **Lower Bounds markieren** mit >= wo Schätzungen vorliegen

## Referenzen

- **Immer auf Existenz prüfen** (Seitenzahlen, Venue, Autoren)
- Originalquellen bevorzugen (Google Scholar)
- Paper-Titel direkt kopieren ist okay
- Nicht zu viele - Seitenlimit beachten
- **Vorsicht vor halluzinierten Referenzen!**

## Discussion-Abschnitte

- **Per-Section Discussion:** Fokus auf taskspezifische Beobachtungen und Limitations
- **End-to-End Discussion:** Synthese über alle Aspekte (Struktur, Runtime, Kosten), nicht nur eine Dimension
- Nicht Zahlen aus dem Results-Absatz wiederholen, sondern höhere Schlussfolgerungen ziehen
- Mit einer klaren Takeaway-Message enden

## Conclusion

- **Future Work als Fließtext**, nicht als itemisierte Liste
- Nur echte Forschungsfragen, kein offensichtliches Engineering
- Gute Themen: Agentic approaches, Human-Agent Collaboration, End-to-End Benchmarks
- **Coding Agents** könnten bei Normalisierung und Fusion ansetzen
- These: Daten + Domain Knowledge zusammen -> bessere Ergebnisse

## Checkliste vor Einreichung

- [ ] Intro: Kernthese klar formuliert (LLM konfiguriert, ersetzt nicht)
- [ ] Abstract: Scalability erwähnt
- [ ] Alle Tabellen: "LLM"/"Human" Labels, LLM-Spalten zuerst
- [ ] Related Work: max 2 Absätze pro Task
- [ ] Referenzen: alle geprüft und existierend
- [ ] Seitenlimit: 8 Seiten inkl. References
- [ ] Keine "--" (Gedankenstriche) im Text
- [ ] Keine Semikolons (;) im Text
- [ ] Zahlen in Tabellen gegen Code verifiziert
- [ ] Zahlen zwischen Tabellen und Text konsistent
- [ ] Zahlen zwischen verschiedenen Sections konsistent (z.B. Fusion-Accuracy in Results vs. Conclusion)
- [ ] Keine generischen/theoretischen Limitations, nur beobachtete
- [ ] Keine unvalidierten detaillierten Vergleiche
- [ ] Results-Absätze ziehen Schlussfolgerungen statt Tabellenwerte aufzulisten
- [ ] Laptop-Specs für Runtime angeben (Prozessor, RAM)
- [ ] Normalisierungskosten in Cost-Tabelle prüfen
