# Configurazione

Materiale tecnico separato dal README; valori verificati nelle definizioni correnti di `inc/settings.php` e `inc/customizer.php`. Per i confini dell'integrazione e l'editor vedere [Architettura](architecture.md); per gli avvisi vedere [Accessibilità](accessibility.md).

## Impostazioni globali

Le sezioni Colors, Typography, Widths and layout e Header utilizzano `theme_mod`. Identità del sito conserva i controlli nativi e le due opzioni di visibilità del tema. Registrazione: `githeme_customize_register()`; predefiniti: `githeme_defaults()`.

| Impostazione | Predefinito | Valori consentiti |
|---|---|---|
| Primario | `#14569a` | Colore esadecimale |
| Secondario | `#4b5563` | Colore esadecimale |
| Testo | `#202833` | Colore esadecimale |
| Sfondo | `#ffffff` | Colore esadecimale |
| Link | `#14569a` | Colore esadecimale |
| Sfondo header | `#ffffff` | Colore esadecimale |
| Sfondo footer | `#ffffff` | Colore esadecimale |
| Mostra titolo | Visibile | Booleano; sempre visibile senza logo |
| Mostra motto | Nascosto sulle nuove attivazioni | Booleano indipendente dal logo |
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

## Font ed editor classico

I font WOFF2 sono locali e non modificati, con licenze SIL OFL 1.1 e provenienza documentata in [assets/fonts/SOURCES.md](../assets/fonts/SOURCES.md). Il tema dichiara solo le due varianti variabili, normale e corsiva, della famiglia selezionata: il browser scarica i file quando il contenuto li usa. Nessun preload forzato e nessun font caricato dal tema con lo stack di sistema. I plugin possono avere impostazioni font proprie, indipendenti dal tema.

L'editor classico riceve famiglia, dimensione, scala, colori e larghezza tramite `tiny_mce_before_init` / `teeny_mce_before_init` e il foglio editor locale. Eventuali stili inline nei contenuti o impostazioni dei plugin possono prevalere.

## Header, footer e identità

Colors include sfondi indipendenti per header e footer, entrambi bianchi per impostazione
predefinita (`githeme_color_header_background`, `githeme_color_footer_background`).
Sono theme_mod validati come gli altri colori e diventano `--color-header-background`
e `--color-footer-background`; il footer non usa più la superficie derivata dal secondario.
La superficie derivata resta disponibile per hover e altri elementi. Testo e link
continuano a usare la palette globale: il pannello informativo calcola separatamente
anche i loro contrasti su header e footer, senza bloccare il salvataggio.

In Site Identity, «Show site title» e «Show tagline» sono indipendenti. Il titolo è
visibile per default ed è sempre mostrato quando non c’è un logo; il motto è nascosto
per default sulle nuove attivazioni. Una configurazione esistente con motto valorizzato
mantiene il motto visibile: la sua scelta viene inizializzata una sola volta nelle
impostazioni del tema durante l’amministrazione/attivazione, senza riscrivere blogname
o blogdescription. Per nasconderlo occorre togliere la spunta e pubblicare; salvare un
altro controllo non lo nasconde. Il valore esplicito salvato ha sempre precedenza.
Un motto vuoto non produce un contenitore vuoto.

Il flag del motto viene inizializzato da `githeme_initialize_identity_visibility()` su `admin_init` e `after_switch_theme`; `githeme_initial_tagline_visibility()` distingue la nuova attivazione dalla configurazione preesistente. `githeme_identity_visible()` applica il fallback di lettura senza modificare titolo o motto.

## Configurazione essenziale

1. Attivare githeme da Aspetto → Temi.
2. Assegnare il menu alla posizione “Primary menu” e configurare eventualmente il logo in Identità del sito.
3. Per una homepage statica scegliere una normale pagina nelle impostazioni di lettura.
4. L'area “Footer — experimental” è facoltativa e configurabile tramite le normali API widget.

## Homepage statica e widget

1. Creare o scegliere una pagina pubblicata, con i contenuti nell’editor classico o, facoltativamente, con FX Builder.
2. In Impostazioni → Lettura selezionare una pagina iniziale statica e assegnare quella pagina; scegliere eventualmente una pagina distinta per gli articoli.
3. In Aspetto → Widget, oppure nelle aree widget del Customizer, aggiungere widget a **Homepage Hero** e/o **Homepage Content**.

L’ordine è header, Homepage Hero, contenuto della pagina, Homepage Content, footer. Le due aree sono indipendenti e opzionali: senza widget non producono contenitori vuoti. La homepage continua a mostrare il normale contenuto della pagina, con il suo titolo. Usare titoli di livello 2 per i widget e una gerarchia coerente nei loro contenuti.

Hero dispone dell’intera larghezza della viewport; il widget decide il proprio layout interno. Homepage Content rispetta la larghezza massima del layout configurata nel tema. Colori, tipografia e larghezze continuano a usare le impostazioni globali. Contenuti di terze parti possono richiedere propri accorgimenti responsive.

Gli ID stabili delle aree sono `homepage-hero` e `homepage-content`. Funzionano tramite `register_sidebar()` e `dynamic_sidebar()`, senza API specifiche dei plugin. Non appaiono nella homepage con gli ultimi articoli, nella pagina separata degli articoli, nelle pagine interne o negli articoli singoli.

Non viene aggiunto `front-page.php`: restano valide la gerarchia nativa e i template assegnati alle pagine che utilizzano header e footer standard del tema. Template esterni che sostituiscono completamente header/footer devono gestire autonomamente il rendering. Non sono introdotti ordinamenti proprietari, nuove opzioni Customizer o sistemi di sezioni.
