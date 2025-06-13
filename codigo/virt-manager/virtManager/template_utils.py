# -*- coding: utf-8 -*-
#
# template_utils.py: funciones para 'convertir en plantilla'
#
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import libvirt
import getpass
import threading
import time

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
        self.topwin = parent_window if isinstance(parent_window, Gtk.Window) else None
        self._progress_dialog = None
        self._progress_label = None
        self._progress_bar = None

    def convert_vm_to_template(self, vm_name, template_name=None):
        # Muestra la barra de progreso antes de lanzar el hilo
        GLib.idle_add(self._show_progress_bar_dialog, "Preparando conversión a plantilla…")
        def start_thread():
            threading.Thread(
                target=self._convert_vm_to_template_thread,
                args=(vm_name, template_name)
            ).start()
            return False
        GLib.idle_add(start_thread)

    def _show_progress_bar_dialog(self, mensaje_inicial):
        dialog = Gtk.Dialog(
            title="Convirtiendo en plantilla",
            transient_for=self.topwin,
            modal=True,
            destroy_with_parent=True,
        )
        dialog.set_deletable(False)
        dialog.set_resizable(False)
        dialog.set_border_width(16)

        vbox = dialog.get_content_area()
        label = Gtk.Label(label=mensaje_inicial)
        label.set_margin_bottom(12)
        progressbar = Gtk.ProgressBar()
        progressbar.set_show_text(True)
        progressbar.set_fraction(0.0)
        vbox.pack_start(label, False, False, 0)
        vbox.pack_start(progressbar, False, False, 0)
        dialog.show_all()

        self._progress_dialog = dialog
        self._progress_label = label
        self._progress_bar = progressbar

    def _update_progress(self, fraction, mensaje=None):
        if self._progress_bar:
            self._progress_bar.set_fraction(fraction)
            if mensaje:
                self._progress_bar.set_text(mensaje)
        if mensaje and self._progress_label:
            self._progress_label.set_text(mensaje)

    def _close_progress_dialog(self):
        if self._progress_dialog:
            self._progress_dialog.destroy()
            self._progress_dialog = None

    def _convert_vm_to_template_thread(self, vm_name, template_name=None):
        try:
            if not template_name:
                template_name = vm_name

            template_dir = os.path.join(TEMPLATES_ROOT, template_name)
            # Si la plantilla ya existe, mostrar error y salir
            if os.path.isdir(template_dir):
                GLib.idle_add(self._close_progress_dialog)
                GLib.idle_add(
                    self._show_error,
                    f"No se puede crear la plantilla '{template_name}' porque ya existe."
                )
                return

            GLib.idle_add(self._update_progress, 0.05, "Creando carpeta para la plantilla…")
            os.makedirs(template_dir)

            GLib.idle_add(self._update_progress, 0.15, "Obteniendo XML de la máquina virtual…")
            dom, domain_uri = get_domain_by_name(vm_name)
            if dom is None:
                raise RuntimeError(f"No se encontró ninguna VM llamada '{vm_name}' ni en sesión ni en sistema.")
            xml_desc = dom.XMLDesc(0)

            GLib.idle_add(self._update_progress, 0.25, "Analizando definición de la VM…")
            root = ET.fromstring(xml_desc)

            # Eliminar el elemento UUID sin confirmación
            elem = find_first_elem(root, 'uuid')
            if elem is not None:
                root.remove(elem)
            xml_desc = ET.tostring(root, encoding='unicode')

            disk_paths = []
            for disk in root.findall("./devices/disk"):
                if disk.get("device") == "disk" and disk.get("type") == "file":
                    source = disk.find("source")
                    if source is not None and 'file' in source.attrib:
                        path = source.attrib['file']
                        if os.path.isfile(path):
                            disk_paths.append(path)

            num_disks = len(disk_paths)
            for idx, src in enumerate(disk_paths):
                nombre = os.path.basename(src)
                dst = os.path.join(template_dir, nombre)
                mensaje = f"Convirtiendo en plantilla {idx+1}/{num_disks}: {nombre}…"
                progreso = 0.30 + 0.50 * ((idx+1)/max(num_disks,1))
                GLib.idle_add(self._update_progress, progreso, mensaje)
                try:
                    copy_disk_with_permissions(src, dst)
                    change_owner_to_user(dst)
                except Exception as e:
                    GLib.idle_add(self._close_progress_dialog)
                    GLib.idle_add(self._show_error, f"No se pudo copiar el disco '{src}' con permisos elevados:\n{e}")
                    shutil.rmtree(template_dir)
                    return

            GLib.idle_add(self._update_progress, 0.85, "Guardando definición XML…")
            xml_path = os.path.join(template_dir, 'definition.xml')
            with open(xml_path, 'w', encoding="utf-8") as f_xml:
                f_xml.write(xml_desc)

            GLib.idle_add(self._update_progress, 1.0, "¡Plantilla creada con éxito!")
            time.sleep(0.5)
            GLib.idle_add(self._close_progress_dialog)
            GLib.idle_add(
                self._show_info,
                f"La máquina '{vm_name}' se ha convertido en plantilla con éxito.\n"
                f"Puedes encontrarla en:\n{template_dir}"
            )
        except Exception as e:
            GLib.idle_add(self._close_progress_dialog)
            GLib.idle_add(self._show_error, str(e))
            if 'template_dir' in locals() and os.path.exists(template_dir):
                shutil.rmtree(template_dir)
            return

    # Métodos auxiliares para mostrar diálogos GTK (deben llamarse desde el hilo principal)
    def _show_error(self, message):
        parent = self.topwin
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
        parent = self.topwin
        dlg = Gtk.MessageDialog(
            parent=parent,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dlg.run()
        dlg.destroy()
