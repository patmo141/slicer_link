'''
Created on Mar 2, 2017

@author: Patrick
'''
'''
https://pymotw.com/2/xml/etree/ElementTree/create.html
https://docs.python.org/2/library/xml.etree.elementtree.html
https://www.na-mic.org/Wiki/index.php/AHM2012-Slicer-Python
https://www.slicer.org/wiki/Documentation/Nightly/ScriptRepository
https://gist.github.com/ungi/4b0bd3a109bd98de054c66cc1ec6cfab
http://stackoverflow.com/questions/6597552/mathematica-write-matrix-data-to-xml-read-matrix-data-from-xml
'''
bl_info = {
    "name": "Blender Scene to Slicer",
    "author": "Patrick R. Moore",
    "version": (1, 0),
    "blender": (2, 78, 0),
    "location": "File > Export > Slicer (.xml)",
    "description": "Adds a new Mesh Object",
    "warning": "",
    "wiki_url": "",
    "category": "Import Export",
    }
#python
import os
import inspect

import bpy

#XML
from xml.etree import ElementTree as ET
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, Comment, ElementTree

#Blender
from bpy.types import Operator, AddonPreferences

from io_mesh_ply import export_ply

def get_settings():
    addons = bpy.context.user_preferences.addons
    stack = inspect.stack()
    for entry in stack:
        folderpath = os.path.dirname(entry[1])
        foldername = os.path.basename(folderpath)
        if foldername not in {'lib','addons'} and foldername in addons: break
    else:
        assert False, 'could not find non-"lib" folder'
    settings = addons[foldername].preferences
    return settings

#Preferences
class SlicerAddonPreferences(AddonPreferences):
    # this must match the addon name, use '__package__'
    # when defining this in a submodule of a python package.
    bl_idname = __name__
    self_dir = os.path.dirname(os.path.abspath(__file__))
    tmp_dir = os.path.join(self_dir, "slicer_module","tmp")
    tmpdir = bpy.props.StringProperty(name = "Temp Folder", default = tmp_dir, subtype = 'DIR_PATH')
    
    def draw(self,context):
        
        layout = self.layout
        row = layout.row()
        row.prop(self, "tmpdir")
        
def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def matrix_to_xml_element(mx):
    nrow = len(mx.row)
    ncol = len(mx.row[0])
    
    xml_mx = Element('matrix')
    
    for i in range(0,nrow):
        xml_row = SubElement(xml_mx, 'row')
        for j in range(0,ncol):
            mx_entry = SubElement(xml_row, 'entry')
            mx_entry.text = str(mx[i][j])
            
    return xml_mx

def material_to_xml_element(mat):
    
    
    xml_mat = Element('material')
    
    
    r = SubElement(xml_mat, 'r')
    r.text = str(round(mat.diffuse_color.r,4))
    g = SubElement(xml_mat, 'g')
    g.text = str(round(mat.diffuse_color.g,4))
    b = SubElement(xml_mat, 'b')
    b.text = str(round(mat.diffuse_color.b,4))
    
    return xml_mat

class SlicerPLYExport(bpy.types.Operator):
    """
    export selected objects mesh in local coords to
    stanford PLY (with colors)
    """
    bl_idname = "export.slicerply"
    bl_label = "Export Slicer Ply"
    
    overwrite = bpy.props.BoolProperty(name = "Overwrite", default = True)
    def execute(self,context):
        #check tmp dir for exchange file
        temp_dir = get_settings().tmpdir
        if temp_dir == '' or not os.path.isdir(temp_dir):
            self.report({'ERROR'}, 'Temp directory doesnt exist, set temp directory in addon preferences')
            return {'CANCELLED'}
        
        #clean old ply files from tmp dir
        for parent, dirnames, filenames in os.walk(temp_dir):
            for fn in filenames:
                if fn.lower().endswith('.ply'):
                    os.remove(os.path.join(parent, fn))
            
        for ob in context.selected_objects: #[TODO] object group managments
            #slicer does not like . in ob names
            if "." in ob.name:
                ob.name.replace(".","_")
                
            temp_file = os.path.join(temp_dir, ob.name + ".ply")
            if os.path.exists(temp_file):
                print('overwriting')
            
            me = ob.to_mesh(context.scene, True, 'PREVIEW')
            if not me:
                continue
            
            ret = export_ply.save_mesh(temp_file, me,
                    use_normals=False,
                    use_uv_coords=False,
                    use_colors=False,
                    )
            bpy.data.meshes.remove(me)
            
        return {'FINISHED'}
            
class SlicerXMLExport(bpy.types.Operator):
    """
    Export to the scene object names and transforms to XML
    """
    bl_idname = "export.slicerxml"
    bl_label = "Export Slicer XML"
    
    def execute(self,context):
        
        x_scene = Element('scene')
        
        for ob in context.scene.objects:
            xob = SubElement(x_scene, 'b_object')
            xob.set('name', ob.name)
            
            xmlmx = matrix_to_xml_element(ob.matrix_world)
            xob.extend([xmlmx])
            
            if len(ob.material_slots):
                mat = ob.material_slots[0].material
                xmlmat = material_to_xml_element(mat)
                xob.extend([xmlmat])
                print(prettify(xmlmat))
                
        #check tmp dir for exchange file
        temp_dir = get_settings().tmpdir
        if temp_dir == '' or not os.path.isdir(temp_dir):
            self.report({'ERROR'}, 'Temp directory doesnt exist, set temp directory in addon preferences')
            return {'CANCELLED'}
        temp_file = os.path.join(temp_dir,"blend_to_slicer.xml")
        if not os.path.exists(temp_file):
            my_file = open(temp_file, 'xb')
        else:
            my_file = open(temp_file,'wb')
        
        ElementTree(x_scene).write(my_file)
        my_file.close()
        
        return {'FINISHED'}
    
    
def register():
    bpy.utils.register_class(SlicerAddonPreferences)
    bpy.utils.register_class(SlicerXMLExport)
    bpy.utils.register_class(SlicerPLYExport)
    #bpy.utils.register_manual_map(SlicerXMLExport)
    #bpy.utils.register_manual_map(SlicerPLYExport)
    

def unregister():
    bpy.utils.unregister_class(SlicerXMLExport)
    bpy.utils.register_class(SlicerXMLExport)
    bpy.utils.register_class(SlicerPLYExport)
    #bpy.utils.unregister_manual_map(SlicerXMLExport)
    #bpy.utils.unregister_manual_map(SlicerPLYExport)
    
if __name__ == "__main__":
    register()