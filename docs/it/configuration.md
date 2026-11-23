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

## Proprietà CSS personalizzate pubbliche

GiTheme espone **24 proprietà CSS personalizzate pubbliche** per colori, tipografia e layout. Sono destinate a child theme, CSS personalizzato e integrazioni di terze parti. Nomi e significato costituiscono l'interfaccia CSS supportata dal tema; le proprietà specifiche dei componenti e quelle interne sono dettagli implementativi e possono cambiare tra le versioni.

`githeme_custom_properties_css()` genera i valori dalle impostazioni validate del tema e li dichiara su `:root`. Le proprietà sono disponibili anche nell'editor classico tramite `content_style`. Il Customizer resta la fonte delle impostazioni: è preferibile utilizzare queste proprietà anziché duplicare valori `theme_mod` o calcoli della palette.

| Proprietà | Valore e utilizzo previsto |
|---|---|
| `--color-primary` | Colore primario del Customizer; accenti e azioni principali. |
| `--color-secondary` | Colore secondario del Customizer; accenti secondari e stati hover. |
| `--color-text` | Colore globale del testo. |
| `--color-background` | Colore globale dello sfondo. |
| `--color-link` | Colore globale dei link. |
| `--color-header-background` | Colore indipendente dello sfondo dell'header. |
| `--color-footer-background` | Colore indipendente dello sfondo del footer. |
| `--color-surface` | Superficie tenue derivata dalla miscela 6% secondario e 94% sfondo. |
| `--color-muted` | Testo secondario derivato da testo e sfondo; torna al colore del testo se il contrasto è insufficiente. |
| `--color-border` | Colore dei bordi derivato da testo e sfondo. |
| `--color-button-text` | Testo bianco o nero scelto automaticamente sullo sfondo primario dei pulsanti. |
| `--color-button-hover-text` | Testo bianco o nero scelto automaticamente sullo sfondo secondario/hover dei pulsanti. |
| `--font-body` | Stack della famiglia tipografica selezionata, compresa l'opzione di sistema. |
| `--font-size-base` | Dimensione base configurata, espressa in `rem`. |
| `--heading-scale` | Rapporto della scala dei titoli, senza unità. |
| `--heading-1` … `--heading-6` | Sei **fattori di scala senza unità**, non dimensioni del font; `--heading-6` vale `1` e ogni livello precedente applica un ulteriore passo della scala. |
| `--width-content` | Larghezza massima dei contenuti editoriali in `rem`. |
| `--width-wide` | Larghezza massima dei contenuti estesi in `rem`. |
| `--width-layout` | Larghezza massima del layout complessivo in `rem`. |

Le larghezze sono massime e non fisse; dopo le protezioni applicate al rendering rispettano `contenuto ≤ estesa ≤ layout`. I fattori dei titoli devono essere combinati con una lunghezza, ad esempio `calc(var(--font-size-base) * var(--heading-3))`: usare soltanto `var(--heading-3)` come `font-size` non è valido.

Esempio per un componente personalizzato:

```css
.custom-card {
    max-width: var(--width-content);
    padding: 1rem;
    background: var(--color-surface);
    color: var(--color-text);
    border: 1px solid var(--color-border);
}

.custom-card h3 {
    font-family: var(--font-body);
    font-size: calc(var(--font-size-base) * var(--heading-3));
}
```

Le **proprietà generate specifiche dei componenti** sono disponibili ma *non* fanno parte di questa interfaccia pubblica generale: `--color-navigation-focus`, `--color-navigation-submenu-focus`, `--color-social-link`, `--color-social-focus`, `--color-header-muted` e `--logo-max-height`. Implementano componenti particolari del tema, anche con scelte di contrasto dipendenti dal contesto, e possono cambiare insieme ai componenti.

Le **proprietà interne** come `--submenu-offset`, `--with-sidebar`, `--space`, `--githeme-prose-h1` … `--githeme-prose-h3`, `--githeme-heading-after` e `--githeme-gallery-*` non sono punti di estensione supportati. La loro presenza nei fogli di stile non le rende un'API stabile. L'elenco pubblico non comprende le variabili dei plugin o dell'interfaccia di amministrazione di ClassicPress.

