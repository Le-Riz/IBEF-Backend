# Configuration des capteurs (`config/sensors_config.json`)

Ce fichier décrit les capteurs physiques, les capteurs calculés et le mode émulation du backend.

La configuration est chargée au démarrage par `ConfigLoader` (`src/core/config_loader.py`) puis utilisée par:

- `ServiceManager` (`src/core/service_manager.py`) pour démarrer les ports série (port + baudrate)
- `SensorManager` (`src/core/services/sensor_manager.py`) pour décider quels capteurs sont connectés/émulés et calculer `ARC`
- `Graphique` (`src/core/processing/graphique.py`) et `TestManager` (`src/core/services/test_manager.py`) pour les libellés et échelles de graphe

## Fichier JSON actuel

```json
{
	"emulation": [],
	"sensors": {
		"FORCE": {
			"baud": 115200,
			"description": "Force sensor (capteur de force)",
			"display_name": "Force (N)",
			"serial_id": "usb-1a86_USB2.0-Serial-if00-port0",
			"max": 1000,
			"enabled": true
		},
		"DISP_1": {
			"baud": 115200,
			"description": "Motion sensor 1 (capteur de mouvement 1)",
			"display_name": "Fleche centrale (mm)",
			"max": 14,
			"serial_id": "usb-Adafruit_Adafruit_Feather_M0_BF31609450304C4B552E3120FF042E0C-if00",
			"enabled": true
		},
		"DISP_2": {
			"baud": 115200,
			"description": "Motion sensor 2 (capteur de mouvement 2)",
			"display_name": "Deplacement 2 (mm)",
			"max": 14,
			"serial_id": "usb-Adafruit_Adafruit_Feather_M0_714ACFDC50304C4B552E3120FF052C1A-if00",
			"enabled": true
		},
		"DISP_3": {
			"baud": 115200,
			"description": "Motion sensor 3 (capteur de mouvement 3)",
			"display_name": "Deplacement 3 (mm)",
			"max": 14,
			"serial_id": "usb-Adafruit_Adafruit_Feather_M0_B3EE8F3050304C4B552E3120FF08061F-if00",
			"enabled": true
		},
		"DISP_4": {
			"baud": 115200,
			"description": "Motion sensor 4 (capteur de mouvement 4)",
			"display_name": "Deplacement 4 (mm)",
			"max": 14,
			"serial_id": "usb-Adafruit_Adafruit_Feather_M0_C6C61DEE50304C4B552E3120FF022A31-if00",
			"enabled": true
		},
		"DISP_5": {
			"baud": 115200,
			"description": "Motion sensor 5 (capteur de mouvement 5)",
			"display_name": "Deplacement 5 (mm)",
			"max": 14,
			"serial_id": "usb-Adafruit_Adafruit_Feather_M0_96D2E6055154384153202020FF182B13-if00",
			"enabled": true
		}
	},
	"calculated_sensors": {
		"ARC": {
			"description": "Calculated arc (circular deflection)",
			"display_name": "Fleche d'arc (mm)",
			"dependencies": [
				"DISP_1",
				"DISP_2",
				"DISP_3"
			],
			"max": 1
		}
	}
}
```

## Structure générale

Le fichier est composé de 3 sections:

