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

Vetvy v našom forku:
- `fix/labware-registry-import` (PR #2)
- `feature/autofill-station` (PR #3)
- `feature/provenance-colours` (PR #4)
- `lab-notes` (tento súbor)

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
