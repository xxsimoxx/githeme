# Architettura

Tema classico PHP per ClassicPress, senza framework, build obbligatoria, Gutenberg o dipendenze obbligatorie da plugin. I contenuti appartengono alle pagine e agli articoli; le opzioni globali di presentazione al Customizer. Non sono presenti page builder interni, ordinamenti proprietari delle sezioni o varianti specifiche per singoli siti.

## Organizzazione e rendering

| Percorso | Responsabilità |
|---|---|
| `functions.php` | Carica impostazioni, setup, Customizer, gallerie, categorie, controllo del titolo e widget. |
| `inc/setup.php` | Supporti del tema, menu, asset e registrazione delle aree widget. |
| `inc/settings.php` | Valori validati, contrasto, font, proprietà CSS ed editor classico. |
| `inc/customizer.php` | Registrazione, validazione, avvisi e asset informativi. |
| `inc/class-githeme-*-control.php` | Controlli Customizer con markup proprio e binding pubblico. |
| `inc/gallery.php`, `assets/js/gallery-slider.js` | Wrapper opzionale della galleria nativa e navigazione progressiva. |
| `inc/category.php`, `category.php` | Query principale delle categorie e griglia dedicata. |
| `template-parts/content-category-card.php` | Card condivise fra archivi e Featured Posts. |
| `inc/page-title.php` | Meta box e preferenza del titolo delle sole pagine. |
| `inc/class-githeme-*-widget.php` | Widget nativi Featured Posts e Gallery Slider. |
| `header.php`, `footer.php` | Header/footer condivisi e inserimento condizionale delle aree homepage. |
| `page.php`, `single.php` | Rendering dei contenuti singoli tramite `template-parts/content-singular.php`. |
| `index.php`, `404.php`, `comments.php` | Elenchi, archivi/ricerca, pagina mancante e commenti. |
| `template-parts/homepage-widgets.php` | Rendering riutilizzato delle aree homepage attive, senza contenitori vuoti. |
| `style.css`, `assets/` | CSS, script vanilla e font locali. |
| `tests/` | Verifiche del checkout di sviluppo. |

Non esistono `front-page.php` o `home.php`: resta valida la gerarchia nativa. La homepage statica mostra il normale contenuto della pagina e, facoltativamente, le aree descritte in [Configurazione](configuration.md). Una pagina creata con un plugin facoltativo resta possibile senza rendere quel plugin necessario al tema.

## CSS e variabili

`githeme_custom_properties_css()` genera proprietà da valori validati, senza utilizzare stringhe CSS arbitrarie provenienti dai controlli. `githeme_rendered_widths()` applica limiti difensivi senza riscrivere valori salvati. CSS Grid, Flexbox e dimensioni relative mantengono il layout responsive.

| Variabili | Origine |
|---|---|
| `--color-primary`, `--color-secondary`, `--color-text`, `--color-background`, `--color-link` | Palette del Customizer. |
| `--color-header-background`, `--color-footer-background` | Sfondi indipendenti del Customizer. |
| `--color-button-text`, `--color-button-hover-text` | Bianco/nero a contrasto migliore su primario e secondario. |
| `--color-surface`, `--color-muted`, `--color-border` | Varianti calcolate dalla palette, senza seconda palette autonoma. |
| `--font-body`, `--font-size-base`, `--heading-scale`, `--heading-1` … `--heading-6` | Font e scala selezionati. |
| `--width-content`, `--width-wide`, `--width-layout` | Larghezze validate e limitate per il rendering. |
| `--logo-max-height` | Altezza massima configurata del logo. |

La superficie derivata usa secondario e sfondo (6%/94%). Il footer utilizza invece il proprio colore indipendente. Il testo attenuato usa una miscela testo/sfondo e torna al testo originale se la miscela non raggiunge la soglia normale; ciò non corregge una palette originale insufficiente.

## Asset ed editor

`githeme_enqueue_assets()` usa le API native. CSS frontend, navigazione, foglio dell'editor classico e integrazione FX usano la versione di `style.css` per la cache; gli asset informativi del Customizer usano `filemtime()`. Anche lo script dello slider usa la versione del tema ed è accodato solo dal rendering di una galleria effettivamente migliorata, senza duplicazioni fra shortcode e widget.