- `emulation`: liste de capteurs à simuler (par nom d'enum, ex: `"FORCE"`)
- `sensors`: capteurs physiques branchés sur ports série
- `calculated_sensors`: capteurs virtuels calculés à partir d'autres capteurs

## Utilité détaillée de chaque champ

### 1. Section `emulation`

- Type: `string[]`
- Valeur actuelle: `[]` (aucune émulation forcée depuis le JSON)

Utilité:

- Si un capteur est listé ici, il est généré artificiellement dans `SensorManager._emulation_loop`.
- Le mode peut être surchargé par la variable d'environnement `EMULATION_MODE` (dans `src/main.py`).
- En cas d'échec de démarrage et si l'émulation est autorisée, l'application peut basculer en émulation complète.

### 2. Section `sensors` (capteurs physiques)

Clés autorisées: `FORCE`, `DISP_1`, `DISP_2`, `DISP_3`, `DISP_4`, `DISP_5`.

Chaque capteur contient:

- `baud` (int): vitesse de communication série.
	Utilisé lors de la création du `SerialHandler`.
- `serial_id` (string): suffixe du chemin `/dev/serial/by-id/`.
	Utilisé pour ouvrir le bon port physique.
- `enabled` (bool): active/désactive logiquement le capteur.
	Influence la connectivité logique (`is_sensor_enabled`) et l'émulation.
- `display_name` (string): nom affiché sur les axes des graphiques.
- `max` (float): borne supérieure pour l'échelle des graphiques.
- `description` (string): texte descriptif (documentation/métadonnées).

Important:

- Si `serial_id` est vide, le capteur est ignoré côté acquisition matérielle.
- `enabled=false` retire le capteur des capteurs actifs (et donc impacte aussi les capteurs calculés qui en dépendent).

### 3. Section `calculated_sensors` (capteurs virtuels)

Clé actuelle: `ARC`.

Champs:

- `dependencies` (`string[]`): capteurs d'entrée nécessaires au calcul.
- `display_name`: libellé d'axe/affichage.
- `max`: échelle graphique max.
- `description`: description fonctionnelle.

Utilité dans le code:

- `ConfigLoader` convertit les dépendances en références vers les capteurs réels.
- `SensorManager` recalcule `ARC` à chaque nouvelle donnée de dépendance.
- Formule actuelle:

	$$ARC = DISP_1 - \frac{DISP_2 + DISP_3}{2}$$

- Le capteur `ARC` est considéré connecté uniquement si toutes ses dépendances sont connectées.

## Configuration active résumée

### Capteurs physiques

| Capteur | Activé | Baud | Max | Affichage | Serial ID |
|---|---:|---:|---:|---|---|
| FORCE | oui | 115200 | 1000 | Force (N) | usb-1a86_USB2.0-Serial-if00-port0 |
| DISP_1 | oui | 115200 | 14 | Fleche centrale (mm) | usb-Adafruit_Adafruit_Feather_M0_BF31609450304C4B552E3120FF042E0C-if00 |
| DISP_2 | oui | 115200 | 14 | Deplacement 2 (mm) | usb-Adafruit_Adafruit_Feather_M0_714ACFDC50304C4B552E3120FF052C1A-if00 |
| DISP_3 | oui | 115200 | 14 | Deplacement 3 (mm) | usb-Adafruit_Adafruit_Feather_M0_B3EE8F3050304C4B552E3120FF08061F-if00 |
| DISP_4 | oui | 115200 | 14 | Deplacement 4 (mm) | usb-Adafruit_Adafruit_Feather_M0_C6C61DEE50304C4B552E3120FF022A31-if00 |
| DISP_5 | oui | 115200 | 14 | Deplacement 5 (mm) | usb-Adafruit_Adafruit_Feather_M0_96D2E6055154384153202020FF182B13-if00 |

### Capteur calculé

| Capteur | Dépendances | Max | Affichage |
|---|---|---:|---|
| ARC | DISP_1, DISP_2, DISP_3 | 1 | Fleche d'arc (mm) |

### Emulation

- Valeur actuelle: liste vide (`[]`), donc priorité au mode matériel.
- Si `EMULATION_MODE` est défini dans l'environnement, cette variable prend la priorité sur le JSON.

## Valeurs par défaut et robustesse

Si une clé manque dans le JSON, `ConfigLoader` applique des valeurs par défaut:

- `baud`: `9600`
- `description`: `""`
- `display_name`: `""`
- `serial_id`: `""`
- `max`: `0.0`
- `enabled`: `true`

Si le fichier est absent ou invalide, un fallback interne est chargé (`_get_default_config`).

## Bonnes pratiques de modification

- Conserver exactement les noms d'enum (`FORCE`, `DISP_1`, etc.).
- Vérifier que chaque `serial_id` existe réellement dans `/dev/serial/by-id/`.
- Adapter `max` aux plages physiques réelles pour éviter des graphiques peu lisibles.
- Ne pas définir `ARC` dans `sensors` (il doit rester dans `calculated_sensors`).
- Garder les dépendances `ARC` cohérentes avec la formule métier.
