# githeme

Tema classico generalista per ClassicPress, in fase iniziale di sviluppo.

## Ambiente di riferimento

- Core locale ClassicPress su `develop`, versione dichiarata `2.7.4+dev`.
- PHP **8.2** come riferimento di sviluppo. Versioni minime e matrice di compatibilità non ancora definite; gli header dei requisiti non sono dichiarati in questa fase.
- Nessun framework, compilazione degli asset o dipendenza obbligatoria da plugin.

## Funzioni iniziali

- Template classici per pagine, articoli, elenchi, ricerca e pagina 404.
- Header e footer semantici, menu principale e logo personalizzato.
- Menu mobile progressivo: senza JavaScript tutti i link restano visibili; sottomenu sempre visibili, senza interazioni basate soltanto sul passaggio del mouse.
- CSS responsive con custom properties, focus visibile e collegamento per saltare al contenuto.
- Immagini in evidenza, titolo documento e feed gestiti dal core; stili per l'editor classico e commenti nativi.
- Aree widget facoltative `homepage-hero` e `homepage-content` per la homepage statica; `footer-experimental` prima dei crediti.
- Quattro sezioni Customizer per colori, tipografia, larghezze/layout e header, con controlli standard e impostazioni `theme_mod`.
- Anteprima tramite ricaricamento, senza JavaScript Customizer proprio o selective refresh abilitato dal tema.

## Impostazioni globali

| Impostazione | Predefinito | Valori consentiti |
|---|---|---|
| Primario | `#14569a` | Colore esadecimale |
| Secondario | `#4b5563` | Colore esadecimale |
| Testo | `#202833` | Colore esadecimale |
| Sfondo | `#ffffff` | Colore esadecimale |
| Link | `#14569a` | Colore esadecimale |
| Font | Stack di sistema | Sistema, Source Sans 3, Source Serif 4, Atkinson Hyperlegible Next |
| Dimensione base | `1rem` | `1–1,375rem`, passo `0,0625` |
| Scala titoli | `1,25` | `1,125`, `1,2`, `1,25`, `1,333` |
| Larghezza contenuto | `46rem` | `36–60rem`, passo `1` |
| Larghezza estesa | `68rem` | `48–90rem`, passo `1` |
| Layout massimo | `76rem` | `60–100rem`, passo `1` |
| Altezza massima logo | `5rem` | `2–8rem`, passo `0,25` |
| Header | Identità a sinistra, menu a destra | In linea oppure identità centrata con menu sotto |

Le dimensioni restano relative alle preferenze del browser; lo zoom non è limitato. La scala dei titoli usa rapporti coerenti per tutti i livelli, condivisi con l'editor classico. Le larghezze sono massime, non dimensioni fisse: `contenuto ≤ estesa ≤ layout`. Gli elementi diretti del contenuto con classe `alignwide` o `alignfull` possono utilizzare rispettivamente la larghezza estesa o quella disponibile nel layout.

Valori incoerenti delle larghezze generano errori di validazione nel Customizer, anche quando più impostazioni cambiano insieme. Valori preesistenti non validi sono limitati soltanto nel rendering, segnalati nella sezione e nella schermata Temi e **mai riscritti automaticamente**.

Il controllo informativo “Color contrast” in Colors mostra stato testuale, rapporto e soglia per testo/sfondo, link/sfondo e testo normale dei pulsanti/primario. Il riferimento 4,5:1 riguarda il testo di dimensione normale: non è una verifica di loghi, icone, bordi dei componenti, stili dei plugin o conformità dell’intero sito. Stati hover/focus e identificazione dei link richiedono verifiche separate. Il confronto usa il rapporto non arrotondato; la visualizzazione mostra due decimali.

Il pannello PHP rimane leggibile nel documento ricevuto dal server se lo script del tema manca. La nota statica indica di ricaricare dopo il salvataggio; quando lo script è disponibile viene sostituita dalla spiegazione degli aggiornamenti immediati. Questo fallback informativo non rende il Customizer del core interamente utilizzabile senza JavaScript.

Gli aggiornamenti visivi seguono gli eventi nativi `input` e `change` dei campi renderizzati dal tema tramite il controllo colore e il binding pubblico `link()`. Nessun accesso al DOM interno del Customizer, a Backbone o al proxy. Una live region separata, inizialmente vuota, usa `role="status"`, `aria-live="polite"` e `aria-atomic="true"`; aggiorna soltanto i risultati cambiati dopo 750 ms di pausa, senza spostare il focus. Non vengono annunciati aggiornamenti identici. L’effettiva lettura richiede comunque verifica manuale con screen reader.

