# Linux fresh point – portable

Išskleisk portable ZIP į rašomą aplanką (pvz., USB laikmeną). Terminale tame aplanke paleisk:

```sh
./start
```

Diegimo ir meniu nuorodos nereikia. Nustatymai bei nauji atkūrimo taškai saugomi šalia programos, `portable-data/` kataloge, atskirai kiekvienam kompiuteriui. Prieš atjungdamas USB uždaryk programą. Portable archyve nėra šio kompiuterio pradinio atkūrimo taško ar vartotojo duomenų.

Tai ne savarankiškas AppImage: reikalingos kompiuteryje įdiegtos Python 3, PyGObject, GTK4 ir gimtojo paketų valdiklio bibliotekos. APT reikia python3-apt, Gentoo – Python Portage. Šalinimui reikia pkexec ir autentifikavimo agento; ne APT sistemose – palaikomo terminalo. Paleidiklis patikrina pagrindines priklausomybes; jų automatiškai neįdiegia.

Palaikomos APT, Pacman, Portage, DNF ir Zypper sistemų šeimos, aprašytos NAUDOJIMAS.md. Visų Linux distribucijų, architektūrų ar versijų suderinamumas negarantuojamas. Alpine/apk, NixOS, Void/xbps ir atominių sistemų (pvz., Fedora Silverblue) ši versija nepalaiko. Ne APT adapteriai dar neišbandyti tikrose distribucijose.

Paleista kitame kompiuteryje programa automatiškai perskaito to kompiuterio paketų duomenų bazę. Programų lange rodomi paketams priskirti darbalaukio meniu įrašai, paketų lange – įdiegti sistemos paketai. Flatpak, Snap, AppImage ir rankiniu būdu įdiegtos programos nėra visiškai inventorizuojamos ar šalinamos.

Taško eilutėje „Delete point“ pašalina išsaugotą paketų sąrašą po patvirtinimo. Paketai ir programų failai neliečiami. Senas kartu su įdiegta programa pateiktas pradinis taškas paslepiamas pašalinimo žyme, kad programos atnaujinimas jo nesugrąžintų; vartotojo sukurto taško JSON failas ištrinamas.

## Apie programą ir licencija

„About / Apie programą“ lange pateiktas programos tikslas, galimybės, ribos, GNU GPL v3 licencijos tekstas ir savanoriškos PayPal paramos nuoroda gavėjui `grygas@gmail.com`. Programa platinama pagal GPL-3.0-only; visas tekstas – LICENSE.


PayPal paramos mygtukas atidaro https://paypal.me/grygaz. Sumą ir mokėjimą vartotojas pasirenka bei patvirtina PayPal svetainėje.
