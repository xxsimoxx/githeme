# Sviluppo e verifiche

Materiale tecnico del checkout completo; gli strumenti di test non sono dipendenze del tema in produzione. Le istruzioni operative per Codex restano in [AGENTS.md](../AGENTS.md).

## Ambiente e compatibilità

I requisiti minimi dichiarati sono ClassicPress 2.7 e PHP 8.2. Il manutentore ha accettato ClassicPress 2.7 dopo una verifica manuale dei controlli Customizer, distinta dai test automatici. I test funzionali automatizzati su 2.7.0 non sono stati completati per indisponibilità del database isolato; non è dichiarata una matrice completa di compatibilità.

Ambiente della regressione di riferimento: PHP 8.2.13 e ClassicPress `2.7.4+dev`, branch `fix/customizer-regressions` derivato da `develop`, SHA `79193cbb98bb4bd4a286cc37cba1a221940396f0`, con riscrittura Customizer destinata a 2.8. Sono dati del contesto verificato, non requisiti di installazione del tema o garanzia per ogni build di quel branch. MAMP Pro è stato usato per l'esecuzione locale; non è richiesto dal tema.

Per i comandi che seguono, la radice di lavoro è un checkout ClassicPress con sorgenti in `src/` e tema in `src/wp-content/themes/githeme/`, salvo diversa indicazione. Adattare `--path` e il percorso del tema a un'altra struttura.

## Checkout, ZIP e controlli del progetto

Lo ZIP installabile generato dal workflow di release contiene il tema e le licenze dei font. Esclude `tests/`, `docs/` e `.github/` tramite `.gitattributes`.

