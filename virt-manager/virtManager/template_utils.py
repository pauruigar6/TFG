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
import getpass

# Carpeta donde se almacenan las plantillas (en el home, siempre sin root)
TEMPLATES_ROOT = os.path.expanduser("~/.local/share/virt-manager/templates")
os.makedirs(TEMPLATES_ROOT, exist_ok=True)

def find_first_elem(root, tag):
    for elem in root.iter():
        if elem.tag.endswith(tag):
            return elem
    return None

def get_domain_by_name(vm_name):
    # Busca la VM en ambas conexiones
    for uri in ["qemu:///session", "qemu:///system"]:
        try:
            conn = libvirt.open(uri)
            if conn is None:
                continue
            dom = conn.lookupByName(vm_name)
            conn.close()
            return dom, uri
        except libvirt.libvirtError:
            continue
    return None, None

def copy_disk_with_permissions(src, dst):
    cmd = ["pkexec", "cp", src, dst]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise Exception(f"Error copiando disco con permisos elevados:\n{res.stderr}")

def change_owner_to_user(dst):
    username = getpass.getuser()
    cmd = ["pkexec", "chown", f"{username}:{username}", dst]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise Exception(f"Error cambiando el propietario de '{dst}':\n{res.stderr}")

def convert_vm_to_template_dialog(parent_window, vm):
    manager = TemplateManager(parent_window)
    vm_name = vm.get_name()
    manager.convert_vm_to_template(vm_name)

class TemplateManager:
    def __init__(self, parent_window):
        self.parent = parent_window

    def convert_vm_to_template(self, vm_name, template_name=None):
        """
        Convierte una VM en plantilla, guardando definición y discos en HOME.
        Usa permisos elevados para copiar discos aunque estén fuera del HOME.
        """
        if not template_name:
            template_name = vm_name  # Por defecto, usa el nombre de la VM

        template_dir = os.path.join(TEMPLATES_ROOT, template_name)
        if os.path.isdir(template_dir):
            respuesta = self._ask_confirmation(
                f"Ya existe una plantilla llamada '{template_name}'.\n"
                "¿Deseas sobrescribirla? Esto eliminará la anterior."
            )
            if not respuesta:
                return
            shutil.rmtree(template_dir)

        try:
            os.makedirs(template_dir)
        except Exception as e:
            self._show_error(f"No se pudo crear la carpeta de la plantilla:\n{e}")
            return

        # --- Paso 2: Obtener XML de la VM desde ambas conexiones ---
        try:
            dom, domain_uri = get_domain_by_name(vm_name)
            if dom is None:
                raise RuntimeError(f"No se encontró ninguna VM llamada '{vm_name}' ni en sesión ni en sistema.")
            xml_desc = dom.XMLDesc(0)
        except Exception as e:
            self._show_error(f"Error al obtener el XML de '{vm_name}':\n{e}")
            shutil.rmtree(template_dir)
            return

        # --- Paso 3: Revisar discos (permitimos cualquiera, copiamos con permisos si hace falta) ---
        try:
            root = ET.fromstring(xml_desc)
        except Exception as e:
            self._show_error(f"Error al parsear el XML de '{vm_name}':\n{e}")
            shutil.rmtree(template_dir)
            return

        disk_paths = []
        for disk in root.findall("./devices/disk"):
            if disk.get("device") == "disk" and disk.get("type") == "file":
                source = disk.find("source")
                if source is not None and 'file' in source.attrib:
                    path = source.attrib['file']
                    if os.path.isfile(path):
                        disk_paths.append(path)

        # --- Paso 4: Copiar discos a la plantilla SIEMPRE usando pkexec ---
        for src in disk_paths:
            nombre = os.path.basename(src)
            dst = os.path.join(template_dir, nombre)
            try:
                copy_disk_with_permissions(src, dst)
                change_owner_to_user(dst)
            except Exception as e:
                self._show_error(f"No se pudo copiar el disco '{src}' con permisos elevados:\n{e}")
                shutil.rmtree(template_dir)
                return

        # --- Paso 5: Guardar el XML como definition.xml ---
        xml_path = os.path.join(template_dir, 'definition.xml')
        try:
            with open(xml_path, 'w', encoding="utf-8") as f_xml:
                f_xml.write(xml_desc)
        except Exception as e:
            self._show_error(f"No se pudo escribir definition.xml:\n{e}")
            shutil.rmtree(template_dir)
            return

        self._show_info(
            f"La máquina '{vm_name}' se ha convertido en plantilla con éxito.\n"
            f"Puedes encontrarla en:\n{template_dir}"
        )
        return

    # Métodos auxiliares para mostrar diálogos GTK (sin cambios)...
    def _ask_confirmation(self, message):
        parent = self.parent if isinstance(self.parent, Gtk.Window) else None
        dlg = Gtk.MessageDialog(
            parent=parent,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=message
        )
        resp = dlg.run()
        dlg.destroy()
        return resp == Gtk.ResponseType.YES

    def _show_error(self, message):
        parent = self.parent if isinstance(self.parent, Gtk.Window) else None
        dlg = Gtk.MessageDialog(
            parent=parent,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dlg.run()
        dlg.destroy()

    def _show_info(self, message):
        parent = self.parent if isinstance(self.parent, Gtk.Window) else None
        dlg = Gtk.MessageDialog(
            parent=parent,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dlg.run()
        dlg.destroy()
