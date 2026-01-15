#!/bin/bash

# Configuration
BASE_URL="http://192.168.1.200:8000"
INTERVAL=0.01  # Intervalle entre les requêtes en secondes
WINDOW=600    # Fenêtre de temps en secondes (10 minutes)

# Couleurs pour l'affichage
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Test de simulation ===${NC}"
echo -e "${YELLOW}Configuration:${NC}"
echo -e "  URL: ${BASE_URL}"
echo -e "  Fenêtre: ${WINDOW}s ($(($WINDOW / 60)) minutes)"
echo -e "  Intervalle: ${INTERVAL}s"
echo ""

# Vérifier que l'API est disponible
echo -e "${GREEN}Vérification de la disponibilité de l'API...${NC}"
until curl -s "${BASE_URL}/health" > /dev/null 2>&1; do
    echo -e "${RED}API non accessible à ${BASE_URL}${NC}"
    echo -e "${YELLOW}Assurez-vous que l'API est démarrée et accessible.${NC}"
    echo -e "${YELLOW}Nouvelle tentative dans 5 secondes... (CTRL+C pour annuler)${NC}"
    sleep 5
done

echo -e "${GREEN}✓ API accessible!${NC}"
echo ""

# Définir les métadonnées du test
echo -e "${YELLOW}Définition des métadonnées du test...${NC}"
TEST_PAYLOAD='{
  "test_id": "simulation_test",
  "date": "'$(date +%Y-%m-%d)'",
  "operator_name": "Test Script",
  "specimen_code": "SIM001",
  "dim_length": 100.0,
  "dim_height": 50.0,
  "dim_width": 25.0,
  "loading_mode": "compression",
  "sensor_spacing": 10.0,
  "ext_support_spacing": 20.0,
  "load_point_spacing": 15.0
}'

INFO_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "${BASE_URL}/api/test/info" \
  -H "Content-Type: application/json" \
  -d "$TEST_PAYLOAD")

HTTP_CODE=$(echo "$INFO_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" -eq 204 ]; then
  echo -e "${GREEN}✓ Métadonnées définies${NC}"
else
  echo -e "${RED}✗ Échec de la définition des métadonnées (HTTP $HTTP_CODE)${NC}"
  echo -e "${RED}Réponse: $(echo "$INFO_RESPONSE" | head -n-1)${NC}"
  exit 1
fi

# Démarrer le test
echo -e "${YELLOW}Démarrage du test...${NC}"
START_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "${BASE_URL}/api/test/start")

HTTP_CODE=$(echo "$START_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" -eq 204 ]; then
  echo -e "${GREEN}✓ Test démarré${NC}"
else
  echo -e "${RED}✗ Échec du démarrage du test (HTTP $HTTP_CODE)${NC}"
  echo -e "${RED}Réponse: $(echo "$START_RESPONSE" | head -n-1)${NC}"
  exit 1
fi

echo ""
echo -e "${BLUE}=== Début des requêtes ===${NC}"
echo -e "${BLUE}Endpoint: ${BASE_URL}/api/sensor/FORCE/data/history?window=${WINDOW}${NC}"
echo ""

# Compteur de requêtes
REQUEST_COUNT=0

# Fonction de nettoyage à l'arrêt
cleanup() {
    echo ""
    echo -e "${RED}Arrêt du script...${NC}"
    echo -e "${GREEN}Nombre total de requêtes: ${REQUEST_COUNT}${NC}"
    
    # Arrêter le test en cours
    echo -e "${YELLOW}Arrêt du test...${NC}"
    curl -s -X PUT "${BASE_URL}/api/test/stop" > /dev/null
    echo -e "${GREEN}✓ Test arrêté${NC}"
    
    exit 0
}

# Capturer CTRL+C pour nettoyer proprement
trap cleanup SIGINT SIGTERM

# Boucle infinie de requêtes
while true; do
    # Capturer le timestamp de début
    START_TIME=$(date +%s.%N)
    REQUEST_COUNT=$((REQUEST_COUNT + 1))
    
    # Effectuer la requête
    RESPONSE=$(curl -s "${BASE_URL}/api/sensor/FORCE/data/history?window=${WINDOW}")
    
    # Extraire le nombre de points retournés
    POINT_COUNT=$(echo "$RESPONSE" | jq '.list | length' 2>/dev/null || echo "0")
    
    # Afficher le résultat
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S.%3N')
    echo -e "${GREEN}[${TIMESTAMP}]${NC} Requête #${REQUEST_COUNT} - Points reçus: ${POINT_COUNT}"
    
    # Optionnel: afficher le premier et dernier point pour débug
    if [ "$POINT_COUNT" -gt 0 ]; then
        FIRST_POINT=$(echo "$RESPONSE" | jq -r '.list[0] | "\(.time):\(.value)"' 2>/dev/null)
        LAST_POINT=$(echo "$RESPONSE" | jq -r '.list[-1] | "\(.time):\(.value)"' 2>/dev/null)
        echo -e "  ${BLUE}Premier: ${FIRST_POINT}, Dernier: ${LAST_POINT}${NC}"
    fi
    
    # Calculer le temps écoulé et ajuster le sleep
    END_TIME=$(date +%s.%N)
    ELAPSED=$(echo "$END_TIME - $START_TIME" | bc)
    SLEEP_TIME=$(echo "$INTERVAL - $ELAPSED" | bc)
    
    # Sleep seulement si nécessaire (et si positif)
    if (( $(echo "$SLEEP_TIME > 0" | bc -l) )); then
        sleep "$SLEEP_TIME"
    fi
done
