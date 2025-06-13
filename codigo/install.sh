#!/usr/bin/env bash
set -euo pipefail

# 1. Clonar el repositorio (si aún no existe)
if [ ! -d "virt-manager" ]; then
  git clone https://github.com/pauruigar6/TFG.git .
fi

# 2. Actualizar e instalar dependencias del sistema
sudo apt update
sudo apt install -y virt-manager python3-venv python3-gi python3-libvirt \
                   gir1.2-gtk-3.0 pkexec  # instalaciones básicas :contentReference[oaicite:2]{index=2}

# 3. Crear y activar entorno virtual Python
python3 -m venv --system-site-packages venv
source venv/bin/activate

# 4. Preparar directorio de plantillas
TEMPLATES_DIR="$HOME/.local/share/virt-manager/templates"
mkdir -p "$TEMPLATES_DIR"
sudo chown "$USER":libvirt "$TEMPLATES_DIR"
chmod 770 "$TEMPLATES_DIR"

# 5. Añadir usuario al grupo libvirt (si no está ya)
if ! id -nG "$USER" | grep -qw libvirt; then
  sudo usermod -aG libvirt "$USER"
  echo "→ Usuario añadido al grupo libvirt. Cierra sesión y vuelve a entrar."
fi

echo "Instalación completada. Ahora puedes compilar y ejecutar la extensión."
