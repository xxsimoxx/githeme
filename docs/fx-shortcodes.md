# Integrazione opzionale con FX Shortcodes

Il tema continua a funzionare senza il plugin. `githeme_enqueue_fx_shortcodes_style()` carica `assets/css/fx-shortcodes.css` soltanto quando il foglio `fx-shortcodes` è accodato; dipendenze `githeme-style` e `fx-shortcodes`, hook `wp_enqueue_scripts` a priorità 20. Nessuna nuova opzione Customizer e nessun richiamo delle API del plugin necessario al tema.

## Componenti supportati

| Componente | Integrazione |
|---|---|
| Button | Primario e `--color-button-text`; hover/focus-visible fill e outline sul secondario, con `--color-button-hover-text` calcolato per il contrasto. Text resta trasparente e conserva l'interazione del plugin. Dimensioni e varianti non vengono riscritte. |
| Card | Sfondo `--color-footer-background`, testo ereditato, bordo `--color-border`, angoli discreti e ombra derivata da `--color-text`. Immagini e proporzioni del plugin preservate. |
| Cover | Sfondo predefinito `--color-background`, testo ereditato e padding responsive. Struttura, immagine e overlay restano del plugin. Gli elementi annidati conservano le proprie regole. |
| Details | Sfondo `--color-background`, bordo `--color-border`, testo ereditato, hover/focus discreto da `currentColor`; comportamento nativo di apertura/chiusura. |
| Separator | Colore predefinito `--color-secondary`; dimensioni, allineamento e varianti del plugin restano disponibili. |

Group è organizzativo e non ha un'identità grafica dedicata. Nessuna integrazione grafica dedicata con FX Builder o FX Builder Widgets.

## Precedenza delle personalizzazioni

Gli attributi del renderer vengono applicati inline: colori, padding, margini, raggio e altre proprietà supportate prevalgono sul foglio del tema. Non si usa `!important`. Button espone `--fx-button-bg` e `--fx-button-color`: se una delle due è presente nel suo attributo `style`, il tema non applica la regola di hover/focus-visible sul secondario e conserva l'hover del plugin. Non vengono sovrascritti gli sfondi espliciti di Card, Cover o Details né il colore esplicito di Separator.

Il tema riutilizza `githeme_button_text_color()` su primario e secondario, scegliendo bianco o nero con contrasto migliore. Non ricalcola il testo per sfondi inline arbitrari. Le personalizzazioni esplicite e il testo sopra le immagini Cover richiedono controllo editoriale del contrasto. Lo spessore di Separator dipende dalle varianti: il renderer esaminato non espone un attributo separato per lo spessore.

## Accessibilità e verifica

Focus visibile, controlli Details nativi, nessuna dipendenza JavaScript aggiuntiva e rispetto del movimento ridotto. Questa integrazione non è una dichiarazione di conformità WCAG dei contenuti del plugin.

Il test [tests/fx-shortcodes.php](../tests/fx-shortcodes.php) verifica in memoria il caricamento condizionale, l'ordine/cache dei CSS e il contrasto automatico, anche quando i plugin vengono saltati. Le prove browser devono includere componenti predefiniti e personalizzati alle viewport indicate in [Sviluppo](development.md). Non modificare il plugin per adattare la presentazione del tema.

## Confine del rendering

FX Shortcodes non registra `[element]` come shortcode ordinario: `do_shortcode()` da solo non lo elabora. Il rendering appartiene al plugin, non al foglio di integrazione del tema. Il tema continua a usare `the_content()` e le normali API widget; i contenuti creati con un plugin possono dipendere da quel plugin per essere visualizzati.
