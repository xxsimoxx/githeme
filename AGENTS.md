# Regole per githeme

## Ambito operativo

- Leggere liberamente core ClassicPress e plugin per verificare le API effettive.
- Creare e modificare file esclusivamente in `src/wp-content/themes/githeme/`, salvo autorizzazione esplicita.
- Non modificare core, plugin, configurazioni MAMP Pro o altri file esterni.
- Non eseguire commit, push, merge, checkout o altre operazioni Git che modificano lo stato senza autorizzazione.
- Non installare dipendenze o alterare l'ambiente senza conferma.
- Prima di modifiche significative, presentare un piano e attendere approvazione; l'autorizzazione esplicita a un ambito vale per il lavoro richiesto.
- Segnalare anomalie del core, soprattutto del Customizer, senza correggerle nel core né introdurre workaround silenziosi nel tema.
- Non delegare ad altri agenti senza richiesta esplicita.

## Architettura

- Tema classico PHP generalista, senza Gutenberg, framework, build obbligatoria o dipendenze da plugin.
- PHP 8.2 è il riferimento di sviluppo. La matrice minima ClassicPress/PHP non è ancora definita: non dichiararla senza accordo e verifiche.
- HTML semantico, CSS con custom properties, Grid/Flexbox e JavaScript vanilla progressivo.
- Obiettivo WCAG 2.2 AA, responsive, prestazioni e SEO tecnico; nessuna dichiarazione di conformità senza verifica.
- Nessun template, componente o impostazione legato a Gieffe, Postib o Dimark: sono casi d'uso, non architettura.
- La homepage nativa configurabile sarà facoltativa. Una normale pagina statica, anche con FX Builder, deve poter essere homepage.
- Non aggiungere `front-page.php` senza valutare la precedenza sui template assegnati alle pagine.
- Nessun page builder interno, sistema astratto di componenti o configurazione generica.
- Contenuti delle singole pagine nell'editor classico; impostazioni globali di presentazione nel Customizer tramite `theme_mod`.
- Usare soltanto API pubbliche; esaminare il Customizer del branch locale `develop` senza presumere compatibilità JavaScript storica.
- Controlli semplici, preferibilmente una sola impostazione per controllo, default espliciti e validazione/sanitizzazione appropriate.
- Le segnalazioni di contrasto sono informative e non impediscono il salvataggio. Il calcolo deve restare riutilizzabile e indipendente dall'interfaccia; niente JavaScript dedicato agli avvisi in questa fase.
- Il testo dei pulsanti sceglie bianco o nero secondo il contrasto migliore. Usare font locali con licenze incluse; dichiarare solo la famiglia selezionata e lasciare il caricamento dei file al loro effettivo utilizzo.
- Larghezze: validare contenuto ≤ estesa ≤ layout considerando le modifiche simultanee. I limiti difensivi di rendering non devono riscrivere i valori salvati.
- Header in linea o centrato con menu sotto: mantenere un solo menu nel DOM.
- Non usare variabili interne del proxy del Customizer. Verificare anteprima e salvataggio prima di introdurre selective refresh.
- FX Builder, FX Shortcodes e FX Builder Widgets sono facoltativi; non chiamarne direttamente le API per i percorsi essenziali.
- Aree widget opzionali con ID stabili; nessun contenuto essenziale dipendente da widget o plugin.
- Tutte le funzioni e gli handle propri usano il prefisso `githeme`; text domain `githeme`.
- Escaping contestuale in uscita; preservare il rendering nativo di contenuti, menu, widget e commenti.

## Verifiche

- Eseguire lint con PHP 8.2 disponibile, senza installare strumenti.
- Verificare sintassi JavaScript, hook, escaping e indipendenza dai plugin.
- Controllare le differenze Git del tema e l'assenza di modifiche nel repository ClassicPress.
- Segnalare separatamente le prove manuali MAMP: attivazione, homepage statica, navigazione da tastiera/mobile, editor, Customizer, widget, commenti e combinazioni FX.
- Non attivare temi/plugin né salvare impostazioni nel database senza autorizzazione.
