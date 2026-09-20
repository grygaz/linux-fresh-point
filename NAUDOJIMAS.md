# Linux fresh point

GTK4 programa, rodanti įdiegtas programas ir paketus. Leidžia pasirinkti vieną ar kelis paketus, peržiūrėti šalinimą ir išsaugoti atkūrimo tašką – dabartinių paketų sąrašą. Numatytoji kalba: anglų; meniu taip pat yra lietuvių, rusų, kinų ir italų kalbos.

## Paleidimas ir diegimas

Išskleisk archyvą ir paleisk `./start`, arba tame aplanke vykdyk:

```sh
/usr/bin/python3 -I app.py
```

Meniu nuorodą įdiegia `python3 install-menu.py` (be sudo). Reikia Python 3, PyGObject (`gi`), GTK4 ir PolicyKit (`pkexec`) su darbalaukio autentifikavimo agentu. APT papildomai reikia `python3-apt`; Arch – `pacman-conf`; RPM sistemoms – `rpm`; Gentoo – Python Portage modulio. Programos diegiklis šių sistemos priklausomybių automatiškai neįdiegia.

Programą paleisk įprasto vartotojo teisėmis. Administratoriaus teisės prašomos tik vykdant šalinimą.

## Automatinis atpažinimas

Programa skaito `/etc/os-release` (`ID`, tada `ID_LIKE`) ir tikrina atitinkamo valdiklio buvimą. Lange rodoma distribucija ir jos valdiklis. Jei distribucija nežinoma arba jos valdiklio nėra, pateikiama klaida, kitas įdiegtas valdiklis automatiškai nepasirenkamas.

| Sistemų šeima | Valdiklis | Šalinimo vykdymas |
|---|---|---|
| Debian, Ubuntu ir jų dariniai | APT | Integruotas APT planas, patvirtinimas ir vykdymas |
| Arch, Manjaro ir jų dariniai | Pacman | Gimtojo valdiklio patvirtinimas terminale |
| Gentoo | Portage | Tikslinis `emerge --depclean --ask`, su priklausomybių tikrinimu |
| Fedora, RHEL, Rocky, AlmaLinux | DNF | DNF terminale; prieš tai papildoma `rpm -e --test` patikra |
| openSUSE, SLES | Zypper | Zypper terminale; prieš tai papildoma `rpm -e --test` patikra |

Ne APT sistemose reikia vieno iš terminalų: GNOME Terminal, Konsole, Xfce Terminal, MATE Terminal arba xterm. Po GUI peržiūros atsidaro terminalas, kuriame matomas gimtojo valdiklio galutinis planas. Jį reikia patvirtinti. Paketų valdiklio diagnostika gali būti anglų kalba.

## Atkūrimo taškai

Sukurk tašką tuomet, kai įdiegtų programų rinkinys tinka. Vėliau pasirink tašką ir peržiūrėk valymą. Programa siekia pašalinti papildomus paketus, tačiau išsaugo taško paketų dabartines versijas, jų dabartines priklausomybes ir apsaugotus sistemos komponentus. Jei programa ar biblioteka tebėra reikalinga, ji paliekama arba šalinimas atmetamas. Nauji branduoliai ir kiti apsaugoti sistemos paketai gali likti, net jei taške jų nebuvo.

Tai **ne failų atsarginė kopija ir ne visiškas sistemos atkūrimas**: nustatymai negrąžinami, ištrintos programos neįdiegiamos iš naujo, atnaujinimai neatšaukiami. Rankiniu būdu įrašyti failai, AppImage, Flatpak, Snap, pip ar npm paketai nevalomi. Programų vartotojo nustatymai ir dokumentai tiesiogiai netrinami; paketo pašalinimo scenarijus vis dėlto gali šalinti savo paslaugos duomenis. Sisteminės konfigūracijos tvarkymas priklauso nuo gimtojo valdiklio.

Taškas susiejamas su kompiuteriu, distribucija, leidimu, architektūra ir valdikliu. Seni Debian taškai lieka suderinami pagal jų ankstesnę kompiuterio bei leidimo patikrą. Keičiant distribucijos leidimą sukurk naują tašką.

Bibliotekų automatinio pašalinimo parinktis veikia APT ir Pacman. DNF, Zypper ir Portage atveju atskiro bibliotekų automatinio šalinimo parinktis išjungta – bibliotekas galima pasirinkti paketų sąraše arba valyti pagal tašką. APT atsisiuntimų podėlio valymas prieinamas tik APT. Kitų valdiklių konfigūracijos, užraktai ir papildomos priklausomybės gali neleisti atlikti viso plano.

## Duomenys ir žurnalai

Kad išliktų ankstesni taškai bei kalbos pasirinkimas, naudojamas senasis duomenų katalogas `~/.local/share/linux-tvarka/` (arba `$XDG_DATA_HOME/linux-tvarka/`). Įdiegta programa yra jo `app/` kataloge, taškai – `points/`. Meniu matomas naujas pavadinimas „Linux fresh point“.

APT vykdymo žurnalai: `/var/log/linux-tvarka/`; kitų valdiklių – `/var/log/linux-fresh-point/`.

## Patikros ribos

Ši versija patikrinta Debian 13: realus APT sąrašo skaitymas, nekeičiant sistemos atlikta plano peržiūra, GTK sąsajos patikra ir automatiniai testai. Pacman, Portage, DNF ir Zypper adapteriai pridėti, tačiau tikrose šių distribucijų sistemose dar nepatikrinti. Jiems patikrinta atpažinimo, komandų sudarymo ir priklausomybių saugojimo logika. Prieš kasdienį naudojimą šiose sistemose versiją išbandyk virtualioje mašinoje.

## Taškų trynimas ir portable versija

Prie taško yra trynimo mygtukas su patvirtinimu. Jis pašalina tik tašką, ne programas. Pradinis kartu pateiktas taškas paslepiamas pašalinimo žyme.

Nešiojamam paleidimui naudok atskirą portable ZIP ir `./start`. Išsamiau – PORTABLE.md.

## Apie programą ir licencija

„About / Apie programą“ lange pateiktas programos tikslas, galimybės, ribos, GNU GPL v3 licencijos tekstas ir savanoriškos PayPal paramos nuoroda gavėjui `grygas@gmail.com`. Programa platinama pagal GPL-3.0-only; visas tekstas – LICENSE.

## Nustatymai ir aprašymas

Viršuje pasirink „Settings / Nustatymai“: čia yra kalbos pasirinkimas ir „About / Apie programą“. Pateiktas pilnas autoriaus aprašymas ir dabartinių galimybių paaiškinimas. GNU simbolis nukreipia į GNU projektą; autoriaus ir licencijos informacija pateikta NOTICE.


PayPal paramos mygtukas atidaro https://paypal.me/grygaz. Sumą ir mokėjimą vartotojas pasirenka bei patvirtina PayPal svetainėje.
