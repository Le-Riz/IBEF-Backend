# Guide d'installation (nouveau systeme)

Ce guide explique comment installer IBEF-Backend sur une machine neuve Linux et le lancer automatiquement via systemd.

## 1. Prerequis

- Un systeme Linux avec systemd
- Acces sudo
- Python 3.10+ avec le module venv
- Git

Exemple (Debian/Ubuntu):

```bash
sudo apt update
sudo apt install -y git python3 python3-venv
```

## 2. Recuperer le projet

```bash
git clone https://github.com/Le-Riz/IBEF-Backend.git
cd IBEF-Backend
```

Si le projet est deja present (copie locale), placez-vous simplement a la racine du depot.

## 3. Configurer les capteurs

Editez le fichier `config/sensors_config.json` pour adapter vos capteurs:

- `serial_id` pour chaque capteur reel
- `baud` (vitesse serie)

Pour retrouver les identifiants serie disponibles:

```bash
ls -l /dev/serial/by-id/
```

## 4. Installer et demarrer le service systemd

Le script `scripts/setup_systemd.sh` fait automatiquement:

- Copie de `ibef-backend.service` dans `/etc/systemd/system/`
- Remplacement de `<CHANGE_ME>` par le chemin courant du projet
- `systemctl daemon-reload`
- `systemctl enable ibef-backend.service`
- `systemctl restart ibef-backend.service`

Execution:

```bash
chmod +x scripts/setup_systemd.sh
./scripts/setup_systemd.sh
```

Important:

- Lancez la commande depuis la racine du projet.
- Le service cree automatiquement `.venv` au premier demarrage via `scripts/create_venv.sh`.

## 5. Verifier que tout fonctionne

Etat du service:

```bash
sudo systemctl status ibef-backend.service
```

Logs en temps reel:

```bash
sudo journalctl -u ibef-backend.service -f
```

Test rapide API:

```bash
curl http://127.0.0.1:8000/health
```

Reponse attendue:

```json
{"status":"ok","app":"IBEF Backend API"}
```

## 6. Commandes utiles

Redemarrer le service:

```bash
sudo systemctl restart ibef-backend.service
```

Arreter le service:

```bash
sudo systemctl stop ibef-backend.service
```

Desactiver le lancement automatique:

```bash
sudo systemctl disable ibef-backend.service
```

## 7. Mise a jour de l'application

Depuis la racine du projet:

```bash
git pull
sudo systemctl restart ibef-backend.service
```

Si les dependances Python ont change, supprimez `.venv` puis redemarrez le service pour forcer une recreation propre:

```bash
rm -rf .venv
sudo systemctl restart ibef-backend.service
```

## 8. Desinstallation

```bash
sudo systemctl stop ibef-backend.service
sudo systemctl disable ibef-backend.service
sudo rm -f /etc/systemd/system/ibef-backend.service
sudo systemctl daemon-reload
```

Vous pouvez ensuite supprimer le dossier du projet si necessaire.
