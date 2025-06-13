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

## Estructura del proyecto

- **TFG/**: Carpeta raíz de entrega para el ZIP final 
  - **código/**: Código fuente y scripts de preparación 
    - `install.sh`: Script de instalación de dependencias y entorno 
    - `compila.txt`: Instrucciones de preparación del entorno 
    - `virt-manager/`: Código de la extensión GTK 
  - **ejecutable/**: Archivos listos para ejecución 
    - `ejecuta.txt`: Instrucciones de lanzamiento de la aplicación 
    - `virt-manager/`

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

## Instalación y preparación

1. **Navega al directorio de código** 
   ```bash
   cd código
   ```

2. **Da permisos de ejecución** 
   ```bash
   chmod +x install.sh
   ```

3. **Ejecuta el instalador** 
   ```bash
   ./install.sh
   ```
   Esto:
   - Actualiza repositorios e instala dependencias de sistema. 
   - Clona el repositorio (si no existe). 
   - Crea un entorno virtual Python (`venv/`). 
   - Prepara el directorio de plantillas en `~/.local/share/virt-manager/templates`. 
   - Añade tu usuario al grupo `libvirt` (si procede).

> **Importante**: Si se te añade al grupo `libvirt`, cierra sesión y vuelve a iniciar para aplicar los permisos.

4. **Consulta detalles de preparación** 
   ```text
   código/compila.txt
   ```

---
## Ejecución

1. **Accede al paquete ejecutable** 
   ```bash
   cd ejecutable
   ```

2. **Activa el entorno virtual** 
   ```bash
   source ../código/venv/bin/activate
   ```

3. **Comprueba permisos del lanzador** 
   ```bash
   ls -l virt-manager/virt-manager
   # Debe mostrar -rwxr-xr-x
   ```

4. **Arranca Virt-Manager con la extensión** 
   ```bash
   cd virt-manager
   ./virt-manager --debug
   ```
   - El modo `--debug` muestra logs detallados en la terminal.

5. **Usa la extensión desde la GUI** 
   - **Convertir VM en plantilla**: clic derecho sobre una VM → **Convertir en plantilla** 
   - **Crear VM desde plantilla**: clic en Archivo → Nueva máquina virtual → **Importar desde plantilla** → selecciona plantilla → ajusta nombre → **Finalizar**.

6. **Verificaciones post-importación** 
   - Si hay errores, revisa:
     ```bash
     ~/.cache/virt-manager/virt-manager.log
     ```

7. **Cierra la aplicación** 
   - Cierra la ventana o presiona `Ctrl+C` en la terminal. 
   - Para salir del entorno virtual:
     ```bash
     deactivate
     ```

---
## Documentación

- **Compilación/preparación**: `código/compila.txt` 
- **Ejecución**: `ejecutable/ejecuta.txt` 

---
## Autoría

- **Paula Ruiz Gardón** 
- Universidad de Sevilla 
- Tutora: **Jose Antonio Pérez Castellano**

---
## Contacto

- GitHub: [pauruigar6](https://github.com/pauruigar6) 
