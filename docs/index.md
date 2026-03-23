# IBEF Backend API

IBEF Backend est un service FastAPI pour l'acquisition temps reel de capteurs, le traitement des mesures et la gestion persistante des essais.

## Fonctionnalites principales

- Acquisition capteurs en continu (FORCE, DISP_1 a DISP_5)
- Capteur calcule `ARC` derive de DISP_1, DISP_2 et DISP_3
- Historique a nombre de points fixe: 300 points par fenetre (30s, 60s, 120s, 300s, 600s)
- Gestion des essais: demarrage, arret, consultation, telechargement et archivage
- Persistance disque des metadonnees (JSON) et mesures (CSV/logs)

## Demarrage rapide

```bash
# lancer l'API (mode dev)
./run.sh

# lancer la documentation MkDocs
./run.sh doc
```

Verification rapide de l'API:

```bash
curl http://127.0.0.1:8000/health
```

Reponse attendue:

```json
{"status":"ok","app":"IBEF Backend API"}
```

## Acces API

- Endpoint de sante: `GET /health`
- Documentation interactive complete: voir [API Reference (interactive)](api-reference.md)
- Pour les details de contrats (schemas, codes de retour, exemples), privilegier la reference OpenAPI plutot qu'une liste partielle ici.

## Documentation disponible

- [Guide d'installation](installation-guide.md) : installation sur nouveau systeme Linux + service systemd
- [Configuration capteurs](config.md) : structure et utilite de `config/sensors_config.json`
- [Lecture serial](serial-data.md) : format des trames FORCE/DISP et chaine de traitement
- [API Reference (interactive)](api-reference.md) : specification OpenAPI complete embarquee dans MkDocs

## Notes techniques

- Le capteur `ARC` suit la relation metier:

	$$ARC = DISP_1 - \frac{DISP_2 + DISP_3}{2}$$

- Les historiques utilisent un echantillonnage uniforme pour garantir une charge memoire stable et des reponses API predictibles.
