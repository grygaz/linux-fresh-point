# Linux Fresh Install atkūrimo programa

Programa skirta **atkurti Linux distribucijos sistemą į kuo artimesnę „fresh install“ būseną**, nereikalaujant iš naujo diegti visos operacinės sistemos.

Pagrindinis programos tikslas – pašalinti vartotojo įdiegtas programas, papildomus paketus bei jų konfigūracijas ir grąžinti sistemą į pradinę būseną, išsaugant tik tai, kas priklauso standartinei Linux distribucijos instaliacijai ir oficialiems sistemos atnaujinimams.

## Pagrindinis veikimo principas

Programa analizuoja dabartinę sistemos būseną ir nustato, kurie paketai bei programos priklauso:

- pradinei distribucijos instaliacijai;
- oficialiems sistemos atnaujinimams;
- vartotojo papildomai įdiegtoms programoms;
- papildomoms priklausomybėms ir nereikalingiems paketams.

Atkūrimo metu vartotojo papildomai įdiegtos programos pašalinamos, o sistema paliekama su **numatytosiomis distribucijos programomis bei jų oficialiais atnaujinimais**.

## Ko siekiama

Po atkūrimo sistema turėtų būti tokios būsenos, tarsi vartotojas būtų atlikęs švarią Linux distribucijos instaliaciją ir įdiegęs visus iki atkūrimo momento išleistus oficialius sistemos atnaujinimus.

Programa neturėtų grąžinti senesnių paketų versijų. Jos tikslas – atkurti **švarią sistemos programinės įrangos sudėtį**, o ne būtinai seną paketų versiją.

## Pagrindinės funkcijos

- Automatinis įdiegtų paketų inventorizavimas.
- Sistemos paketų atskyrimas nuo vartotojo įdiegtų paketų.
- Vartotojo papildomai įdiegtų programų pašalinimas.
- Nereikalingų priklausomybių ir likusių paketų išvalymas.
- Paketų tvarkyklės būsenos sutvarkymas.
- Oficialaus distribucijos atnaujinimo palikimas.
- Sistemos konfigūracijų ir vartotojo duomenų išsaugojimo galimybė.
- „Dry run“ režimas, leidžiantis prieš atkūrimą pamatyti, kas bus pašalinta.
- Atkūrimo žurnalas (log), kuriame registruojami visi atlikti veiksmai.

## Saugumas

Kadangi programa keičia sistemos paketų būseną, prieš atliekant atkūrimą rekomenduojama sukurti atsarginę svarbių duomenų kopiją.

Programa neturėtų automatiškai šalinti paketų, kurie yra būtini sistemos paleidimui ar pagrindiniam jos veikimui. Prieš atliekant pakeitimus vartotojui turi būti pateikiama aiški suvestinė, kokie paketai ir programos bus pašalinti.

## Galutinis rezultatas

**Fresh Install Restore** leidžia grąžinti Linux sistemą į švarią, standartinę programinės įrangos būseną:

> **Numatytosios distribucijos programos + oficialūs sistemos atnaujinimai – vartotojo papildomai įdiegtos programos.**

Tokiu būdu galima „išvalyti“ sistemą ir grįžti prie švarios programinės aplinkos neperrašant visos operacinės sistemos.