Per eseguire i test utilizzare un checkout completo del [repository di sviluppo](https://github.com/xxsimoxx/githeme), che include gli script PHP, JavaScript e Selenium. I comandi di verifica descritti qui richiedono quel checkout e gli strumenti di sviluppo indicati; non sono eseguibili dal solo ZIP installabile. Questi strumenti non sono dipendenze del tema in produzione.

Lo ZIP usa `git archive` nel workflow `.github/workflows/zip.yml`, attivato alla pubblicazione di una release. Le esclusioni effettive sono in `.gitattributes`, compresi `AGENTS.md`, `docs/` e i file operativi elencati. Il README, lo screenshot, i componenti runtime e le licenze dei font rimangono inclusi. I riferimenti ai test in questi documenti sono destinati al checkout completo, non al contenuto ridotto dello ZIP. Non sono state modificate regole di packaging o workflow.

Il workflow `.github/workflows/cpcs.yml` esegue i ClassicPress Directory Coding Standards su push/PR ed esclude `tests/`. Non equivale all'esecuzione delle suite funzionali seguenti. Non installare dipendenze automaticamente per eseguire i controlli.

## Test browser: prerequisiti e sicurezza

Selenium/Firefox e WebDriver BiDi devono essere già configurati in un ambiente separato. Prima dell'uso leggere README/AGENTS di quell'ambiente; definire `BROWSER_TOOLS` con il suo percorso effettivo e `TEST_URL` con l'URL HTTPS locale autorizzato. Il suo `env.sh` deve definire `CODEX_BROWSER_ROOT` e `TMPDIR` coerenti con i controlli degli script. Non utilizzare profili personali, non registrare credenziali o cookie. Il launcher anonimo non deve essere usato per aggirare i controlli delle sessioni autenticate.

Gli script attuali contengono vincoli espliciti a un volume esterno e a un ambiente macOS dedicato: non sono runner portabili senza verifica. `navigation-readonly-browser.py` contiene anche URL e risoluzione loopback fissati nel sorgente; non accetta `--url`. Il suo comando seguente documenta la procedura esistente, non una promessa di esecuzione su host arbitrari. Conservare i dettagli della singola installazione fuori dalla documentazione generale.

I test che scrivono opzioni o menu richiedono autorizzazione esplicita, snapshot completi di esistenza, valori, tipi, chiavi e autoload, pulizia indipendente e verifica finale tramite nuovo processo WP-CLI. Non mettere operazioni necessarie dentro `assert`: Python ottimizzato deve mantenere test e ripristino operativi. Non creare contenuti permanenti o eliminare contenuti preesistenti per preparare fixture. Screenshot, log e snapshot rimangono fuori dai repository.

## Test delle impostazioni

Con ClassicPress caricato e PHP 8.2, dalla radice del progetto:

```sh
wp --path=src eval-file src/wp-content/themes/githeme/tests/global-settings.php
```

Il test usa le API reali e valori sovrascritti soltanto in memoria: non salva impostazioni e non crea contenuti. Verifica valori limite, ordine delle larghezze, input invalidi, avvisi non bloccanti, font selezionati, CSS dell'editor e classi header. La verifica di anteprima/pubblicazione del Customizer e delle richieste font effettive usa separatamente un browser autenticato.

Accessibilità WCAG 2.2 AA, prestazioni e SEO tecnico sono obiettivi di sviluppo, non certificazioni della versione iniziale.

## Test della homepage

Dalla radice ClassicPress:

```sh
wp --path=src eval-file src/wp-content/themes/githeme/tests/homepage-widgets.php
wp --path=src --skip-plugins eval-file src/wp-content/themes/githeme/tests/homepage-widgets.php
```

Il test PHP non scrive nel database: verifica registrazione, aree vuote/popolate e contesti ammessi, comprese callback widget senza output.

Il test browser richiede l’ambiente Selenium esterno già disponibile e autorizzazione alle modifiche temporanee delle sole opzioni elencate nello script. Utilizza pagine/articoli di prova **già pubblicati**, senza modificarne il contenuto. Prima dell’esecuzione impostare le variabili degli ID su contenuti pubblicati già esistenti nel sito di test:

```sh
. "$BROWSER_TOOLS/env.sh"
"$CODEX_BROWSER_ROOT/venv/bin/python" src/wp-content/themes/githeme/tests/homepage-widgets-browser.py \
  --url "$TEST_URL" --wp-path src \
  --front-page-id "$FRONT_PAGE_ID" --posts-page-id "$POSTS_PAGE_ID" \
  --internal-page-id "$INTERNAL_PAGE_ID" --post-id "$POST_ID"
```

Gli argomenti `--fx-content-id` e `--fx-page-id` sono facoltativi e si riferiscono ai fixture locali con i marcatori `githeme-test-*`; ometterli dove non disponibili. Il test usa esplicitamente il profilo Firefox dedicato, esegue screenshot e osservazioni BiDi senza registrare credenziali. Salva snapshot privati delle opzioni nell’area artifacts dell’ambiente esterno e ripristina valori, tipi, assenza e autoload, verificandoli anche in un nuovo processo WP-CLI. Controlla inoltre che i contenuti dei fixture e l’attivazione dei plugin rimangano invariati. Le viewport headless strette verificano il responsive, non emulano completamente uno smartphone.

## Test del contrasto

Dalla radice ClassicPress, con WP-CLI, PHP e Node già disponibili:

```sh
wp --path=src eval-file src/wp-content/themes/githeme/tests/contrast.php
node src/wp-content/themes/githeme/tests/contrast.js
```

I test coprono coppie identiche, bianco/nero, soglie, valori intermedi, input invalidi, foreground automatico, markup PHP di fallback e parità tra i linguaggi. Non scrivono nel database.

Il test browser richiede Selenium già installato, un ambiente esterno con `CODEX_BROWSER_ROOT`/`TMPDIR` configurati e una sessione autorizzata nel profilo dedicato. Non usa il launcher anonimo e non raccoglie credenziali. Eseguire solo con autorizzazione a modifiche temporanee dei theme_mod, poiché verifica anche la pubblicazione; conserva snapshot completi dei theme_mod e dei transient Site Health interessati, elimina i propri changeset temporanei e verifica il ripristino in un nuovo processo WP-CLI:

```sh
"$CODEX_BROWSER_ROOT/venv/bin/python" tests/customizer-contrast-browser.py --url https://sito-locale:porta --wp-path /percorso/ClassicPress/src
```

Il percorso dello script è relativo alla directory del tema. Screenshot e risultati vengono salvati nell’area artifacts dell’ambiente esterno, fuori dai repository. Il test server-fallback analizza HTML senza eseguirne gli script; non equivale a una verifica completa del Customizer con JavaScript disattivato. Gli annunci sono verificati come mutazioni DOM, non come parlato di VoiceOver.

## Test della navigazione

Il test browser richiede Selenium già disponibile, il profilo dedicato e autorizzazione alle modifiche temporanee dei menu:

```sh
. "$BROWSER_TOOLS/env.sh"
"$CODEX_BROWSER_ROOT/venv/bin/python" src/wp-content/themes/githeme/tests/navigation-browser.py \
  --url "$TEST_URL" --wp-path src
```

Crea due menu temporanei usando pagine pubblicate esistenti, senza modificarle. Verifica menu assente, semplice e annidato, etichette lunghe, entrambi gli header, mouse, Tab/Shift+Tab, Enter/Space, Escape, focus al cambio di larghezza e viewport strette. A viewport costante prova variazioni di logo, contenitore, disposizione, famiglia tipografica e caricamento tardivo di un font locale; campiona il layout su più frame per verificare stabilità e ritorno alla modalità orizzontale. Queste variazioni avvengono soltanto nel DOM e vengono eliminate ricaricando la pagina. La prova senza JavaScript usa una preferenza del solo profilo dedicato; al termine ripristina e verifica la preferenza JavaScript originale del profilo. Rimuove esclusivamente i menu creati dal test e ripristina le opzioni originali, verificando anche tipi, assenza e autoload in un nuovo processo WP-CLI. Screenshot, snapshot e risultati restano negli artifact dell’ambiente esterno. L’opzione `--baseline` registra il comportamento precedente senza richiedere il collasso aggiuntivo a 1024/820 px.

Sono test di viewport e tastiera in Firefox desktop, non prove su smartphone reali o certificazioni di accessibilità; resta necessaria la verifica con screen reader.

## Verifica della navigazione senza scritture al sito

`tests/navigation-readonly-browser.py` verifica il menu realmente assegnato a 1440, 1280,
768, 390 e 320 CSS px con mouse, Tab/Shift+Tab, Escape, Enter/Space e controllo del focus.
Menu breve, piatto, annidato, troppo lungo e assente sono fixture in un iframe isolato,
con lo stesso CSS/JavaScript: non vengono cambiati menu, contenuti o assegnazioni nel DB.
Sono verificati anche fallback senza script, variazioni dello spazio senza resize e
stabilità degli osservatori. Le fixture non sostituiscono una verifica autenticata delle
schermate di assegnazione menu. Profili anonimi temporanei e risultati rimangono nell’ambiente esterno;
nessuna configurazione degli strumenti viene modificata.

```sh
. "$BROWSER_TOOLS/env.sh"
"$CODEX_BROWSER_ROOT/venv/bin/python" src/wp-content/themes/githeme/tests/navigation-readonly-browser.py
```

Usare questo test quando non è autorizzata alcuna modifica al database; il precedente
`navigation-browser.py` crea invece fixture native e richiede autorizzazione esplicita.

## Altri controlli mirati

```sh
wp --path=src eval-file src/wp-content/themes/githeme/tests/header-surfaces.php
wp --path=src eval-file src/wp-content/themes/githeme/tests/fx-shortcodes.php
wp --path=src --skip-plugins eval-file src/wp-content/themes/githeme/tests/fx-shortcodes.php
```

Il primo copre le otto combinazioni logo/titolo/motto, sfondi e controlli con override in memoria. Il test FX verifica dipendenza opzionale e contrasto senza salvare opzioni. Usare anche lint PHP 8.2, `node --check` per gli script JavaScript, parsing/sintassi Python senza artefatti nel repository e `git diff --check`. Non dichiarare superato un controllo non eseguito.

Per la regressione frontend includere homepage, pagina e articolo, cinque componenti FX, viewport 1440/1280/768/390/320, assenza di overflow, tastiera, focus, menu senza JS, console/rete e nuovi errori PHP. Il test del solo contrasto non copre tutti i controlli del Customizer: verificare separatamente anteprima/pubblicazione/persistenza di font, larghezze, header e identità. Le verifiche manuali residue sono in [Accessibilità](accessibility.md).

## Verifiche mirate introdotte in 0.5.0

Le suite PHP `tests/gallery-slider.php`, `tests/gallery-widget.php`, `tests/featured-posts.php`, `tests/category-archives.php`, `tests/footer.php` e `tests/page-title-integration.php` si eseguono con `wp eval-file` nel checkout ClassicPress. Usano letture e fixture in memoria; richiedono contenuti locali esistenti secondo gli script. `tests/page-title.php` è invece un test isolato eseguibile direttamente con PHP.

Le corrispondenti verifiche browser e quelle per tipografia e `githeme-wide` usano Firefox/Selenium già disponibili e gli artifact esterni. Le fixture DOM non equivalgono all'aggiunta e al salvataggio di un widget in amministrazione. La configurazione/persistenza di Featured Posts è stata confermata manualmente dal manutentore; per Gallery Slider, oltre alla resa visiva e alle istanze indipendenti, il 13 novembre 2026 è stato verificato il ciclo amministrativo reale con Firefox/Selenium: modifica di un widget esistente, impostazione di un titolo e tre ID immagine validi, salvataggio e ricaricamento della pagina amministrativa. Titolo e ordine degli ID sono rimasti invariati; sul frontend sono stati verificati titolo, caricamento e ordine delle immagini e pulsanti precedente/successiva. La configurazione originale del widget e le associazioni alle aree sono state ripristinate esattamente e verificate in un nuovo processo WP-CLI. Questa verifica non equivale a una prova manuale del manutentore.

## Compatibilità del Customizer

La doppia registrazione dei default di `develop` poteva cancellare la descrizione Colors. Il branch locale ClassicPress `fix/customizer-regressions` contiene la correzione esaminata separatamente; il tema non modifica il core.

La riscrittura JavaScript conserva un proxy incompleto: nel ramo esaminato `wp.customize(id, callback)` non è invocabile e le sottoscrizioni Value si perdono dopo modifiche tramite UI. Riproduzione minima e confini dell’integrazione: [riproduzione nel checkout di sviluppo](../tests/customizer-api-regression.md). L’informazione dinamica del tema usa eventi DOM standard sui propri input, non sostituisce l’API mancante. Modifiche programmatiche di terze parti che non emettono eventi non sono osservabili in modo affidabile finché la regressione pubblica del core non sarà risolta.

Queste osservazioni sono riferite al core esaminato: non costituiscono un nuovo audit di versioni successive. Cercare alternative attraverso API pubbliche, senza patch al core o workaround su dettagli interni; non aprire automaticamente issue/PR.

## Verifiche delle integrazioni facoltative

Controllare CSS e formattazione FX Builder, parser FX Shortcodes nei diversi contesti e aggiornamento dei widget nel Customizer riscritto. La regressione di riferimento non sostituisce ogni combinazione dei plugin. FX Builder Widgets può esporre pubblicamente il proprio tipo di contenuto e archivio: verificarne l’uso e la pubblicazione nel sito di destinazione, senza introdurre dipendenze nel tema.

## Criteri per i contributori

Preservare API native, escaping contestuale e validazione; niente dipendenze obbligatorie o personalizzazioni per singoli siti. Correzioni circoscritte e test pertinenti, senza refactoring soltanto estetici. Non cambiare ambiente, plugin, dati o workflow per far passare un test senza autorizzazione. I limiti del core o degli strumenti devono essere distinti dai difetti del tema e conservati nei rapporti.
