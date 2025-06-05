# TFG: Automatización de la creación de máquinas virtuales desde plantillas con Virt-Manager

## Descripción

Este proyecto es el Trabajo de Fin de Grado de Paula Ruiz Gardón.  
Consiste en una aplicación integrable con Virt-Manager que permite **automatizar la creación de máquinas virtuales (VMs) a partir de plantillas**, 
facilitando tanto la clonación como la gestión de dichas plantillas, todo desde una interfaz gráfica sencilla.

El objetivo es mejorar la eficiencia y la experiencia de usuario en la administración de entornos virtualizados con KVM/QEMU, 
aportando funcionalidades adicionales a Virt-Manager para usuarios técnicos y no técnicos.

---

## Características principales

- **Conversión de máquinas virtuales en plantillas**: Guarda la definición y los discos de una VM como plantilla reutilizable.
- **Creación rápida de nuevas máquinas a partir de plantillas**: Personaliza el nombre de la nueva VM desde un asistente gráfico.
- **Selección de imágenes de disco gestionadas por libvirt** (no rutas externas).
- **Gestión intuitiva y profesional**: Ventanas informativas y barras de progreso durante las operaciones largas.
- **Integración visual moderna**: Uso de GtkHeaderBar, iconos del sistema y diseño adaptado a Virt-Manager.

---

## Requisitos

- **Sistema operativo**: Linux (desarrollado y probado en Ubuntu 22.04/24.04)
- **Virt-Manager**: 4.1.0 o compatible
- **Python**: >=3.8
- **GTK+ 3** y PyGObject
- **libvirt** y python-libvirt
- **Dependencias adicionales**: `pkexec`, `getpass`, `shutil`, `subprocess`
- Acceso a pools de almacenamiento gestionados por libvirt

---

## Instalación

1. **Clona el repositorio:**

    ```bash
    git clone https://github.com/pauruigar6/TFG.git
    cd TFG
    ```

2. **Instala las dependencias del sistema** (en Ubuntu/Debian):

    ```bash
    sudo apt update
    sudo apt install virt-manager python3-venv python3-gi python3-libvirt gir1.2-gtk-3.0
    ```

3. **Activa un entorno virtual Python (`venv`):**

    ```bash
    source .venv/bin/activate
    ./virt-manager/virt-manager --debug
    ```

4. **Lanza Virt-Manager** y sigue las instrucciones del manual de usuario para usar la integración.


---

## Uso

- Desde Virt-Manager, encontrarás nuevas opciones para **convertir máquinas en plantillas** e **instanciar nuevas VMs a partir de plantillas**.
- Las plantillas se almacenan en `~/.local/share/virt-manager/templates`.
- Durante cualquier operación larga (clonación, conversión), se mostrarán **barras de progreso e información contextual**.
- Consulta el manual de usuario para detalles paso a paso.

---

## Documentación

La documentación se irá actualizando conforme avance el desarrollo.

---

## Vídeo de demostración

Los videos se irá actualizando conforme avance el desarrollo.

---

## Autoría

Proyecto desarrollado por **Paula Ruiz Gardón**  
Universidad de Sevilla  
Tutorizado por **Jose Antonio Pérez Castellano**

---

## Contacto

Para cualquier duda o sugerencia:

- GitHub: [https://github.com/pauruigar6](https://github.com/pauruigar6)

---

