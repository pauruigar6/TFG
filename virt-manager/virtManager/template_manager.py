# -*- coding: utf-8 -*-
#
# template_manager.py: funciones para 'convertir en plantilla' e 'importar desde plantilla'
#
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import libvirt

# Carpeta base donde guardaremos plantillas:
TEMPLATE_BASE = os.path.expanduser('~/.local/share/virt-manager/templates')

class TemplateManager:
    def __init__(self, parent_window):
        """
        parent_window: referencia a la ventana principal de virt-manager (Gtk.Window),
                       usada para los diálogos de confirmación/progreso.
        """
        self.parent = parent_window

    def convert_vm_to_template(self, vm_name):
        """
        Convierte la VM con nombre vm_name en plantilla. Se realizan estos pasos:

          1. Crear ~/.local/share/virt-manager/templates/vm_name/ (ya existe o se crea).
          2. Hacer 'virsh dumpxml vm_name' y guardar el XML en definition.xml.
          3. Parsear el XML para encontrar rutas de discos .qcow2 y copiarlos al directorio de plantilla.
          4. Ejecutar virt-customize para limpiar /etc/machine-id en cada copia de disco.
          5. Hacer virsh undefine vm_name (destruir y desregistrar la VM).
          6. Mostrar diálogo informativo de éxito o error.
        """
        # --- Paso 0: asegurar que existe TEMPLATE_BASE ---
        try:
            os.makedirs(TEMPLATE_BASE, exist_ok=True)
        except Exception as e:
            self._show_error(f"No se pudo crear la carpeta de plantillas:\n{e}")
            return

        # --- Paso 1: crear subdirectorio para esta plantilla ---
        template_dir = os.path.join(TEMPLATE_BASE, vm_name)
        if os.path.isdir(template_dir):
            # Si ya existía, preguntar sobreescribir
            respuesta = self._ask_confirmation(
                f"Ya existe una plantilla llamada '{vm_name}'.\n"
                "¿Deseas sobrescribirla? Esto eliminará la anterior."
            )
            if not respuesta:
                return
            shutil.rmtree(template_dir)

        try:
            os.makedirs(template_dir)
        except Exception as e:
            self._show_error(f"No se pudo crear el subdirectorio de la plantilla:\n{e}")
            return

        # --- Paso 2: volcar XML de la VM ---
        xml_path = os.path.join(template_dir, 'definition.xml')
        cmd_dumpxml = ['virsh', 'dumpxml', vm_name]
        try:
            with open(xml_path, 'w') as f_xml:
                subprocess.check_call(cmd_dumpxml, stdout=f_xml)
        except subprocess.CalledProcessError as e:
            self._show_error(f"Error al volcar XML de '{vm_name}':\n{e}")
            shutil.rmtree(template_dir)
            return

        # --- Paso 3: parsear el XML para encontrar discos QCOW2 ---
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
        except Exception as e:
            self._show_error(f"Error al parsear el XML: {e}")
            shutil.rmtree(template_dir)
            return

        # Lista de rutas absolutas de discos .qcow2
        disk_paths = []
        # Recorremos cada <disk> en /domain/devices/disk
        for disk in root.findall("./devices/disk"):
            source = disk.find("./source")
            if source is not None and 'file' in source.attrib:
                path = source.attrib['file']
                if path.endswith('.qcow2') and os.path.isfile(path):
                    disk_paths.append(path)

        if not disk_paths:
            # Advertencia: la VM no tiene discos .qcow2
            self._show_info(
                f"La máquina '{vm_name}' no parece tener discos .qcow2 asociados.\n"
                "Se borrará la definición pero no se copiarán discos."
            )

        # --- Paso 4: copiar cada disco .qcow2 al directorio de plantilla ---
        copied_disks = []
        for src in disk_paths:
            nombre = os.path.basename(src)
            dst = os.path.join(template_dir, nombre)
            try:
                shutil.copy2(src, dst)
                copied_disks.append(dst)
            except Exception as e:
                self._show_error(f"No se pudo copiar el disco '{src}':\n{e}")
                shutil.rmtree(template_dir)
                return

        # --- Paso 5: limpiar /etc/machine-id en cada disco copiado ---
        for disk_img in copied_disks:
            cmd_clean = [
                'virt-customize', '-a', disk_img,
                '--run-command',
                "if [ -f /etc/machine-id ]; then echo '' > /etc/machine-id; fi"
            ]
            try:
                subprocess.check_call(cmd_clean)
            except subprocess.CalledProcessError as e:
                # Avisamos, pero no abortamos todo
                self._show_error(f"Error al limpiar /etc/machine-id en '{disk_img}':\n{e}")

        # --- Paso 6: undefine de la VM en libvirt ---
        try:
            conn = libvirt.open(None)
            dom = conn.lookupByName(vm_name)
            if dom.isActive():
                dom.destroy()
            dom.undefine()
            conn.close()
        except libvirt.libvirtError as e:
            self._show_error(f"Error al hacer 'undefine' de '{vm_name}':\n{e}")
            return

        # Éxito final
        self._show_info(
            f"La máquina '{vm_name}' se ha convertido en plantilla con éxito.\n"
            f"Puedes encontrarla en:\n{template_dir}"
        )
        return

    #
    # Métodos auxiliares para mostrar diálogos GTK
    #
    def _ask_confirmation(self, message):
        dlg = Gtk.MessageDialog(
            parent=self.parent,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=message
        )
        resp = dlg.run()
        dlg.destroy()
        return resp == Gtk.ResponseType.YES

    def _show_error(self, message):
        dlg = Gtk.MessageDialog(
            parent=self.parent,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dlg.run()
        dlg.destroy()

    def _show_info(self, message):
        dlg = Gtk.MessageDialog(
            parent=self.parent,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dlg.run()
        dlg.destroy()