`githeme_editor_settings()` aggiunge font e proprietà a `content_style` tramite `tiny_mce_before_init` e `teeny_mce_before_init`, conservando l'eventuale stile precedente. Le virgolette doppie del solo CSS generato vengono sostituite con singole prima dell'aggiunta, per evitare l'errore di inizializzazione TinyMCE con famiglie come “Segoe UI”. Il foglio `assets/css/editor.css` non carica il layout del frontend nell'editor.

## Navigazione e progressive enhancement

Il menu conserva un unico elenco nel DOM, il pulsante nativo con `aria-expanded` e `aria-controls`, e i sottomenu disponibili con mouse e tastiera. Su desktop i pannelli sono fuori dal flusso: soltanto le voci principali determinano lo spazio necessario, non la larghezza dei sottomenu aperti. Escape chiude anche un pannello desktop e riporta il focus al collegamento genitore quando proviene dal pannello. I livelli ulteriori restano annidati nel pannello, senza flyout fuori schermo. L’indicatore passa da hamburger a chiusura senza modificare il nome accessibile “Menu”. Escape chiude la navigazione compatta e riporta il focus al pulsante. Il layout centrato con menu sotto considera disponibile l’intera riga; quello in linea considera anche lo spazio dell’identità del sito. Senza JavaScript il menu può andare a capo e tutti i collegamenti restano utilizzabili.

I ricalcoli sono raggruppati tramite `requestAnimationFrame`: `ResizeObserver` osserva header, identità e menu, mentre le variazioni delle classi di layout e delle variabili inline vengono rilevate separatamente. Il completamento del caricamento dei font locali richiede un nuovo controllo anche dopo il rendering iniziale. Non vengono osservati gli attributi che lo script stesso modifica nel menu.

## Controlli e confini del Customizer

API pubbliche PHP, controlli standard ove possibile, una impostazione per controllo, sanitizzazione e validazione. L'anteprima usa `refresh`; non viene implementato selective refresh. L'interfaccia informativa del tema ascolta eventi DOM standard sui propri input; non dipende da Backbone, dal proxy JavaScript incompleto o dal DOM interno del core. Vedere [Accessibilità](accessibility.md) e [Sviluppo](development.md).

Le checkbox usano WP_Customize_Control, il contenitore nativo
`customize-inside-control-row`, etichette for/id e descrizioni aria-describedby; il
valore HTML resta 1 anche da disattivate. Nessun override CSS o API JavaScript interna.
Il test mirato `tests/header-surfaces.php` usa solo override in memoria per le otto
combinazioni logo/titolo/motto e la validazione delle nuove impostazioni.

## Plugin facoltativi

Il tema usa `the_content()` e le normali API widget; funziona senza FX Builder, FX Shortcodes e FX Builder Widgets. Non richiama direttamente le loro API. I contenuti creati con un plugin possono comunque dipendere dal plugin per il rendering.

La sola integrazione grafica dedicata riguarda i cinque componenti descritti in [FX Shortcodes](fx-shortcodes.md). Group, FX Builder e FX Builder Widgets non hanno integrazioni grafiche dedicate nel tema.

## Licenze

Il codice è GPL-3.0-or-later, come indicato in [LICENSE](../LICENSE). I font mantengono SIL OFL 1.1, con licenze nelle rispettive directory e [provenienza documentata](../assets/fonts/SOURCES.md).

## Componenti condivisi di 0.5.0

Featured Posts usa lo stesso template e gli stessi stili delle categorie; soltanto query, ID e livello del titolo della card dipendono dal contesto. Gallery Slider invoca una volta il normale shortcode gallery, senza una seconda implementazione. Il filtro `shortcode_atts_gallery` fornisce `large` solo agli slider privi di `size`; `do_shortcode_tag` conserva l'HTML nativo e lo avvolge soltanto se riconoscibile. In assenza di DOM o con output incompatibile resta il rendering nativo.

La tipografia editoriale ha un blocco CSS condiviso fra frontend ed editor, con breakpoint a 48rem e valori derivati dalle variabili esistenti; titoli di widget e componenti mantengono le proprie regole. `githeme-wide` amplia solo i contenitori con righe Default esplicitamente abilitate e conserva la larghezza editoriale delle altre righe. Non vengono introdotte API JavaScript del Customizer o dipendenze dai plugin.
