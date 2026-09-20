# Programma di ripristino Linux Fresh Install

Il programma mira a **ripristinare una distribuzione Linux a uno stato il più possibile simile a un’installazione pulita**, senza reinstallare l’intero sistema operativo.

L’obiettivo principale è rimuovere applicazioni installate dall’utente, pacchetti aggiuntivi e relative configurazioni, riportando il sistema allo stato iniziale e conservando i componenti standard della distribuzione e gli aggiornamenti ufficiali.

## Principio di funzionamento

Il programma analizza lo stato attuale del sistema e identifica i pacchetti e le applicazioni appartenenti a:

- installazione iniziale della distribuzione;
- aggiornamenti ufficiali del sistema;
- applicazioni aggiunte successivamente dall’utente;
- dipendenze aggiuntive e pacchetti non necessari.

Durante il ripristino vengono rimosse le applicazioni aggiunte dall’utente, lasciando **le applicazioni predefinite della distribuzione e i loro aggiornamenti ufficiali**.

## Obiettivo

Dopo il ripristino il sistema dovrebbe assomigliare a una nuova installazione Linux con tutti gli aggiornamenti ufficiali pubblicati fino al momento del ripristino.

Il programma non dovrebbe ripristinare versioni precedenti dei pacchetti. L’obiettivo è ripristinare **una composizione pulita del software di sistema**, non necessariamente le vecchie versioni.

## Funzioni principali

- Inventario automatico dei pacchetti installati.
- Distinzione tra pacchetti di sistema e pacchetti installati dall’utente.
- Rimozione delle applicazioni aggiunte dall’utente.
- Pulizia delle dipendenze inutili e dei pacchetti residui.
- Riparazione dello stato del gestore pacchetti.
- Conservazione degli aggiornamenti ufficiali della distribuzione.
- Possibilità di conservare configurazioni di sistema e dati utente.
- Modalità dry run per vedere cosa verrà rimosso prima del ripristino.
- Registro di ripristino con tutte le operazioni effettuate.

## Sicurezza

Poiché il programma modifica lo stato dei pacchetti di sistema, si consiglia di eseguire una copia di sicurezza dei dati importanti prima del ripristino.

Il programma non dovrebbe rimuovere automaticamente i pacchetti essenziali per l’avvio o il funzionamento di base del sistema. Prima di applicare modifiche, deve presentare un riepilogo chiaro dei pacchetti e delle applicazioni da rimuovere.

## Risultato finale

**Fresh Install Restore** mira a riportare Linux a uno stato software pulito e standard:

> **Applicazioni predefinite della distribuzione + aggiornamenti ufficiali del sistema − applicazioni aggiunte dall’utente.**

Questo permette di pulire il sistema e tornare a un ambiente software pulito senza reinstallare l’intero sistema operativo.
