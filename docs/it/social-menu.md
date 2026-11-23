# Menu social di GiTheme

GiTheme mette a disposizione una posizione di menu facoltativa, denominata `social`, visualizzata in una riga dedicata del footer tramite `githeme_get_social_links_menu()`.

Il menu utilizza il normale walker di ClassicPress: ordine delle voci, gerarchia, URL, destinazioni e attributi dei collegamenti rimangono quelli nativi. Ai collegamenti riconosciuti viene associata un'icona SVG e un'etichetta accessibile agli screen reader; i collegamenti non riconosciuti mantengono il testo visibile. Nel menu social i collegamenti non sono sottolineati, ma restano visibili i bordi al passaggio del puntatore e gli indicatori di focus da tastiera. Sul frontend non è richiesto JavaScript.

## Personalizzare le icone con `githeme_social_links_icons`

Il filtro `githeme_social_links_icons` riceve e restituisce un array associativo di regole per il riconoscimento dei servizi. Le regole vengono applicate all'URL originale della voce di menu, prima della resa del titolo: il filtro non analizza l'HTML generato e non effettua richieste di rete o ricerche dei servizi.

| Campo | Valore ammesso | Comportamento |
| --- | --- | --- |
| Identificatore del servizio | Chiave associativa, per esempio `community` | Permette di aggiungere, modificare o rimuovere una regola. |
| `hosts` | Array di nomi host esatti, minuscoli, in ASCII/punycode | Per URL HTTP/HTTPS, anche senza schema (`//`). Omettere `www.`: l'host viene normalizzato eliminando il `www.` iniziale e l'eventuale punto finale valido. I sottodomini vanno indicati esplicitamente. |
| `path_prefix` | Stringa facoltativa non vuota, per esempio `/community` | Confronto sensibile alle maiuscole: il percorso deve coincidere con il prefisso oppure proseguire con `/`. Query string e frammenti non determinano il servizio. |
| `icon` | Nome di file SVG locale senza estensione, conforme a `[a-z0-9-]+` | Il file viene cercato in `assets/icons/social/` tramite `get_theme_file_path()`; ha precedenza l'eventuale risorsa del child theme. Non sono ammessi URL né attraversamenti di directory. |
| `scheme` | `mailto` oppure `tel`, in alternativa a `hosts` | Riconosce un singolo destinatario email valido o un URI telefonico numerico; non è un sistema generico per schemi arbitrari. |

Le regole vengono valutate nell'ordine dell'array: **vince la prima regola valida corrispondente**. Per cambiare un servizio già presente, modificarne la regola anziché aggiungerne una concorrente in fondo all'array.

Se un URL non è riconosciuto o il relativo SVG manca o non è utilizzabile, rimane visibile l'etichetta originale. Gli URL con informazioni utente (`user:password@host`) non vengono associati a icone. Il riconoscimento non modifica mai l'URL del collegamento.

Per i collegamenti telefonici sono supportati numeri internazionali e locali, separatori grafici e parametri come `;ext=42` e `;phone-context=example.test`.

### Esempio: un'istanza Mastodon e un servizio personalizzato

Inserire il codice nel `functions.php` di un child theme o in un'altra estensione PHP locale appropriata:

```php
add_filter( 'githeme_social_links_icons', 'example_child_social_icons' );

function example_child_social_icons( $icons ) {
    $icons['mastodon']['hosts'][] = 'social.example.org';

    $icons['community'] = array(
        'hosts'       => array( 'community.example.org' ),
        'path_prefix' => '/members',
        'icon'        => 'community',
    );

    return $icons;
}
```

Con queste regole, `https://social.example.org/@team` usa l'icona Mastodon, mentre `https://community.example.org/members/team` usa `community.svg`. Il percorso `/members-other` non corrisponde al prefisso `/members`. Sostituire i domini d'esempio con quelli effettivi.

## SVG personalizzati nei child theme

Per il servizio `community` dell'esempio, salvare il file in:

```text
your-child-theme/assets/icons/social/community.svg
```

L'SVG deve contenere un `viewBox` valido e tracciati `<path d="…">` già appiattiti. Il renderer sanitizza il markup SVG e dei tracciati e impone `currentColor`, dimensioni intrinseche fisse, `aria-hidden="true"` e `focusable="false"`.

Non sono supportati riferimenti esterni, script, gestori di eventi, stili, immagini, testo o trasformazioni. Evitare trasformazioni di gruppo e riempimenti multicolore: convertire preventivamente la grafica in tracciati compatibili. Il nome accessibile del collegamento deriva dall'etichetta della voce di menu, non dal titolo dell'SVG.

Conservare licenze e attribuzioni delle risorse originali. Le icone incluse nel tema provengono da Font Awesome Free 7.1.0; vedere [provenienza e licenze delle icone](../../assets/icons/social/README.md). Anche `phone.svg` segue le convenzioni delle altre icone solide.

## Integrazione con il Customizer

### Aggiornamento dei menu

GiTheme si appoggia al **Selective Refresh nativo di ClassicPress** per aggiornare i menu già presenti nell'anteprima, senza registrare partial, impostazioni o listener JavaScript aggiuntivi del tema.

La funzione che genera il menu social usa `wp_nav_menu()` con `echo => true` all'interno di un buffer di output e restituisce l'HTML raccolto. Questo permette al core di riconoscere il menu come idoneo al proprio meccanismo di aggiornamento parziale.

L'assegnazione iniziale o la rimozione di un menu, così come un footer inizialmente vuoto, possono richiedere un aggiornamento completo dell'anteprima perché non esiste ancora un elemento da sostituire. GiTheme non inserisce segnaposto nascosti o righe vuote nel footer per aggirare questo comportamento.

### Anteprima dei colori

Le impostazioni dei colori di GiTheme sono registrate in `githeme_customize_register()` (`inc/customizer.php`) con `transport => 'refresh'`, come le altre impostazioni globali di presentazione.

I colori dei collegamenti e del focus del menu social vengono ricavati in `githeme_custom_properties_css()` dai colori di collegamenti, primario e footer. Dopo un aggiornamento completo riuscito dell'anteprima, i colori vengono ricalcolati. Il tema non implementa una palette JavaScript separata né un aggiornamento CSS istantaneo.

## Verifiche e test

I test pertinenti alla funzione sono distribuiti tra:

- `tests/social-menu.php`: riconoscimento degli URL, collegamenti telefonici, accessibilità, footer vuoto, rendering del menu e interazione con i filtri del Customizer;
- `tests/social-menu-browser.py`: comportamento visivo del footer, adattamento responsive, decorazione dei collegamenti, hover e focus da tastiera.

Le verifiche dei difetti interni del Customizer di ClassicPress e la relativa cronologia diagnostica non fanno parte della documentazione funzionale del menu social. Per il contesto delle correzioni al core, vedere le PR [#2826](https://github.com/ClassicPress/ClassicPress/pull/2826), [#2827](https://github.com/ClassicPress/ClassicPress/pull/2827) e [#2828](https://github.com/ClassicPress/ClassicPress/pull/2828).
