# Pracovné poznámky – 6. 10. 2026

Čo sme v našom forku robili, aby sme na to vedeli nadviazať. Kalibrácia,
teachpointy, IP adresy a záznamy komunikácie sem zámerne nepatria. Ostávajú
lokálne na laboratórnom PC (pozri koniec).

## Pull requesty do pôvodného repozitára

| PR | Obsah | Stav |
|---|---|---|
| [kelsorj/pyBravo#2](https://github.com/kelsorj/pyBravo/pull/2) | Oprava importu labware z exportu registrov a Labware Editora, ktorý nuloval geometriu jamiek | otvorený |
| [kelsorj/pyBravo#3](https://github.com/kelsorj/pyBravo/pull/3) | Autofill station: pumpy, váha, UI panel a 3D model. **Zatiaľ len ručné ovládanie, nie je pripravené na pipeline.** | otvorený |
| [kelsorj/pyBravo#4](https://github.com/kelsorj/pyBravo/pull/4) | Farebné označenie pôvodu: Imported / Imported, edited / Local | otvorený |
| [kelsorj/pyBravo#5](https://github.com/kelsorj/pyBravo/pull/5) | Kroky pre workflow: **Pump Reagent**, Stop Pumps, Read Level a oprava výšky od dna pri Mix/Aspirate/Dispense. Stavia na #3. | otvorený |

Vetvy v našom forku:
- `fix/labware-registry-import` (PR #2)
- `feature/autofill-station` (PR #3)
- `feature/provenance-colours` (PR #4)
- `feature/autofill-workflow-steps` (PR #5, postavené na #3)
- `lab-notes` (tento súbor)

## Umývanie tipov ako workflow (PR #5)

Krok **Pump Reagent** je analógiou rovnomennej úlohy z pôvodného softvéru.
Jeho parametre:
- **Reservoir mode** (Fill/Empty), rýchlosť pumpy a čas behu
- **How often**: čerpá pri 1. prechode a potom pri každom N-tom
- **Allow concurrent operation**: ďalšie kroky idú počas čerpania
- **Run second pump**: zapne aj druhú pumpu
- **Weigh station**: prahy akcie a zastavenia

Umývanie tipov je slučka (Loop) s tromi krokmi: Pump Reagent Fill → Mix na
pozícii stanice, ako keby to bola doska → Pump Reagent Empty. Vodu sa dá
meniť aj počas miešania, keď sa zapne druhá pumpa a súbežný beh.

Naše konkrétne procedúry („Tip wash: fill - mix - empty (5x)“ a „Tip wash:
flowing (5x)“: tipy 70 µL z pozície 9, umývanie v 3, späť do 9) sú lokálne
workflowy v `~/.pybravo/workflows` na laboratórnom PC, nie v repozitári.
Hodnoty miešania sú v nich zatiaľ zástupné.

## Hold level: udržiavanie hladiny pri prietoku (večer 6. 10.)

Režim **Hold level** v Pump Reagent (a v ručnom paneli) plní aj vypúšťa naraz
a podľa váhy drží cieľovú hladinu. Cieľ aj prítok sa dajú meniť za behu. Panel
ukazuje rýchlosti púmp a 120 s graf. Lokálny workflow „Tip wash in flow,
hold 80 %“ mieša špičky v pretekajúcej vode.

Merania na stanici 384ST (dlhé behy, krátke 5 s behy sú na bublinu
nepoužiteľné):
- **Pumpy sú rovnako silné.** „Slabší odtok“ (3 %/s) bola bublina v odtokovej
  hadici. Po 30 s preplachu na 100 % má odtok ~10 %/s pri 100 % a 3,1 %/s pri
  30 % (lineárne). Prítok má ~4,7 %/s pri 50 % a ~7,5–8 %/s pri 100 %.
  Mŕtvy čas: prítok ~0,6 s, odtok ~1 s (pri plných hadiciach).
- **Suché hadice.** Odtok, ktorý bežal naprázdno, na 30–40 % vôbec nepotiahne
  (0,13 %/s za 30 s), na 100 % sa zavodní za 1–5 s. Prívod sa v pokoji vracia
  do zdroja. Na 50 % potom nedodal nič za 90 s, na 100 % voda prišla po 6–10 s.
- **Váha.** Šum ±0,7 %. Prázdna vanička ukazuje −10 až −12 % podľa toho, či sú
  hadice plné, takže taru treba merať v rovnakom stave hadíc ako pri práci.
- **Regulátor.** Nové predvolené hodnoty sú naladené na modeli podľa týchto
  meraní: kp 1,5, ki 0,2, lookahead 1 s, zmena odtoku 20 %/s, rampa cieľa
  15 %/s. Na HW pri 75 → 50 % klesol jitter odtoku z ~11 na 2,5–4,5 %/vzorku.
  Odchýlka bola ±2 % pri 75 % a ~3,5 % pri 50 % (ešte bez rýchlejšieho
  odvíjania integrálu).
- **Zavodnenie v Hold.** Prítok ide na 100 %, kým hladina nestúpne, potom
  hneď na požadovanú hodnotu. Odtok ide 15 % pod cieľom na 100 %, kým hladina
  zreteľne neklesá (max 8 s). **Overené len v simulácii a testoch.** Posledný
  HW beh mal ešte pevný 1,5 s pulz a ten na úplne suchú linku nestačil (plató
  na 85 % na 13 s).
- Opravená chyba: Hold po Stop Pumps ďalej reguloval a v nasledujúcom kroku
  Empty znova zapínal prítok.

Nabudúce:
- Overiť zavodnenie odtoku na HW (`hw_exp.py hold 90 75 50 50 50` so suchým
  odtokom).
- Zmerať taru s plnými hadicami.
- Skúsiť umývanie s reálnymi špičkami: hold 80 % a súbežný Mix (workflow
  `b4620de8…`). Čas holdu musí pokryť všetky miešania.
  Simulácia z 6. 10. večer prebehla celá bez chýb: oprava Stop → Empty
  funguje, vanička sa vypustí a prítok zostane vypnutý.
  **Chyba v poradí krokov:** Hold beží súbežne a vráti sa hneď, takže prvý
  Mix začne v prázdnej vaničke. Pred Hold treba pridať „Fill by weight do
  ~80 %“.
- PR #5 (do pôvodného repozitára) dopĺňa Hold level a sekciu „Hardware
  findings“. Na HW sa Hold skúšal len cez ručný panel, nie ako workflow.
  Posledná verzia zavodňovania je overená len v simulácii.
- Čiastočne plná krabička špičiek: použiť existujúci head mode.

## 1. Import z exportu registrov

pyBravo vie načítať profil prístroja z exportu registrov Windows (`.reg`), cez
**Profiles → Import .reg…** alebo `POST /api/profile/import_reg`.
- **Prenesie:** osi, rýchlosti, homing, teachpointy, gripper, prúdové limity a
  bezpečnostné nastavenia.
- **Neprenesie:** IP adresu (v registroch nie je).
- **Typ hlavy:** registry hodnota `Head type = 0` (96ST) zatiaľ nemá mapovanie,
  hlavu treba nastaviť ručne.

Labware a liquid classes sa importujú skriptami:

```bash
python scripts/import_labware_from_registry.py labware.reg --dry-run
python scripts/import_liquid_classes_from_registry.py liquid.reg --machine-id <ID> --dry-run
```

**Opravené chyby (PR #2):**
- Skript hľadal kľúč `Velocity11\shared` s malým „s“, export však píše `Shared`,
  takže skript nenašiel nič.
- Keď sa Labware Editor naplnil z katalógu, nepreniesol hĺbku jamky, offset A1 ani
  rozostup jamiek. Prvé uloženie ich potom zapísalo ako 0 a všetky jamky padli na A1.

**Ešte otvorené:**
- Liquid classes nie sú naimportované, treba rozhodnúť `--machine-id`.
- Dva LT250 tip boxy majú rovnaké meno ako v novom súbore `96am.yaml`, takže sú
  v katalógu dvakrát.

## 2. Autofill station: pumpy a váha (PR #3)

Pumpy aj váha sú na zbernici príslušenstva prístroja, nie na COM porte. Darwin
controller im preposiela 9-bajtové sériové správy (`TCPMessageType.SERIAL_DATA`).
Formát sme zistili zo sieťovej komunikácie nášho prístroja:

| Príkaz | Bajty | Význam |
|---|---|---|
| spusti pumpu | `AC mm pp dd ss ss` | modul, pumpa, smer (1 = forward, 0 = reverse), rýchlosť v 0,01 % (LE, 0–10000) |
| zastav pumpy | `AE 00` | zastaví všetky pumpy, posiela sa 2× |
| stav modulu | `AF mm` | odpoveď sa počas behu nemení |
| čítaj váhu | `B3 mm` | A/D hodnota v bajtoch 2–3 odpovede (LE) |
| detekcia pri init | `AB 00` | odpoveď `AB 00 02 02` |

- **Pumpa sa sama nezastaví.** Príkaz `AC` nemá čas behu. Ovládač preto vždy
  časuje beh strážnym vláknom (watchdog) a pumpy zastaví aj pri Abort, odpojení
  a zmene profilu. Jeden beh trvá najviac 600 s.
- **Tara a rozsah** sú len kalibrácia v programe:
  hladina % = (hodnota − tara) / (rozsah − tara).
- **Kde to je:**
  - ovládač `pybravo/accessories/autofill.py`
  - API `/api/accessories/{id}/autofill/level|run|stop`
  - panel **Config → Accessories → Add Autofill**
- **3D model:** `frontend/accessories/AutofillStation.gltf`, generuje ho
  `scripts/build_autofill_tray_model.py`. Uzol `liquid` sleduje hladinu z váhy.
  Model sa vyberá v zozname **Model** pri príslušenstve, predvolene je
  „Standard position“.
- **Overené na prístroji:** váha sedí s diagnostikou prístroja a pumpy idú aj
  stoja podľa očakávania.

**Nie je hotové:** krok workflowu (pipeline) na plnenie alebo vyprázdnenie,
čakanie na hladinu a blokovanie pipetovania počas plnenia.

## 3. Farebné označenie pôvodu (PR #4)

V profiloch, labware, liquid classes a príslušenstve sa farebne odlišuje, čo
pochádza z importu a čo vzniklo v pyBravo:

| Farba | Význam |
|---|---|
| 🔵 Imported | z exportu registrov, nezmenené |
| 🟠 Imported, edited | z importu, potom upravené v pyBravo |
| 🟢 Local | vytvorené v pyBravo |

V editore labware je aj filter podľa pôvodu.

**Ešte bez PR:** import príslušenstva (autofill a Teleshake) z profilu v
registroch. Potrebuje typ `autofill` z PR #3, preto ho pošleme až po jeho
zlúčení. Zatiaľ je necommitnutý v pracovnom adresári na laboratórnom PC.

## Na laboratórnom PC (mimo repozitára)

- Záloha registrov, záznamy komunikácie a pomocné skripty na zachytávanie
  (`pktmon`) sú v `Documents\Bravo-registry-backup-2026-10-06`.
- Lokálne profily `384ST_8shaker_3Autofill-weight` a
  `96ST_8shaker_3Autofill-weight` sú importy z registrov. Pre reálny prístroj
  treba nastaviť `controller_type: darwin_native` a adresu prístroja.
- Pomocné nástroje:
  - `git` z GitHub Desktop (nie je v PATH)
  - GitHub CLI `gh`, prihlásený ako `xaviersvk`
  - Wireshark (`tshark`) na čítanie záznamov
