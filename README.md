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
- Area widget facoltativa `footer-experimental`, visibile prima dei crediti.
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

Il contrasto testo/sfondo e link/sfondo viene calcolato tramite `githeme_contrast_ratio()`, indipendente dall'interfaccia. Un rapporto inferiore a 4,5:1 produce consigli informativi nella sezione Colori e nella schermata Temi; non impedisce il salvataggio. Questi avvisi sono ricalcolati al caricamento delle schermate, non durante la modifica interattiva. Il testo dei pulsanti usa automaticamente bianco o nero secondo il contrasto migliore. Superfici, bordi e testi secondari sono derivati dalla palette.

I font WOFF2 sono locali e non modificati, con licenze SIL OFL 1.1 e provenienza documentata in `assets/fonts/SOURCES.md`. Il tema dichiara solo le due varianti variabili, normale e corsiva, della famiglia selezionata: il browser scarica i file quando il contenuto li usa. Nessun preload forzato e nessun font caricato dal tema con lo stack di sistema. I plugin possono avere impostazioni font proprie, indipendenti dal tema.

L'editor classico riceve famiglia, dimensione, scala, colori e larghezza tramite `tiny_mce_before_init` / `teeny_mce_before_init` e il foglio editor locale. Eventuali stili inline nei contenuti o impostazioni dei plugin possono prevalere.

## Test delle impostazioni

Con ClassicPress caricato e PHP 8.2, dalla radice del progetto:

```sh
wp eval-file src/wp-content/themes/githeme/tests/global-settings.php
```

Il test usa le API reali e valori sovrascritti soltanto in memoria: non salva impostazioni e non crea contenuti. Verifica valori limite, ordine delle larghezze, input invalidi, avvisi non bloccanti, font selezionati, CSS dell'editor e classi header. La verifica di anteprima/pubblicazione del Customizer e delle richieste font effettive richiede ancora un browser autenticato.

Accessibilità WCAG 2.2 AA, prestazioni e SEO tecnico sono obiettivi di sviluppo, non certificazioni della versione iniziale.

## Uso essenziale in MAMP Pro

1. Verificare il PHP assegnato al sito (riferimento: 8.2).
2. Attivare **githeme** da Aspetto → Temi.
3. Assegnare un menu alla posizione “Primary menu” e impostare eventualmente un logo dall'identità del sito.
4. Per una homepage statica scegliere una normale pagina nelle impostazioni di lettura. Non esiste `front-page.php`: la pagina usa il normale rendering e può essere costruita con FX Builder.
5. Provare l'area “Footer — experimental” da Aspetto → Widget e dal Customizer.

La homepage nativa a sezioni non è ancora implementata e resterà facoltativa. Le impostazioni globali di presentazione saranno separate dai contenuti editoriali delle pagine.

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

## Limiti noti della versione 0.2.0

Sul core `develop` esaminato, `wp-admin/customize.php` richiama nuovamente `register_controls()` dopo `customize_register`: la sezione core `colors` viene ricreata e perde la descrizione aggiunta dal tema, inclusi gli avvisi di contrasto. Il comportamento è stato riprodotto a livello PHP anche con una semplice descrizione statica; non dipende dal calcolo del contrasto o dall'escaping. Gli avvisi nella schermata Temi seguono un percorso separato.

Le descrizioni sono inoltre costruite al caricamento usando i valori disponibili in quella fase: non si aggiornano in tempo reale durante le modifiche. La versione 0.2.0 non include correzioni o workaround per questo problema. Il ciclo autenticato completo di anteprima e pubblicazione resta da verificare in un browser automatizzabile.

## Licenza

Il codice del tema è GPL-3.0-or-later, come indicato in `LICENSE`. I font inclusi mantengono la propria licenza SIL OFL 1.1, disponibile nelle rispettive directory.
