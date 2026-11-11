# Accessibilità

Accessibilità WCAG 2.2 AA, prestazioni e SEO tecnico sono obiettivi di sviluppo, non certificazioni. I test automatici e le prove di viewport non dimostrano conformità completa.

## Struttura, navigazione e focus

Header/footer semantici, un elemento `main` e skip link verso `#main-content`. I widget opzionali usano titoli di livello 2; i contenuti devono mantenere una gerarchia coerente. Menu con un unico elenco e pulsante nativo, `aria-expanded` e `aria-controls`; sottomenu raggiungibili con mouse e tastiera, Escape e ripristino del focus. Non sono ruoli ARIA da applicazione né un dialogo con focus trap. Senza JavaScript tutti i collegamenti restano utilizzabili. Dettagli implementativi in [Architettura](architecture.md).

Il CSS include `:focus-visible`. La verifica manuale deve considerare i contenuti e gli stili espliciti aggiunti dagli autori, oltre ai default del tema. Dimensioni relative e zoom non bloccato; viewport stretta non equivale a zoom reale.

## Contrasto e avvisi informativi

Il controllo informativo “Color contrast” in Colors mostra stato testuale, rapporto e soglia per testo/sfondo, link/sfondo, testo normale dei pulsanti/primario e testo/link sugli sfondi di header e footer. Il riferimento 4,5:1 riguarda il testo di dimensione normale: non è una verifica di loghi, icone, bordi dei componenti, stili dei plugin o conformità dell’intero sito. Stati hover/focus e identificazione dei link richiedono verifiche separate. Il confronto usa il rapporto non arrotondato; la visualizzazione mostra due decimali.

Il pannello PHP rimane leggibile nel documento ricevuto dal server se lo script del tema manca. La nota statica indica di ricaricare dopo il salvataggio; quando lo script è disponibile viene sostituita dalla spiegazione degli aggiornamenti immediati. Questo fallback informativo non rende il Customizer del core interamente utilizzabile senza JavaScript.

Gli aggiornamenti visivi seguono gli eventi nativi `input` e `change` dei campi renderizzati dal tema tramite il controllo colore e il binding pubblico `link()`. Nessun accesso al DOM interno del Customizer, a Backbone o al proxy. Una live region separata, inizialmente vuota, usa `role="status"`, `aria-live="polite"` e `aria-atomic="true"`; aggiorna soltanto i risultati cambiati dopo 750 ms di pausa, senza spostare il focus. Non vengono annunciati aggiornamenti identici. L’effettiva lettura richiede comunque verifica manuale con screen reader.

Il riferimento è [WCAG 2.2, contrasto del testo](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). Le costanti sRGB e la soglia sono definite una sola volta in `githeme_contrast_rules()` e passate a JavaScript. Le implementazioni PHP/JS della stessa formula WCAG sono verificate con casi condivisi e test di parità. `githeme_contrast_report()` restituisce anche lo stato non calcolabile per input invalidi. I consigli non modificano colori scelti né bloccano il salvataggio; la validazione sintattica esistente resta separata. Il testo dei pulsanti sceglie automaticamente bianco o nero con contrasto migliore. Superfici, bordi e testi secondari restano derivati dalla palette.

`githeme_contrast_ratio()` calcola il rapporto, `githeme_button_text_color()` sceglie il foreground automatico e `githeme_contrast_warnings()` produce gli avvisi PHP. Il confronto per le sette coppie non comprende ogni possibile stato di interazione o contenuto dei plugin. L'hover FX sul secondario usa un foreground automatico separato; vedere [FX Shortcodes](fx-shortcodes.md).

## Tipografia e font locali

I font WOFF2 sono locali e non modificati, con licenze SIL OFL 1.1 e provenienza documentata in [provenienza e licenze dei font](../assets/fonts/SOURCES.md). Il tema dichiara solo le due varianti variabili, normale e corsiva, della famiglia selezionata: il browser scarica i file quando il contenuto li usa. Nessun preload forzato e nessun font caricato dal tema con lo stack di sistema. I plugin possono avere impostazioni font proprie, indipendenti dal tema.

Atkinson Hyperlegible Next è una delle scelte disponibili; non è imposto e la sua selezione non costituisce una verifica dell'accessibilità dei contenuti. Restano disponibili stack di sistema, Source Sans 3 e Source Serif 4.

## Movimento ridotto

Non sono necessarie animazioni per usare la navigazione. Il foglio opzionale FX elimina le transizioni dei pulsanti con `prefers-reduced-motion: reduce`; l'indicatore Details non richiede una transizione. Plugin e contenuti esterni possono avere preferenze proprie da verificare.

Lo slider nativo usa Scroll Snap e scorrimento orizzontale senza autoplay. Con JavaScript aggiunge pulsanti nominati e corregge la visibilità delle immagini focalizzate; il movimento ridotto rende immediati gli spostamenti dei pulsanti. Senza script restano link e scorrimento nativo: Firefox può lasciare un'immagine focalizzata parzialmente visibile finché l'utente non scorre. Le immagini fuori schermo non vengono nascoste alle tecnologie assistive.

## Verifiche che richiedono una persona

- Attivazione, pagine/articoli, elenchi, ricerca, 404 e contenuti protetti da password.
- Homepage statica con e senza FX Builder; tema con plugin FX disattivati.
- Menu annidati, tastiera, Escape, cambio larghezza, zoom e JavaScript disattivato.
- Logo, titoli lunghi, immagini, tabelle e contenuti dell'editor classico.
- Customizer: anteprima e pubblicazione del logo, menu e widget; aggiunta del primo widget, riordino, modifica e rimozione dell'ultimo.
- Commenti, risposte annidate e paginazione.

Restano necessari screen reader, dispositivi touch reali, ingrandimento e lettura dei contenuti effettivi. Le mutazioni della live region non attestano ciò che viene pronunciato da VoiceOver o altri lettori. Le procedure e i limiti dei test sono in [Sviluppo](development.md).