## Font ed editor classico

I font WOFF2 sono locali e non modificati, con licenze SIL OFL 1.1 e provenienza documentata in [assets/fonts/SOURCES.md](../../assets/fonts/SOURCES.md). Il tema dichiara solo le due varianti variabili, normale e corsiva, della famiglia selezionata: il browser scarica i file quando il contenuto li usa. Nessun preload forzato e nessun font caricato dal tema con lo stack di sistema. I plugin possono avere impostazioni font proprie, indipendenti dal tema.

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
4. L'area “Footer” è facoltativa e configurabile tramite le normali API widget; l'ID stabile resta `footer-experimental`. Senza output dei widget non viene generata una fascia vuota né vengono aggiunti crediti automatici.

## Menu Social

Oltre alla posizione «Primary menu», GiTheme registra la posizione facoltativa «Social». Assegnare un menu da **Aspetto → Menu** per mostrare i collegamenti nel footer. I servizi riconosciuti ricevono automaticamente un’icona SVG locale e un’etichetta accessibile; i collegamenti non riconosciuti conservano il testo originale. Il menu non richiede JavaScript sul frontend. Per i servizi supportati, il filtro di estensione e le icone personalizzate vedere [Menu Social](social-menu.md).

## Homepage statica e widget

1. Creare o scegliere una pagina pubblicata, con i contenuti nell’editor classico o, facoltativamente, con FX Builder.
2. In Impostazioni → Lettura selezionare una pagina iniziale statica e assegnare quella pagina; scegliere eventualmente una pagina distinta per gli articoli.
3. In Aspetto → Widget, oppure nelle aree widget del Customizer, aggiungere widget a **Homepage Hero** e/o **Homepage Content**.

L’ordine è header, Homepage Hero, contenuto della pagina, Homepage Content, footer. Le due aree sono indipendenti e opzionali: senza widget non producono contenitori vuoti. La homepage continua a mostrare il normale contenuto della pagina; il titolo del template è visibile per default e può essere nascosto con “Hide page title” nell’editor della singola pagina. Usare titoli di livello 2 per i widget e una gerarchia coerente nei loro contenuti.

Hero dispone dell’intera larghezza della viewport; il widget decide il proprio layout interno. Homepage Content rispetta la larghezza massima del layout configurata nel tema. Colori, tipografia e larghezze continuano a usare le impostazioni globali. Contenuti di terze parti possono richiedere propri accorgimenti responsive.

Gli ID stabili delle aree sono `homepage-hero` e `homepage-content`. Funzionano tramite `register_sidebar()` e `dynamic_sidebar()`, senza API specifiche dei plugin. Non appaiono nella homepage con gli ultimi articoli, nella pagina separata degli articoli, nelle pagine interne o negli articoli singoli.

Non viene aggiunto `front-page.php`: restano valide la gerarchia nativa e i template assegnati alle pagine che utilizzano header e footer standard del tema. Template esterni che sostituiscono completamente header/footer devono gestire autonomamente il rendering. Non sono introdotti ordinamenti proprietari, nuove opzioni Customizer o sistemi di sezioni.

## Widget, archivi e titolo delle pagine

Il [README](../../README.md) descrive i widget nativi GiTheme – Featured Posts e GiTheme – Gallery Slider, le modalità di selezione, gli archivi di categoria a 12 articoli per pagina e lo shortcode `[gallery layout="slider"]`. I widget riutilizzano card e gallerie esistenti, senza opzioni estetiche aggiuntive. Le righe Default di FX Builder possono usare `githeme-wide` per raggiungere `--width-layout`; non cambia la larghezza `--width-wide` né il rendering Full Width del plugin.

“Hide page title” usa il post meta `_githeme_hide_page_title` soltanto sulle pagine. Non altera titolo salvato, document title o heading del contenuto; autosave e revisioni non riscrivono la preferenza. La tipografia editoriale responsive e i margini condivisi con il Classic Editor rispettano la dimensione base e la scala configurate, senza cambiare i livelli semantici.
