#!/usr/bin/env bash
# Despliega la app del agente (Streamlit) en Azure App Service.
# Uso: bash infra/deploy_app.sh        (desde la raíz del repo, con `az login` hecho)
set -euo pipefail

RG="rg-dataknown-caso"
REGION="${REGION:-eastus2}"
SKU="${SKU:-B1}"                          # B1 (básico) o F1 (gratis, con límites de CPU)
PLAN="asp-dataknown-caso"
APP="${APP_NAME:-app-dataknown-caso}"     # debe ser único en Azure; se puede cambiar con APP_NAME=...
OPENAI="oai-dataknown-caso"
DEPLOYMENT="gpt-5.4-mini"

echo "1/6 Plan de App Service (Linux $SKU en $REGION)"
az appservice plan create -g "$RG" -n "$PLAN" -l "$REGION" --is-linux --sku "$SKU" -o none

echo "2/6 Web App con Python 3.12"
az webapp create -g "$RG" -p "$PLAN" -n "$APP" --runtime "PYTHON:3.12" -o none

echo "3/6 Variables de entorno (la key se lee de Azure, no del repo)"
ENDPOINT=$(az cognitiveservices account show -g "$RG" -n "$OPENAI" --query properties.endpoint -o tsv)
KEY=$(az cognitiveservices account keys list -g "$RG" -n "$OPENAI" --query key1 -o tsv)
az webapp config appsettings set -g "$RG" -n "$APP" -o none --settings \
    AZURE_OPENAI_ENDPOINT="$ENDPOINT" \
    AZURE_OPENAI_API_KEY="$KEY" \
    AZURE_OPENAI_DEPLOYMENT="$DEPLOYMENT" \
    SCM_DO_BUILD_DURING_DEPLOYMENT=true \
    WEBSITES_PORT=8000
unset KEY

echo "4/6 Comando de arranque y websockets (Streamlit los necesita)"
ALWAYS_ON=true; [ "$SKU" = "F1" ] && ALWAYS_ON=false      # el plan gratuito no permite always-on
az webapp config set -g "$RG" -n "$APP" -o none --web-sockets-enabled true --always-on "$ALWAYS_ON" \
    --startup-file "python -m streamlit run agent/app.py --server.port 8000 --server.address 0.0.0.0 --server.headless true"

echo "5/6 Paquete con lo mínimo para la app"
python - <<'EOF'
import zipfile
from pathlib import Path

archivos = (list(Path("agent").glob("*.py")) + list(Path("src").glob("*.py"))
            + list(Path("data/processed").glob("*.csv")) + [Path(".streamlit/config.toml")])
requisitos = "\n".join(["pandas", "numpy", "statsmodels", "openai", "python-dotenv",
                        "streamlit", "altair", "ddgs"]) + "\n"

with zipfile.ZipFile("app.zip", "w", zipfile.ZIP_DEFLATED) as z:
    for f in archivos:
        z.write(f, f.as_posix())
    z.writestr("requirements.txt", requisitos)   # versión ligera, sin jupyter ni scikit-learn
print(f"app.zip con {len(archivos) + 1} archivos")
EOF

echo "6/6 Subiendo el código (Azure instala las librerías; tarda unos minutos)"
az webapp deploy -g "$RG" -n "$APP" --src-path app.zip --type zip --async true -o none
rm app.zip

echo
echo "Listo: https://$APP.azurewebsites.net  (la primera carga puede tardar 1-2 minutos)"
