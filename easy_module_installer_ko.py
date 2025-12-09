bl_info = {
    "name": "Easy Module Installer",
    "author": "JetishIE",
    "version": (1, 1),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Module Installer",
    "description": "Install and Manage Python modules via pip directly in Blender. Made for my students :)<br> after installation, open the sidebar",
    "warning": "",
    "wiki_url": "",
    "category": "Development",
}

import bpy
import subprocess
import sys
import os
import json

# --- Data Properties ---
class MIP_InstalledPackage(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name")
    version: bpy.props.StringProperty(name="Version")

# --- Operators ---

class MIP_OT_list_packages(bpy.types.Operator):
    """List installed pip packages"""
    bl_idname = "mip.list_packages"
    bl_label = "Refresh Package List"
    bl_description = "List all installed pip packages"

    def execute(self, context):
        python_exe = sys.executable
        # Use json format for reliable parsing
        cmd = [python_exe, "-m", "pip", "list", "--format=json"]
        
        try:
            # Startupinfo to hide console window on Windows during check_output
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.check_output(cmd, startupinfo=startupinfo)
            data = json.loads(result)
            
            # Clear and populate collection
            context.scene.mip_installed_packages.clear()
            
            for pkg in data:
                item = context.scene.mip_installed_packages.add()
                item.name = pkg['name']
                item.version = pkg['version']
                
            self.report({'INFO'}, f"Found {len(data)} packages")
        except subprocess.CalledProcessError as e:
            self.report({'ERROR'}, f"Failed to list packages: {e}")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
            return {'CANCELLED'}
            
        return {'FINISHED'}

class MIP_OT_install_package(bpy.types.Operator):
    """Install the specified Python package via pip"""
    bl_idname = "mip.install_package"
    bl_label = "Install Package"
    bl_description = "Install the specified package using pip"

    def execute(self, context):
        package_name = context.scene.mip_package_name.strip()
        
        if not package_name:
            self.report({'ERROR'}, "Please enter a package name")
            return {'CANCELLED'}

        python_exe = sys.executable
        cmd = [python_exe, "-m", "pip", "install", package_name]

        try:
            self.report({'INFO'}, f"Installing {package_name}...")
            # Use subprocess to call pip
            subprocess.check_call(cmd)
            self.report({'INFO'}, f"Successfully installed {package_name}")
            
            # Refresh list automatically
            bpy.ops.mip.list_packages()
            
        except subprocess.CalledProcessError:
            self.report({'ERROR'}, f"Failed to install {package_name}. Check console.")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        return {'FINISHED'}

class MIP_OT_uninstall_package(bpy.types.Operator):
    """Uninstall the selected package"""
    bl_idname = "mip.uninstall_package"
    bl_label = "Uninstall Package"
    bl_description = "Uninstall the selected package"

    def execute(self, context):
        scene = context.scene
        idx = scene.mip_installed_packages_index
        
        try:
            item = scene.mip_installed_packages[idx]
            package_name = item.name
        except IndexError:
            self.report({'ERROR'}, "No package selected")
            return {'CANCELLED'}

        python_exe = sys.executable
        # Auto-confirm uninstall with -y
        cmd = [python_exe, "-m", "pip", "uninstall", "-y", package_name]
        
        try:
            self.report({'INFO'}, f"Uninstalling {package_name}...")
            subprocess.check_call(cmd)
            self.report({'INFO'}, f"Successfully uninstalled {package_name}")
            
            # Refresh list
            bpy.ops.mip.list_packages()
            
        except subprocess.CalledProcessError:
            self.report({'ERROR'}, f"Failed to uninstall {package_name}")
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        return {'FINISHED'}

class MIP_OT_ensure_pip(bpy.types.Operator):
    """Ensure pip is installed"""
    bl_idname = "mip.ensure_pip"
    bl_label = "Ensure PIP"
    bl_description = "Ensure pip is available"

    def execute(self, context):
        python_exe = sys.executable
        try:
            subprocess.check_call([python_exe, "-m", "ensurepip", "--default-pip"])
            subprocess.check_call([python_exe, "-m", "pip", "install", "--upgrade", "pip"])
            self.report({'INFO'}, "PIP checked/installed successfully")
            bpy.ops.mip.list_packages()
        except Exception as e:
            self.report({'ERROR'}, f"Error installing PIP: {str(e)}")
            return {'CANCELLED'}
        return {'FINISHED'}

# --- UI ---

class MIP_UL_package_list(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.label(text=item.name, icon='PACKAGE')
            layout.label(text=item.version)
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='PACKAGE')

class MIP_PT_main_panel(bpy.types.Panel):
    """Creates a Panel in the View3D UI"""
    bl_label = "Module Installer"
    bl_idname = "MIP_PT_main_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Modules'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Installer Section
        box = layout.box()
        box.label(text="Install New Package:", icon='ADD')
        box.prop(scene, "mip_package_name", text="")
        
        row = box.row()
        row.scale_y = 1.3
        row.operator("mip.install_package", icon='IMPORT')
        
        layout.separator()

        # Manager Section
        box = layout.box()
        row = box.row()
        row.label(text="Installed Packages:", icon='TEXT')
        row.operator("mip.list_packages", text="", icon='FILE_REFRESH')
        
        row = box.row()
        row.template_list("MIP_UL_package_list", "", scene, "mip_installed_packages", scene, "mip_installed_packages_index", rows=5)
        
        row = box.row()
        sub = row.row()
        sub.scale_y = 1.2
        sub.enabled = len(scene.mip_installed_packages) > 0
        sub.operator("mip.uninstall_package", icon='TRASH', text="Uninstall Selected")

        layout.separator()
        
        # Utilities Section
        col = layout.column(align=True)
        col.label(text="Utilities:")
        col.operator("mip.ensure_pip", icon='PREFERENCES')
        col.operator("wm.console_toggle", text="Toggle Console")

# --- Registration ---

classes = (
    MIP_InstalledPackage,
    MIP_OT_list_packages,
    MIP_OT_install_package,
    MIP_OT_uninstall_package,
    MIP_OT_ensure_pip,
    MIP_UL_package_list,
    MIP_PT_main_panel
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    
    bpy.types.Scene.mip_package_name = bpy.props.StringProperty(
        name="Package Name",
        description="Name of the Python package",
        default=""
    )
    
    bpy.types.Scene.mip_installed_packages = bpy.props.CollectionProperty(type=MIP_InstalledPackage)
    bpy.types.Scene.mip_installed_packages_index = bpy.props.IntProperty(name="Index", default=0)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    
    del bpy.types.Scene.mip_package_name
    del bpy.types.Scene.mip_installed_packages
    del bpy.types.Scene.mip_installed_packages_index

if __name__ == "__main__":
    register()