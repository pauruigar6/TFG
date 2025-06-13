#!/bin/bash
set -e

# 1. Clonar el repositorio (si aún no lo tienes)
if [ ! -d "TFG" ]; then
  git clone https://github.com/pauruigar6/TFG.git
fi
cd TFG

# 2. Actualizar e instalar dependencias del sistema
sudo apt update
sudo apt install -y virt-manager python3-venv python3-gi \
                   python3-libvirt gir1.2-gtk-3.0 pkexec

# 3. (Opcional) Crear y activar entorno virtual
python3 -m venv --system-site-packages venv
source venv/bin/activate

# 4. Preparar directorio de plantillas
mkdir -p ~/.local/share/virt-manager/templates
sudo chown "$USER":libvirt ~/.local/share/virt-manager/templates
chmod 770 ~/.local/share/virt-manager/templates

# 5. Asegurar usuario en el grupo libvirt
sudo usermod -aG libvirt "$USER"

echo "Instalación completada. Ahora puedes arrancar Virt-Manager en modo debug:"
echo "   cd TFG && ./virt-manager/virt-manager --debug"