Il riferimento è [WCAG 2.2, contrasto del testo](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). Le costanti sRGB e la soglia sono definite una sola volta in `githeme_contrast_rules()` e passate a JavaScript. Le implementazioni PHP/JS della stessa formula WCAG sono verificate con casi condivisi e test di parità. `githeme_contrast_report()` restituisce anche lo stato non calcolabile per input invalidi. I consigli non modificano colori scelti né bloccano il salvataggio; la validazione sintattica esistente resta separata. Il testo dei pulsanti sceglie automaticamente bianco o nero con contrasto migliore. Superfici, bordi e testi secondari restano derivati dalla palette.

I font WOFF2 sono locali e non modificati, con licenze SIL OFL 1.1 e provenienza documentata in `assets/fonts/SOURCES.md`. Il tema dichiara solo le due varianti variabili, normale e corsiva, della famiglia selezionata: il browser scarica i file quando il contenuto li usa. Nessun preload forzato e nessun font caricato dal tema con lo stack di sistema. I plugin possono avere impostazioni font proprie, indipendenti dal tema.

L'editor classico riceve famiglia, dimensione, scala, colori e larghezza tramite `tiny_mce_before_init` / `teeny_mce_before_init` e il foglio editor locale. Eventuali stili inline nei contenuti o impostazioni dei plugin possono prevalere.

## Test delle impostazioni

Con ClassicPress caricato e PHP 8.2, dalla radice del progetto:

```sh
wp eval-file src/wp-content/themes/githeme/tests/global-settings.php
```

Il test usa le API reali e valori sovrascritti soltanto in memoria: non salva impostazioni e non crea contenuti. Verifica valori limite, ordine delle larghezze, input invalidi, avvisi non bloccanti, font selezionati, CSS dell'editor e classi header. La verifica di anteprima/pubblicazione del Customizer e delle richieste font effettive usa separatamente un browser autenticato.

Accessibilità WCAG 2.2 AA, prestazioni e SEO tecnico sono obiettivi di sviluppo, non certificazioni della versione iniziale.

## Uso essenziale in MAMP Pro

1. Verificare il PHP assegnato al sito (riferimento: 8.2).
2. Attivare **githeme** da Aspetto → Temi.
3. Assegnare un menu alla posizione “Primary menu” e impostare eventualmente un logo dall'identità del sito.
4. Per una homepage statica scegliere una normale pagina nelle impostazioni di lettura. Non esiste `front-page.php`: la pagina usa il normale rendering e può essere costruita con FX Builder.
5. Provare l'area “Footer — experimental” da Aspetto → Widget e dal Customizer.

## Homepage statica e widget

1. Creare o scegliere una pagina pubblicata, con i contenuti nell’editor classico o, facoltativamente, con FX Builder.
2. In Impostazioni → Lettura selezionare una pagina iniziale statica e assegnare quella pagina; scegliere eventualmente una pagina distinta per gli articoli.
3. In Aspetto → Widget, oppure nelle aree widget del Customizer, aggiungere widget a **Homepage Hero** e/o **Homepage Content**.

L’ordine è header, Homepage Hero, contenuto della pagina, Homepage Content, footer. Le due aree sono indipendenti e opzionali: senza widget non producono contenitori vuoti. La homepage continua a mostrare il normale contenuto della pagina, con il suo titolo. Usare titoli di livello 2 per i widget e una gerarchia coerente nei loro contenuti.

Hero dispone dell’intera larghezza della viewport; il widget decide il proprio layout interno. Homepage Content rispetta la larghezza massima del layout configurata nel tema. Colori, tipografia e larghezze continuano a usare le impostazioni globali. Contenuti di terze parti possono richiedere propri accorgimenti responsive.

Gli ID stabili delle aree sono `homepage-hero` e `homepage-content`. Funzionano tramite `register_sidebar()` e `dynamic_sidebar()`, senza API specifiche dei plugin. Non appaiono nella homepage con gli ultimi articoli, nella pagina separata degli articoli, nelle pagine interne o negli articoli singoli.

Non viene aggiunto `front-page.php`: restano valide la gerarchia nativa e i template assegnati alle pagine che utilizzano header e footer standard del tema. Template esterni che sostituiscono completamente header/footer devono gestire autonomamente il rendering. Non sono introdotti ordinamenti proprietari, nuove opzioni Customizer o sistemi di sezioni.

## Test della homepage

Dalla radice ClassicPress:

```sh
wp --path=src eval-file src/wp-content/themes/githeme/tests/homepage-widgets.php
wp --path=src --skip-plugins eval-file src/wp-content/themes/githeme/tests/homepage-widgets.php
```

Il test PHP non scrive nel database: verifica registrazione, aree vuote/popolate e contesti ammessi, comprese callback widget senza output.

Il test browser richiede l’ambiente Selenium esterno già disponibile e autorizzazione alle modifiche temporanee delle sole opzioni elencate nello script. Utilizza pagine/articoli di prova **già pubblicati**, senza modificarne il contenuto. Gli ID seguenti sono esempi dell’installazione locale; verificare quelli del proprio sito prima dell’esecuzione:

