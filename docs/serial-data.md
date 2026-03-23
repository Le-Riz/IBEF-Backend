# Lecture Serial: stack complete et format des trames

Ce document explique le parcours complet d'une donnee capteur depuis le port serie jusqu'aux valeurs disponibles via l'API, puis detaille le format des trames FORCE et DEPLACEMENT (DISP_*).

## Vue d'ensemble de la stack

1. Demarrage des services
- Au lancement de l'application, le gestionnaire de services recupere les ports/baudrates depuis la configuration capteurs.
- Un `SerialHandler` est cree par capteur reel (FORCE, DISP_1 ... DISP_5).

2. Lecture bas niveau du port serie
- Chaque `SerialHandler` ouvre son port (`pyserial`) avec `baudrate` et `timeout`.
- Sur Linux, des optimisations de latence sont appliquees (VMIN/VTIME, buffers, etc.).
- La boucle de lecture lit `readline()`, decode en UTF-8 (`errors='ignore'`) puis supprime les espaces de debut/fin.

3. Passage par la queue asynchrone
- Chaque ligne valide est poussee dans une queue asynchrone partagee sous la forme:
	- `(sensor_id, ligne_texte, timestamp_reception)`
- Si la queue est pleine, la plus ancienne entree est supprimee pour privilegier les donnees recentes.

4. Consommation centralisee de la queue
- `SensorsTask` depile les messages et appelle les fonctions de traitement enregistrees.
- `SensorManager` recoit alors la ligne brute et route vers le bon parseur:
	- FORCE -> `_parse_force(...)`
	- DISP_1..DISP_5 -> `_parse_motion(...)`

5. Normalisation des valeurs
- Apres parsing, `SensorManager` publie une `SensorData`:
	- `raw_value`: valeur brute issue de la trame
	- `offset`: zero applique
	- `value`: valeur corrigee (`raw_value - offset`)
	- `timestamp`: temps associe a la mesure

6. Diffusion et usages metier
- Les callbacks recoivent les donnees parsees:
	- stockage instantane de la derniere valeur par capteur
	- calcul du capteur virtuel ARC (a partir de DISP_1/2/3)
	- enregistrement des donnees de test (`raw.log`, `raw_data.csv`)
	- alimentation des historiques et graphiques
- Les routes API exposent ensuite ces valeurs (raw, corrigees, historique, zero).

## Trame FORCE

### Exemple de trame

```text
ASC2 20945595 -165341 -1.527986e-01 -4.965955e+01 -0.000000e+00
```

### Regles de parsing

- La ligne est ignoree si elle ne contient pas `ASC2`.
- Decoupage par espaces avec `split()`.
- Condition minimale: au moins 5 elements.
- Valeur exploitee: element d'index `4` (5e colonne), converti en `float`.

Dans l'exemple ci-dessus:
- `parts[4] = -4.965955e+01` -> valeur force brute.

### Timestamp FORCE

- Le timestamp utilise est le temps de reception local (pris juste apres `readline()`).
- Il n'y a pas de recalage supplementaire specifique FORCE dans le parseur actuel.

## Trame DEPLACEMENT (DISP_1 a DISP_5)

### Exemple de trame

```text
76 144 262 us SPC_VAL usSenderId=0x2E01 ulMicros=76071216 Val=0.000
```

### Champs interpretes

- Signature de trame requise: `SPC_VAL`.
- `sending_timestamp`:
	- reconstruit a partir des tokens places avant `us`.
	- dans l'exemple: `76 144 262 us` -> `76144262 us` -> `76.144262 s`.
- `usSenderId=...`:
	- identifiant emetteur du capteur (ex: `0x2E01`).
- `ulMicros=...`:
	- timestamp de requete capteur, converti en secondes (ex: `76071216` -> `76.071216 s`).
- `Val=...`:
	- valeur de deplacement parsee en `float`.

### Correction temporelle appliquee

Le parseur corrige le timestamp de reception pour se rapprocher du temps capteur:

$$
t_{corrige} = t_{reception} - (t_{sending} - t_{request})
$$

avec:
- $t_{reception}$: timestamp local lors de la lecture serie
- $t_{sending}$: valeur reconstruite depuis `... us`
- $t_{request}$: valeur issue de `ulMicros`

Si les infos temporelles ne sont pas exploitables, la mesure peut etre marquee invalide.

### Filtrage metier actuel

- Workaround actif: si `Val < 0.02`, la valeur est forcee a `NaN` (filtrage anti-zero parasite).
- Cette regle est temporaire et clairement marquee dans le code comme un contournement.

## De la valeur brute a la valeur API

Apres parsing:

1. Valeur brute (`raw_value`) recue depuis la trame.
2. Application d'un offset de zero par capteur.
3. Valeur corrigee:

$$
value = raw\_value - offset
$$

4. Mise a disposition via les endpoints capteurs:
- valeur corrigee (`/sensor/{id}/data`)
- valeur brute (`/sensor/{id}/raw`)
- offset (`/sensor/{id}/zero`)
- historique (`/sensor/{id}/data/history`)

## Resume rapide

- FORCE: trame `ASC2 ...`, valeur en colonne 5 (`parts[4]`).
- DEPLACEMENT: trame `SPC_VAL ... Val=...`, avec recalage temporel via `us` et `ulMicros`.
- Toutes les mesures passent ensuite par la meme chaine: queue -> parse -> offset -> stockage -> API.
