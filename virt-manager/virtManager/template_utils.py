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
import time

# Carpeta donde se almacenan las plantillas (sin root, en tu home)
TEMPLATES_ROOT = os.path.expanduser("~/.local/share/virt-manager/templates")

# Ahora TEMPLATE_BASE ya apunta a tu home (sin root):
TEMPLATE_BASE = os.path.expanduser('~/.local/share/virt-manager/templates')

def copy_disk_with_permissions(src, dst):
        """
        Intenta copiar un archivo usando pkexec si no hay permisos como usuario normal.
        """
        import subprocess
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

def get_domain_by_name(vm_name):
    # Devuelve (dominio, uri) o (None, None)
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

class TemplateManager:
    def __init__(self, parent_window):
        self.parent = parent_window


    def convert_vm_to_template(self, vm_name):
        # --- Paso 0: asegurar que existe TEMPLATE_BASE ---
        try:
            os.makedirs(TEMPLATE_BASE, exist_ok=True)
        except Exception as e:
            self._show_error(f"No se pudo crear la carpeta de plantillas:\n{e}")
            return

        # --- Paso 1: crear subdirectorio para esta plantilla ---
        template_dir = os.path.join(TEMPLATE_BASE, vm_name)
        if os.path.isdir(template_dir):
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

        # --- Paso 2: volcar XML de la VM usando libvirt-session en lugar de virsh ---
        try:
            conn = libvirt.open("qemu:///session")
            if conn is None:
                raise RuntimeError("No se pudo abrir conexión de sesión a libvirt")
            dom, domain_uri = get_domain_by_name(vm_name)
            if dom is None:
                self._show_error(f"No se encontró ninguna VM llamada '{vm_name}' ni en sesión ni en sistema.")
                shutil.rmtree(template_dir)
                return
            xml_desc = dom.XMLDesc(0)
            conn.close()
        except Exception as e:
            self._show_error(f"Error al obtener el XML de '{vm_name}':\n{e}")
            shutil.rmtree(template_dir)
            return

        # Guardamos el XML en definition.xml
        xml_path = os.path.join(template_dir, 'definition.xml')
        try:
            with open(xml_path, 'w') as f_xml:
                f_xml.write(xml_desc)
        except Exception as e:
            self._show_error(f"No se pudo escribir definition.xml:\n{e}")
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

        disk_paths = []
        for disk in root.findall("./devices/disk"):
            source = disk.find("./source")
            if source is not None and 'file' in source.attrib:
                path = source.attrib['file']
                if path.endswith('.qcow2') and os.path.isfile(path):
                    disk_paths.append(path)

        if not disk_paths:
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
            except PermissionError:
                # Si falla por permisos, intentamos con pkexec (te pedirá la contraseña)
                try:
                    copy_disk_with_permissions(src, dst)
                    # Cambia el propietario al usuario actual
                    change_owner_to_user(dst)
                    copied_disks.append(dst)
                except Exception as e2:
                    self._show_error(f"No se pudo copiar el disco '{src}' ni con permisos elevados:\n{e2}")
                    shutil.rmtree(template_dir)
                    return
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
                # Ejecuta virt-customize con pkexec para acceso a kernel
                subprocess.check_call(["pkexec"] + cmd_clean)
            except subprocess.CalledProcessError as e:
                self._show_error(f"Error al limpiar /etc/machine-id en '{disk_img}':\n{e}")
                # No abortamos aquí; seguimos con el resto
        time.sleep(1) 

        # --- Paso 6: undefine de la VM en libvirt-session en lugar de virsh ---
        if domain_uri:
            try:
                conn = libvirt.open(domain_uri)
                dom = conn.lookupByName(vm_name)
                if dom.isActive():
                    dom.destroy()
                dom.undefine()
                conn.close()
            except libvirt.libvirtError as e:
                self._show_info(
                    f"Advertencia: no se pudo eliminar la definición de la VM '{vm_name}'.\n"
                    f"Puede que ya no exista o haya sido eliminada. Detalle:\n{e}"
                )
                
        # Éxito final
        self._show_info(
            f"La máquina '{vm_name}' se ha convertido en plantilla con éxito.\n"
            f"Puedes encontrarla en:\n{template_dir}"
        )
        return
    
        

    #
    # Métodos auxiliares para mostrar diálogos GTK (quedan igual)...
    #
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
    
    