```sh
. /Volumes/Simo/Development/codex-browser-tools/env.sh
"$CODEX_BROWSER_ROOT/venv/bin/python" src/wp-content/themes/githeme/tests/homepage-widgets-browser.py \
  --url https://githeme:8890 --wp-path src \
  --front-page-id 9 --posts-page-id 15 --internal-page-id 5 --post-id 6 \
  --fx-content-id 16 --fx-page-id 10
```

Gli argomenti FX sono facoltativi e si riferiscono ai fixture locali con i marcatori `githeme-test-*`; ometterli dove non disponibili. Il test usa esplicitamente il profilo Firefox dedicato, esegue screenshot e osservazioni BiDi senza registrare credenziali. Salva snapshot privati delle opzioni nell’area artifacts sul volume Simo e ripristina valori, tipi, assenza e autoload, verificandoli anche in un nuovo processo WP-CLI. Controlla inoltre che i contenuti dei fixture e l’attivazione dei plugin rimangano invariati. Le viewport headless strette verificano il responsive, non emulano completamente uno smartphone.

## Plugin FX facoltativi

Il tema usa `the_content()` e le normali API widget; funziona senza FX Builder, FX Shortcodes e FX Builder Widgets. Non richiama direttamente le loro API. I contenuti creati con un plugin possono comunque dipendere dal plugin per il rendering.

Da verificare: CSS e formattazione FX Builder, parser FX Shortcodes nei diversi contesti e aggiornamento dei widget nel Customizer riscritto. FX Shortcodes non registra `[element]` come shortcode ordinario: `do_shortcode()` da solo non lo elabora. FX Builder Widgets può esporre pubblicamente il proprio tipo di contenuto e archivio.

## Verifiche manuali

- Attivazione, pagine/articoli, elenchi, ricerca, 404 e contenuti protetti da password.
- Homepage statica con e senza FX Builder; tema con plugin FX disattivati.
- Menu annidati, tastiera, Escape, cambio larghezza, zoom e JavaScript disattivato.
- Logo, titoli lunghi, immagini, tabelle e contenuti dell'editor classico.
- Customizer: anteprima e pubblicazione del logo, menu e widget; aggiunta del primo widget, riordino, modifica e rimozione dell'ultimo.
- Commenti, risposte annidate e paginazione.

Il Customizer locale differisce dalle implementazioni storiche: non basare integrazioni sulle variabili interne del suo proxy JavaScript.

## Compatibilità del Customizer

La doppia registrazione dei default di `develop` poteva cancellare la descrizione Colors. Il branch locale ClassicPress `fix/customizer-regressions` contiene la correzione esaminata separatamente; il tema non modifica il core.

La riscrittura JavaScript conserva un proxy incompleto: nel ramo esaminato `wp.customize(id, callback)` non è invocabile e le sottoscrizioni Value si perdono dopo modifiche tramite UI. Riproduzione minima e confini dell’integrazione: [tests/customizer-api-regression.md](tests/customizer-api-regression.md). L’informazione dinamica del tema usa eventi DOM standard sui propri input, non sostituisce l’API mancante. Modifiche programmatiche di terze parti che non emettono eventi non sono osservabili in modo affidabile finché la regressione pubblica del core non sarà risolta.

## Test del contrasto

Dalla radice ClassicPress, con WP-CLI, PHP e Node già disponibili:

```sh
wp --path=src eval-file src/wp-content/themes/githeme/tests/contrast.php
node src/wp-content/themes/githeme/tests/contrast.js
```

I test coprono coppie identiche, bianco/nero, soglie, valori intermedi, input invalidi, foreground automatico, markup PHP di fallback e parità tra i linguaggi. Non scrivono nel database.

Il test browser richiede Selenium già installato, l’ambiente esterno con `CODEX_BROWSER_ROOT`/`TMPDIR` sul volume Simo e una sessione autorizzata nel profilo dedicato. Non usa il launcher anonimo e non raccoglie credenziali. Eseguire solo con autorizzazione a modifiche temporanee dei theme_mod, poiché verifica anche la pubblicazione; conserva uno snapshot PHP tipizzato e lo ripristina esattamente in uscita:

```sh
"$CODEX_BROWSER_ROOT/venv/bin/python" tests/customizer-contrast-browser.py --url https://sito-locale:porta --wp-path /percorso/ClassicPress/src
```

Il percorso dello script è relativo alla directory del tema. Screenshot e risultati vengono salvati nell’area artifacts dell’ambiente esterno, fuori dai repository. Il test server-fallback analizza HTML senza eseguirne gli script; non equivale a una verifica completa del Customizer con JavaScript disattivato. Gli annunci sono verificati come mutazioni DOM, non come parlato di VoiceOver.

## Licenza

Il codice del tema è GPL-3.0-or-later, come indicato in `LICENSE`. I font inclusi mantengono la propria licenza SIL OFL 1.1, disponibile nelle rispettive directory.
