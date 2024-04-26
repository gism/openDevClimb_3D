bl_info = {
    "name": "SketchStyle",
    "author": "Chipp Walters, Alexander Glazyrin (aka algl1002)",
    "version": (2, 0, 1),
    "blender": (2, 80, 0),
    "location": "",
    "description": "",
    "category": "Render"
}


import os
import bpy
import json
import idprop
import platform
import webbrowser
import subprocess
from bpy.app.handlers import persistent
from mathutils import Color
from bpy.utils import (register_class, unregister_class, previews, script_path_user)
from bpy.types import (PropertyGroup, Scene, Panel, Object, AddonPreferences,
                       Image, SpaceView3D, Operator, WindowManager,
                       FreestyleLineSet, FreestyleLineStyle,
                       LineStyleGeometryModifier, LineStyleGeometryModifier_BackboneStretcher)
from bpy.props import (IntProperty, FloatProperty, PointerProperty, BoolProperty,
                       EnumProperty, StringProperty, FloatVectorProperty, CollectionProperty)
 
                       
# PROPERTIES OF THE ADDON
NUMBER_OF_LINESETS = 10
# PROPERTIES OF THE ADDON

# Returns path to folder with the addon
def getBasePath():
    p = bpy.utils.script_path_user()
    p = os.path.join(p, "addons", "sketch_style")
    p += os.sep
    return p
    
def setPath(path):
    osname = platform.system()
    if osname == 'Windows':
        return path
    else:
        return path.replace("\\", "/")
#

def getSettings():
    settings = bpy.context.window_manager.sketch_style
    return settings

def getDefaultSettings():
    settings = bpy.context.window_manager.sketch_style_default
    return settings


def set_panel_props():
    props = getSettings()
    #
    bpy.context.view_layer.update()
    #
    mat = bpy.data.materials['cw_SketchStyle']
    node = mat.node_tree.nodes.get("Ambient Occlusion")
    props.ms_ao = node.inputs[1].default_value
    #props.ms_ao.default = node.inputs[1].default_value
    #
    w = bpy.data.worlds['SketchStyle']
    node = w.node_tree.nodes.get("Brightness")
    props.ws_brightness = node.inputs[1].default_value   
    #props.ws_brightness.default = node.inputs[1].default_value   
    #
    try:
        props.rs_samples = bpy.data.scenes["SketchStyle"].view_layers["Viewport"].samples
    except:
        props.rs_samples = bpy.data.scenes["SketchStyle"].view_layers[0].samples
    #props.rs_samples.default = bpy.data.scenes["SketchStyle"].view_layers["Viewport"].samples
    
def set_props():
    props = getSettings()
    try:
        mat = bpy.data.materials['cw_SketchStyle']
        node = mat.node_tree.nodes.get("Ambient Occlusion")
        node.inputs[1].default_value = props.ms_ao
        #
        w = bpy.data.worlds['SketchStyle']
        node = w.node_tree.nodes.get("Brightness")
        node.inputs[1].default_value = props.ws_brightness
        #
        for layer in bpy.data.scenes["SketchStyle"].view_layers:
            layer.samples = props.rs_samples
        #
        bpy.data.scenes["SketchStyle"].cycles.device = "CPU"
    except:
        pass

def remove_bad_materials():
    props = getSettings()
    #
    for i in bpy.data.materials:
        if "cw_SketchStyle" in i.name and i.name != "cw_SketchStyle":
            i.user_clear()
            bpy.data.materials.remove(i)
    #
    for i in bpy.data.worlds:
        if "SketchStyle." in i.name:
            i.user_clear()
            bpy.data.worlds.remove(i)
    #
    if bpy.data.scenes.get("SketchStyle"):
        if bpy.data.worlds.get("SketchStyle"):
            bpy.data.scenes.get("SketchStyle").world = bpy.data.worlds.get("SketchStyle")
            
def deselect_all(scene):
    props = getSettings()
    for obj in scene.objects:
        obj.select_set(False)

def load_thumbnails(current_script_file):
    props = getSettings()
    directory = os.path.join(os.path.dirname(current_script_file), "settings")
    bpy.context.window_manager.sketch_style.my_previews_dir = directory

    # cleanup already existing thumbnails
    bpy.context.window_manager.sketch_style.thumbnails.clear()
    
    image_paths = []
    blend_paths = []
    if directory and os.path.exists(directory):
        # Scan the directory for png and blend files
        for fn in os.listdir(directory):
            if fn.lower().endswith(".png"):
                image_paths.append(fn)
            elif fn.lower().endswith(".blend"):
                blend_paths.append(fn)
            else:
                pass

    for i, name in enumerate(blend_paths):
        #adding a new thumbnail to the thumb collection property only for blend files with relevant images in the same folder
        relevant_image_name = name[:-6] + ".png"
        if relevant_image_name in image_paths:
            thumbnail = props.thumbnails.add()
            thumbnail.index = i
            thumbnail.name = name[:-6] + ".png"

    return props.thumbnails

def get_blend_path(image_name):
    abpath = getBasePath()
    blend_name = image_name[:-4] + ".blend"
    blend_path = os.path.join(abpath,"settings", blend_name)
    return blend_path

def enum_previews_from_directory_items(self, context):
    """EnumProperty callback"""
    enum_items = []

    if context is None:
        return enum_items

    #loading the thumbnails names from the created collection props instead of the folder
    path = getBasePath()
    thumbnails = load_thumbnails(path)

    props = getSettings()
    directory = props.my_previews_dir

    # Get the preview collection (defined in register func).
    pcoll = preview_collections["main"]

    if directory == pcoll.my_previews_dir:
        return pcoll.current_thumb
    
    if thumbnails:
        for i, thumbnail in enumerate(thumbnails):
            # generates a thumbnail preview for a file.
            name = thumbnail.name
            filepath = os.path.join(directory, name)
            icon = pcoll.get(name)
            if not icon:
                thumb = pcoll.load(name, filepath, 'IMAGE')
            else:
                thumb = pcoll[name]
            enum_items.append((name, name[:-3] + "blend", "", thumb.icon_id, i))

    pcoll.current_thumb = enum_items
    pcoll.my_previews_dir = directory
    return pcoll.current_thumb

def open_file_explorer(path):
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])

# UPDATER FUNCTIONS
# --------------------------------------------------------------------------- 
# Updater for Scene mode radio button
def updater_scene_mode(self, context):
    abpath = getBasePath()
    props = self
    if self.initial_scene == "":
        self.initial_scene = bpy.data.scenes[0].name 
    # Switch between scenes depending on button state		
    if self.mode == "NORMAL":
        bpy.context.window.scene = bpy.data.scenes[self.initial_scene]
        #
        for obj in bpy.data.scenes["SketchStyle"].objects:
            try:
                if obj.material_slots[0].material != bpy.data.materials["cw_SketchStyle"]:
                    obj["sketchstyle_keep_mat"] = True
                else:
                    obj["sketchstyle_keep_mat"] = False
                for i in range(len(obj.material_slots)):
                    mat_slot = obj.material_slots[i]
                    try:
                        mat_slot.material = obj["sketchstyle_mats_to_restore"][str(i)]
                    except:
                        pass
            except:
                pass
        #
    else:
        if not bpy.data.scenes.get("SketchStyle"):	
            if bpy.data.scenes.get("SketchStyle"):
                bpy.ops.scene.delete({"scene": bpy.data.scenes["SketchStyle"]})
            #if bpy.data.materials.get("cw_SketchStyle"):
            #    bpy.data.materials.remove(bpy.data.materials["cw_SketchStyle"])
            if bpy.data.worlds.get("SketchStyle"):
                bpy.data.worlds.remove(bpy.data.worlds["SketchStyle"])
            #					
            load_settings(os.path.join(abpath, "sketch_style", "sketchstyle_default.blend"))
            deselect_all(bpy.data.scenes["SketchStyle"])
        bpy.context.window.scene = bpy.data.scenes["SketchStyle"]
        props.mode = "SKETCH" 
        #
        if not bpy.data.materials.get("cw_SketchStyle", None):
            path = os.path.join(abpath, "sketch_style", "sketchstyle_default.blend", "Material")
            name = "cw_SketchStyle"
            bpy.ops.wm.append(filename=name, directory=path)
                
        for obj in bpy.data.scenes["SketchStyle"].objects:
            if obj.get("sketchstyle_mats_to_restore"):
                for i in range(len(obj.material_slots)):
                    mat_slot = obj.material_slots[i]
                    if not obj["sketchstyle_keep_mat"]:
                        mat_slot.material = bpy.data.materials["cw_SketchStyle"]
                    else:
                        mat_slot.material = obj["sketchstyle_mats_to_restore"][str(i)]
        #
    remove_bad_materials()

# Updater for Render Device  
def updater_render_device(self, context):
    props = getSettings()
    try:
        if props.render_device == "0":
            bpy.data.scenes["SketchStyle"].cycles.device = "CPU"
        else:
            bpy.data.scenes["SketchStyle"].cycles.device = "GPU"
    except:
        print(props.render_device, "device type is not supported!")

# Material Settings: Color
def updater_ms_color(self, context):
    props = getSettings()
    mat = bpy.data.materials['cw_SketchStyle']
    node = mat.node_tree.nodes.get("Ambient Occlusion")
    col = props.ms_color
    col = [col[0], col[1], col[2], 1]
    node.inputs[0].default_value = col
    
# Updater for Material Settings: AO Distance
def updater_ms_ao(self, context):
    props = getSettings()
    mat = bpy.data.materials['cw_SketchStyle']
    node = mat.node_tree.nodes.get("Ambient Occlusion")
    node.inputs[1].default_value = props.ms_ao
    
# World Settings: BG Color
def updater_ws_bg_color(self, context):
    props = getSettings()
    w = bpy.data.worlds['SketchStyle']
    node = w.node_tree.nodes.get("Background")
    col = props.ws_bg_color
    col = [col[0], col[1], col[2], 1]
    node.inputs[0].default_value = col
    
# Updater for World Settings: Brightness
def updater_ws_brightness(self, context):
    props = getSettings()
    w = bpy.data.worlds['SketchStyle']
    node = w.node_tree.nodes.get("Brightness")
    node.inputs[1].default_value = props.ws_brightness  

def updater_ws_brightness_color(self, context):
    props = getSettings()
    w = bpy.data.worlds['SketchStyle']
    node = w.node_tree.nodes.get("Brightness")
    col = props.ws_brightness_color
    col = [col[0], col[1], col[2], 1]
    node.inputs[0].default_value = col
    
# Updater for Render Settings: Samples
def updater_rs_samples(self, context):
    props = getSettings()
    for layer in bpy.data.scenes["SketchStyle"].view_layers:
        layer.samples = props.rs_samples
        
# Updater Render Settings: Use Denoising
def updater_rs_denoising(self, context):
    props = getSettings()
    for layer in bpy.data.scenes["SketchStyle"].view_layers:
        layer.cycles.use_denoising = props.rs_use_denoising
            
# Render Settings: View Map Cache
def updater_view_map_cache(self, context):
    props = getSettings()
    for layer in bpy.data.scenes["SketchStyle"].view_layers:
        layer.freestyle_settings.use_view_map_cache = props.rs_view_map_cache

def update_active_index(self, context):
    #change the current thumbnail according to the active index value
    props = self
    thumbnails = props.thumbnails
    current_thumb = props.current_thumb
    for thumb in thumbnails:
        if current_thumb == thumb.name:
            active_index = thumb.index
            bpy.context.window_manager.sketch_style.active_index = active_index

    return

# LINE SETS
# LS 1
for i in range(NUMBER_OF_LINESETS):
    si = str(i + 1)
    #
    a = '''
def updater_ls_{}_use(self, context):
    props = getSettings()
    for layer in bpy.data.scenes["SketchStyle"].view_layers:
        lineset = layer.freestyle_settings.linesets[props.ls_{}_name]
        lineset.show_render = props.ls_{}_use
    '''.format(si, si, si)
    exec(a)
    #
    a = '''
def updater_ls_{}_alpha(self, context):
    props = getSettings()
    for layer in bpy.data.scenes["SketchStyle"].view_layers:
        linestyle = layer.freestyle_settings.linesets[props.ls_{}_name].linestyle
        linestyle.alpha = props.ls_{}_alpha
    '''.format(si, si, si)
    exec(a)
    #
    a = '''
def updater_ls_{}_thickness(self, context):
    props = getSettings()
    for layer in bpy.data.scenes["SketchStyle"].view_layers:
        linestyle = layer.freestyle_settings.linesets[props.ls_{}_name].linestyle
        linestyle.thickness = props.ls_{}_thickness
    '''.format(si, si, si)
    exec(a)
    #
    a = '''
def updater_ls_{}_extend_lines(self, context):
    props = getSettings()
    for layer in bpy.data.scenes["SketchStyle"].view_layers:
        linestyle = layer.freestyle_settings.linesets[props.ls_{}_name].linestyle
        linestyle.geometry_modifiers["Backbone Stretcher"].backbone_length = props.ls_{}_extend_lines
    '''.format(si, si, si)
    exec(a)
    #
    a = '''
def updater_ls_{}_color(self, context):
    props = getSettings()
    for layer in bpy.data.scenes["SketchStyle"].view_layers:
        linestyle = layer.freestyle_settings.linesets[props.ls_{}_name].linestyle
        col = props.ls_{}_color
        linestyle.color = col
    '''.format(si, si, si)
    exec(a)

# ---------------------------------------------------------------------------      
# UPDATER FUNCTIONS


# SOME FUNCTIONS
# ---------------------------------------------------------------------------  
# Creates a line set with given <name> and params
def load_settings(settings_path):
    abpath = getBasePath()
    props = getSettings()
    #
    if bpy.context.scene.name != "SketchStyle":
        props.initial_scene = bpy.context.scene.name
    else:
        if props.initial_scene == "":
            props.initial_scene = "Scene"
    # Load the SketchStyle scene from settings file
    if True:
        if bpy.data.scenes.get("SketchStyle"):
            bpy.ops.scene.delete({"scene": bpy.data.scenes["SketchStyle"]})
            
    with bpy.data.libraries.load(settings_path) as (data_from, data_to):
        for attr in dir(data_to):
            if attr in ["scenes"]:
                setattr(data_to, attr, getattr(data_from, attr))
                break
    # Take only some properties that we need, then remove the scene
    # so we create a linked scene that later will be filled with 
    # properties from scene loaded from settings file and renamed to SketchStyle
    bpy.ops.scene.new(type='LINK_COPY')
    scene = bpy.context.scene
    scene.name = "SketchStyle_Linked"
    # Copy neccessary properties
    bpy.context.scene.render.engine = 'CYCLES'
    #
    scene.render.use_freestyle = True
    scene.render.line_thickness_mode = 'RELATIVE'
    #
    scene.view_settings.view_transform = 'Standard'
    #
    if props.render_device == "0":
        scene.cycles.device = "CPU"
    else:
        scene.cycles.device = "GPU"
    #
    ls_i = 0
    #
    for i in range(NUMBER_OF_LINESETS):
        setattr(props, "ls_{}_name".format(str(i + 1)), "")
        
    # SET SOME PROPERTIES THAT DO NOT DEPEND ON LAYER
    samples = bpy.data.scenes["SketchStyle"].view_layers["Viewport"].samples
    
    mat = bpy.data.materials["cw_SketchStyle"]
    use_denoising = bpy.data.scenes["SketchStyle"].view_layers["Viewport"].cycles.use_denoising
    use_view_map_cache = bpy.data.scenes["SketchStyle"].view_layers["Viewport"].freestyle_settings.use_view_map_cache
    
    # Material Settings: Color
    node = mat.node_tree.nodes.get("Ambient Occlusion")
    col = node.inputs[0].default_value
    col = [col[0], col[1], col[2]]
    setattr(props, "ms_color", col)
    #SketchStyle_DefaultProps["ms_color"] = col
    setattr(getDefaultSettings(), "ms_color", col)
        
    # Material Settings: AO
    node = mat.node_tree.nodes.get("Ambient Occlusion")
    setattr(props, "ms_ao", node.inputs[1].default_value)  # here we set actual property
    #SketchStyle_DefaultProps["ms_ao"] = node.inputs[1].default_value  # here - default property
    setattr(getDefaultSettings(), "ms_ao", node.inputs[1].default_value)
        
    # World Settings: BG Color
    w = bpy.data.worlds['SketchStyle']
    node = w.node_tree.nodes.get("Background")
    col = node.inputs[0].default_value
    col = [col[0], col[1], col[2]]
    setattr(props, "ws_bg_color", col)
    #SketchStyle_DefaultProps["ws_bg_color"] = col
    setattr(getDefaultSettings(), "ws_bg_color", col)
        
    # World Settings: Brightness
    w = bpy.data.worlds['SketchStyle']
    node = w.node_tree.nodes.get("Brightness")
    setattr(props, "ws_brightness", node.inputs[1].default_value)
    #SketchStyle_DefaultProps["ws_brightness"] = node.inputs[1].default_value
    setattr(getDefaultSettings(), "ws_brightness", node.inputs[1].default_value)
        
    # World Settings: Brightness color
    col = node.inputs[0].default_value
    col = [col[0], col[1], col[2]]
    setattr(props, "ws_brightness_color", col)
    #SketchStyle_DefaultProps["ws_brightness_color"] = col
    setattr(getDefaultSettings(), "ws_brightness_color", col)
        
    # Render Settings: Samples
    setattr(props, "rs_samples", samples)
    #SketchStyle_DefaultProps["rs_samples"] = samples
    setattr(getDefaultSettings(), "rs_samples", samples)
        
    # Render Settings: View Map Cache
    setattr(props, "rs_view_map_cache", use_view_map_cache)
    #SketchStyle_DefaultProps["rs_view_map_cache"] = use_view_map_cache
    setattr(getDefaultSettings(), "rs_view_map_cache", use_view_map_cache)
        
    # Render Settings: Use Denoising
    setattr(props, "rs_use_denoising", use_denoising)
    #SketchStyle_DefaultProps["rs_use_denoising"] = use_denoising
    setattr(getDefaultSettings(), "rs_use_denoising", use_denoising)
    # SET SOME PROPERTIES THAT DO NOT DEPEND ON LAYER
    
    
    if not bpy.data.materials.get("cw_SketchStyle", None):
        default_path = os.path.join(abpath, "sketch_style", "sketchstyle_default.blend", "Material")
        name = "cw_SketchStyle"
        bpy.ops.wm.append(filename=name, directory=path)
    #
    for obj in scene.objects:
        if not obj.get("sketchstyle_mats_to_restore"):
            obj["sketchstyle_mats_to_restore"] = {}
            obj["sketchstyle_keep_mat"] = False
            for i in range(len(obj.material_slots)):
                mat_slot = obj.material_slots[i]
                obj["sketchstyle_mats_to_restore"][str(i)] = mat_slot.material
    
    #
    for layer in scene.view_layers:
        layer.samples = samples
        #layer.material_override = mat
        layer.cycles.use_denoising = use_denoising
        layer.freestyle_settings.use_view_map_cache = use_view_map_cache
        layer.freestyle_settings.use_smoothness = False
        
        # Remove all linessets from the scene
        freestyle = layer.freestyle_settings
        for lineset in freestyle.linesets:
            freestyle.linesets.remove(lineset)
        # Now load linesets from the settings file
        freestyle_loaded = bpy.data.scenes["SketchStyle"].view_layers["Viewport"].freestyle_settings
        #
        for ls in freestyle_loaded.linesets:
            if ls_i < NUMBER_OF_LINESETS:
                # Just copy settings for all linesets and linestyles from loaded scene to current
                lineset = freestyle.linesets.new(ls.name)
                lineset.show_render = ls.show_render
                lineset.select_contour = ls.select_contour
                lineset.select_crease = ls.select_crease
                lineset.select_edge_mark = ls.select_edge_mark
                lineset.select_external_contour = ls.select_external_contour
                lineset.select_material_boundary = ls.select_material_boundary
                lineset.select_ridge_valley = ls.select_ridge_valley
                lineset.select_silhouette = ls.select_silhouette
                lineset.select_suggestive_contour = ls.select_suggestive_contour
                lineset.select_border = ls.select_border
                #
                lineset.edge_type_negation = ls.edge_type_negation
                lineset.edge_type_combination = ls.edge_type_combination
                #
                lineset.visibility = ls.visibility
                lineset.qi_start = ls.qi_start
                lineset.qi_end = ls.qi_end
                #
                lineset.select_by_visibility = ls.select_by_visibility
                lineset.select_by_edge_types = ls.select_by_edge_types
                lineset.select_by_face_marks = ls.select_by_face_marks
                lineset.select_by_collection = ls.select_by_collection
                lineset.select_by_image_border = ls.select_by_image_border
                #
                lineset.face_mark_negation = ls.face_mark_negation
                lineset.face_mark_condition = ls.face_mark_condition
                #
                lineset.collection_negation = ls.collection_negation
                lineset.collection = ls.collection
                # Set linestyle for lineset
                lineset.linestyle = ls.linestyle
                
                # Set properties of the panel
                ls_prefix = "ls_" + str(ls_i + 1) + "_"
                
                name = ls.name
                
                linestyle = ls.linestyle
                
                alpha = linestyle.alpha
                thickness = linestyle.thickness
                try:
                    extend = linestyle.geometry_modifiers["Backbone Stretcher"].backbone_length
                except:
                    bpy.ops.scene.freestyle_geometry_modifier_add(type='BACKBONE_STRETCHER')
                    linestyle.geometry_modifiers["Backbone Stretcher"].backbone_length = 0
                    extend = 0
                    
                line_color = linestyle.color
                
                setattr(props, ls_prefix + "name", name)
                #SketchStyle_DefaultProps[ls_prefix + "name"] = name
                setattr(getDefaultSettings(), ls_prefix + "name", name)
                
                setattr(props, ls_prefix + "alpha", alpha)
                #SketchStyle_DefaultProps[ls_prefix + "alpha"] = alpha
                setattr(getDefaultSettings(), ls_prefix + "alpha", alpha)
                
                setattr(props, ls_prefix + "thickness", thickness)
                #SketchStyle_DefaultProps[ls_prefix + "thickness"] = thickness
                setattr(getDefaultSettings(), ls_prefix + "thickness", thickness)
                
                setattr(props, ls_prefix + "extend_lines", extend)
                #SketchStyle_DefaultProps[ls_prefix + "extend_lines"] = extend
                setattr(getDefaultSettings(), ls_prefix + "extend_lines", extend)
                
                setattr(props, ls_prefix + "color", line_color)
                setattr(getDefaultSettings(), ls_prefix + "color", line_color)
                #
                ls_i += 1
            else:
                break
        ls_i = 0
    #
    bpy.data.scenes.remove(bpy.data.scenes["SketchStyle"])
    scene.name = "SketchStyle"
    #
    remove_bad_materials()
    set_panel_props()
    # Set custom properties where old materials of objects will be stored (for EEVEE purposes)
    for obj in bpy.data.scenes["SketchStyle"].objects:
        obj["sketchstyle_mats_to_restore"] = {}
        for i in range(len(obj.material_slots)):
            mat_slot = obj.material_slots[i]
            obj["sketchstyle_mats_to_restore"][str(i)] = mat_slot.material
            mat_slot.material = bpy.data.materials["cw_SketchStyle"]
    #
    props.ms_manual_override = "OVERRIDE"
    
def reset_to_default():
    props = getSettings()
    #
    props_to_not_reset = ["initial_scene", "mode", "render_device", "ms_manual_override"]
    for i in range(NUMBER_OF_LINESETS):
        props_to_not_reset.append("ls_{}_name".format(str(i + 1)))

    for prop in SketchStyle_Props.__dict__["__annotations__"]:
        if not prop in props_to_not_reset:
            if getattr(getDefaultSettings(), prop, None):
                new_attr = getattr(getDefaultSettings(), prop, None)
                setattr(props, prop, new_attr)
            else:
                getSettings().property_unset(prop)
    
    if bpy.data.scenes.get("SketchStyle"):
        for layer in bpy.data.scenes.get("SketchStyle").view_layers:
            for i in layer.freestyle_settings.linesets:
                i.show_render = True
    
# ---------------------------------------------------------------------------  
# SOME FUNCTIONS


# PROPERTIES
# ---------------------------------------------------------------------------  
class SketchStyle_LineSet(PropertyGroup):
    name: StringProperty(name="", default="")
    alpha: FloatProperty(name="Alpha", 
                         default=0.66, 
                         min=0,
                         max=1)
    thickness: FloatProperty(name="Thickness", 
                         default=2.0, 
                         min=0,
                         max=5) 
    extend_lines: FloatProperty(name="Extend Lines", 
                         default=0, 
                         min=0,
                         max=100) 
                
# Storing default properties
#SketchStyle_DefaultProps = {
#    "ws_brightness": 0
#}
             
# Stroing default properties to then be able to reset props correctly
class SketchStyle_DefaultProps(PropertyGroup):
    # Line Sets settings
    for i in range(NUMBER_OF_LINESETS):
        si = str(i + 1)
        #
        a = '''
ls_{}_name: StringProperty(default="")
ls_{}_use: BoolProperty(name="", default=True, update=updater_ls_{}_use)
        '''.format(si, si, si)
        exec(a)
        #
        a = '''
ls_{}_alpha: FloatProperty(name="Alpha", 
                         default=0.66, 
                         min=0,
                         max=1,
                         update=updater_ls_{}_alpha)
ls_{}_thickness: FloatProperty(name="Thickness", 
                         default=2.0, 
                         min=0,
                         max=30,
                         update=updater_ls_{}_thickness) 
ls_{}_extend_lines: FloatProperty(name="Extend Lines", 
                         default=0, 
                         min=0,
                         max=100,
                         update=updater_ls_{}_extend_lines)
ls_{}_color: FloatVectorProperty(name="",
                         default=[0,0,0],
                         min=0.0,
                         max=1.0,
                         subtype="COLOR",
                         update=updater_ls_{}_color)
        '''.format(si, si, si, si, si, si, si, si)
        exec(a)
        
        # Material settings
    ms_color: FloatVectorProperty(name="",
        default=[0,0,0],
        min=0.0,
        max=1.0,
        subtype="COLOR",
        update=updater_ms_color)
    ms_ao: FloatProperty(name="Distance",
        default=1.0,
        min=0.0,
        max=50.0,
        precision=1,
        update=updater_ms_ao)
        
    # World settings
    ws_bg_color: FloatVectorProperty(name="",
        default=[0,0,0],
        min=0.0,
        max=1.0,
        subtype="COLOR",
        update=updater_ws_bg_color)
    
    ws_brightness: FloatProperty(name="Brightness",
        default=0.5,
        min=0.0,
        max=50.0,
        precision=1,
        update=updater_ws_brightness)
    ws_brightness_color: FloatVectorProperty(name="",
        default=[0,0,0],
        min=0.0,
        max=1.0,
        subtype="COLOR",
        update=updater_ws_brightness_color)
        
    # Render settings
    rs_samples: IntProperty(name="Samples",
        default=20,
        min=0,
        max=2000,
        update=updater_rs_samples)
        
    rs_view_map_cache: BoolProperty(name="View Map Cache",
        default=False,
        update=updater_view_map_cache)
        
    rs_use_denoising: BoolProperty(name="Use Denoising",
        default=True,
        update=updater_rs_denoising)

# definition of a thumbnail entry        
class ThumbEntry(bpy.types.PropertyGroup):
    name : StringProperty(
        name="Thumbnail file name"
    )
    index : IntProperty(
        name= "Index of thumbnail entry"
    )
               
# Storing actual properties
class SketchStyle_Props(PropertyGroup):
    initial_scene: StringProperty(name="")
    settings_filepath: StringProperty(subtype="FILE_PATH", default=os.sep + "sketchstyle_default.blend")
    #
    render_device: EnumProperty(name="Render device", 
                                items=[("0", "CPU" "", "CPU device to use for rendering", 0),
                                      ("1", "GPU" "", "GPU device to use for rendering", 1)], 
                                update=updater_render_device)
    
    mode: EnumProperty(name="Mode", 
                       items=[("NORMAL", "Normal", "Switches to the main scene", "", 0),
                              ("SKETCH", "Sketch", "Creates and/or switches to the SketchStyle scene", "", 1)], 
                       default="NORMAL", update=updater_scene_mode)

    #
    for i in range(NUMBER_OF_LINESETS):
        si = str(i + 1)
        #
        a = '''
ls_{}_name: StringProperty(default="")
ls_{}_use: BoolProperty(name="", default=True, update=updater_ls_{}_use)
        '''.format(si, si, si)
        exec(a)
        #
        a = '''
ls_{}_alpha: FloatProperty(name="Alpha", 
                         default=0.66, 
                         min=0,
                         max=1,
                         update=updater_ls_{}_alpha)
ls_{}_thickness: FloatProperty(name="Thickness", 
                         default=2.0, 
                         min=0,
                         max=30,
                         update=updater_ls_{}_thickness) 
ls_{}_extend_lines: FloatProperty(name="Extend Lines", 
                         default=0, 
                         min=0,
                         max=100,
                         update=updater_ls_{}_extend_lines)
ls_{}_color: FloatVectorProperty(name="",
                         default=[0,0,0],
                         min=0.0,
                         max=1.0,
                         subtype="COLOR",
                         update=updater_ls_{}_color)
        '''.format(si, si, si, si, si, si, si, si)
        exec(a)
    
    ms_color: FloatVectorProperty(name="",
        default=[0.0,0.0,0.0],
        min=0.0,
        max=1.0,
        subtype="COLOR",
        update=updater_ms_color)
    ms_ao: FloatProperty(name="Distance",
        default=1.0,
        min=0.0,
        max=50.0,
        precision=1,
        update=updater_ms_ao)
        
    # World settings
    ws_bg_color: FloatVectorProperty(name="",
        default=[0,0,0],
        min=0.0,
        max=1.0,
        subtype="COLOR",
        update=updater_ws_bg_color)
    
    ws_brightness: FloatProperty(name="Brightness",
        default=0.5,
        min=0.0,
        max=50.0,
        precision=1,
        update=updater_ws_brightness)
    ws_brightness_color: FloatVectorProperty(name="",
        default=[0,0,0],
        min=0.0,
        max=1.0,
        subtype="COLOR",
        update=updater_ws_brightness_color)
    #
    rs_samples: IntProperty(name="Samples",
        default=20,
        min=0,
        max=2000,
        update=updater_rs_samples)
        
    rs_view_map_cache: BoolProperty(name="View Map Cache",
        default=False,
        update=updater_view_map_cache)
        
    rs_use_denoising: BoolProperty(name="Use Denoising",
        default=True,
        update=updater_rs_denoising)
    
    # properties for thumbnails functionality
    my_previews_dir : StringProperty(
        name="Folder Path",
        subtype='DIR_PATH',
        default=""
    )

    current_thumb : EnumProperty(
        items = enum_previews_from_directory_items,
        update= update_active_index,
    )

    active_index : IntProperty(
        name="Index of current_thumb",
    )

    thumbnails : CollectionProperty(
        type=ThumbEntry
    )

    style_name : StringProperty(
        name = "Current SketchStyle name"
    )


# TOOLTIPS FOR PROPERTIES
# ----------------------------------------------
# Descriptions for properties
descriptions = {
    'ms_color': 'Color for all objects in the scene',
    'ms_ao': 'Ambient Occlusion distance. Larger is darker',
    
    
    'ws_bg_color': 'Color of the background',
    'ws_brightness': 'Adjusts overall scene brightness. Larger is brighter',
    'ws_brightness_color': 'Adjusts scene lighting color',
    
    
    'rs_samples': 'Number of Cycles render samples to use',
    'rs_view_map_cache': 'Saves time test rendering when there is long Mesh Loading and you are NOT changing the camera view. Turn off for final renders',
    'rs_use_denoising': 'Toggles ON/OFF Denoising'
}

for i in range(NUMBER_OF_LINESETS):
    pr = 'ls_{}_'.format(str(i + 1))
    descriptions[pr + 'use'] = 'Toggles ON/OFF Line Setting'
    descriptions[pr + 'alpha'] = 'Adjusts line transparency: 1 = no transparency'
    descriptions[pr + 'thickness'] = 'Adjusts relative line thickness'
    descriptions[pr + 'extend_lines'] = 'Adjusts length of lines to extend past intersections. 5.0 is a good number'
    descriptions[pr + 'color'] = 'Adjusts stroke color'
# ----------------------------------------------
# TOOLTIPS FOR PROPERTIES


    
# Add descriptions to the properties
for k, v in descriptions.items():
    SketchStyle_Props.__dict__['__annotations__'][k][1]['description'] = v
# ---------------------------------------------------------------------------
# PROPERTIES

    
# OPERATORS
# -----------------------------------------------	
class Override_O_Operator(Operator):
    bl_idname  = "object.override_o"						
    bl_label   = "Override Materials"
    bl_description = "Override Materials"				
    bl_options = {'REGISTER', 'UNDO'} 
    
    def execute(self, context):
        abpath = getBasePath()
        props = getSettings()
        scene = bpy.data.scenes["SketchStyle"]
        # Find selected objects, if no objects are selected then use all objects
        objs_selected = []
        for obj in scene.objects:
            if obj.select_get():
                objs_selected.append(obj)
        #
        if len(objs_selected) == 0:
            objs_selected = scene.objects
        #
        if not bpy.data.materials.get("cw_SketchStyle", None):
            default_path = os.path.join(abpath, "sketch_style", "sketchstyle_default.blend", "Material")
            name = "cw_SketchStyle"
            bpy.ops.wm.append(filename=name, directory=path)
        #
        for obj in scene.objects:
            if not obj.get("sketchstyle_mats_to_restore"):
                obj["sketchstyle_mats_to_restore"] = {}
                obj["sketchstyle_keep_mat"] = False
            try:
                if obj.material_slots[0].material != bpy.data.materials["cw_SketchStyle"]:
                    for i in range(len(obj.material_slots)):
                        mat_slot = obj.material_slots[i]
                        obj["sketchstyle_mats_to_restore"][str(i)] = mat_slot.material
            except:
                pass
        #
        for obj in objs_selected:
            obj["sketchstyle_keep_mat"] = False
            for i in range(len(obj.material_slots)):
                mat_slot = obj.material_slots[i]
                mat_slot.material = bpy.data.materials["cw_SketchStyle"]
        #
        return {'FINISHED'}	
    
class Override_M_Operator(Operator):
    bl_idname  = "object.override_m"						
    bl_label   = "Use Original Materials"
    bl_description = "Use Original Materials"				
    bl_options = {'REGISTER', 'UNDO'} 
    
    def execute(self, context):
        abpath = getBasePath()
        props = getSettings()
        scene = bpy.data.scenes["SketchStyle"]
        # Find selected objects, if no objects are selected then use all objects
        objs_selected = []
        for obj in scene.objects:
            if obj.select_get():
                objs_selected.append(obj)
        #
        if len(objs_selected) == 0:
            objs_selected = scene.objects
        #
        if not bpy.data.materials.get("cw_SketchStyle", None):
            default_path = os.path.join(abpath, "sketch_style", "sketchstyle_default.blend", "Material")
            name = "cw_SketchStyle"
            bpy.ops.wm.append(filename=name, directory=path)
        #
        for obj in scene.objects:
            if not obj.get("sketchstyle_mats_to_restore"):
                obj["sketchstyle_mats_to_restore"] = {}
                obj["sketchstyle_keep_mat"] = False
            try:
                if obj.material_slots[0].material != bpy.data.materials["cw_SketchStyle"]:
                    for i in range(len(obj.material_slots)):
                        mat_slot = obj.material_slots[i]
                        obj["sketchstyle_mats_to_restore"][str(i)] = mat_slot.material
            except:
                pass
        #
        for obj in objs_selected:
            obj["sketchstyle_keep_mat"] = True
            for i in range(len(obj.material_slots)):
                mat_slot = obj.material_slots[i]
                mat_slot.material = obj["sketchstyle_mats_to_restore"][str(i)]
        #
        return {'FINISHED'}	
        
class RE_Cycles_Operator(Operator):					     					
    bl_idname  = "object.render_engine_cycles"						
    bl_label   = "Switch to Cycles"
    bl_description = "Switch to Cycles"				
    bl_options = {'REGISTER', 'UNDO'}  
    
    def execute(self,context):	
        bpy.context.scene.render.engine = 'CYCLES'
        return {'FINISHED'}	

class RE_Eevee_Operator(Operator):					     					
    bl_idname  = "object.render_engine_eevee"						
    bl_label   = "Switch to EEVEE"
    bl_description = "Switch to EEVEE"				
    bl_options = {'REGISTER', 'UNDO'}  
    
    def execute(self,context):	
        bpy.context.scene.render.engine = 'BLENDER_EEVEE'
        return {'FINISHED'}	

class Reset_All_Operator(Operator):					     					
    bl_idname  = "object.reset_all"						
    bl_label   = "Reset All Values to Default"
    bl_description = "Loads default settings"				
    bl_options = {'REGISTER', 'UNDO'}  					
    
    def execute(self,context):	
        props = getSettings()
        #	
        reset_to_default()
        return {'FINISHED'}	
    
class Remove_SS_Scene_Operator(Operator):					     					
    bl_idname  = "object.remove_ss_scene"						
    bl_label   = "Remove SketchStyle Scene"
    bl_description = "Remove SketchStyle Scene"				
    bl_options = {'REGISTER', 'UNDO'}  					
    
    @classmethod
    def poll(self, context):
        if bpy.data.scenes.get("SketchStyle"):
            return True
        else:
            return False
    
    def execute(self,context):	
        props = getSettings()
        #
        bpy.ops.scene.delete({"scene": bpy.data.scenes["SketchStyle"]})
        #
        return {'FINISHED'}	
    
class Help_Operator(Operator):					     					
    bl_idname  = "object.sketch_style_help"						
    bl_label   = "Go to Page With Documentation"	
    bl_description = "Link to online documentation"				
    bl_options = {'REGISTER', 'UNDO'}  					
    
    def execute(self,context):		
        props = getSettings()
        #
        url="docs.google.com/document/d/1I3rJkSmhKgb45QhE17RAgnm2dubJz0NYObsLGXnLi4M"					
        #chrome_path = "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
        try:
            #webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
            #webbrowser.get('chrome').open(url)
            webbrowser.open(url)
        except Exception as e:
            bpy.ops.wm.url_open(url=url)
        return {'FINISHED'}	
    
class Export_All_Operator(Operator):					     					
    bl_idname  = "object.ss_export_all"						
    bl_label   = "Export All Settings"		
    bl_description = "Export all settings to .blend file (to do so you firstly need to save current file you are working in)"			
    bl_options = {'REGISTER', 'UNDO'}  	
    
    filepath: StringProperty(subtype="FILE_PATH")				
    
    @classmethod
    def poll(self, context):
        if bpy.data.scenes.get("SketchStyle"):
            if bpy.data.filepath.strip() == "":
                return False
            else:
                return True
    
    def execute(self,context):	
        abpath = getBasePath()	
        props = getSettings()
        #
        on = ""
        for i in bpy.data.scenes["SketchStyle"].objects:
            try:
                if i.material_slots[0].material != bpy.data.materials["cw_SketchStyle"]:
                    for j in range(len(i.material_slots)):
                        mat_slot = i.material_slots[j]
                        i["sketchstyle_mats_to_restore"][str(i)] = mat_slot.material
                        mat_slot.material = bpy.data.materials["cw_SketchStyle"]
                        
                        mat_slot = obj.material_slots[i]
                        mat_slot.material = obj["sketchstyle_mats_to_restore"][str(i)]
            except:
                continue
        #
        bpy.ops.wm.save_mainfile(filepath=bpy.data.filepath)
        #
        path = os.path.join(abpath, "sketch_style", "sketchstyle_exported.py")
        default_path = os.path.join(abpath, "sketch_style", "sketchstyle_exported.blend")
        
        # CHANGE IF DOES NOT WORK
        path_to_save = self.filepath
        
        if not "sketch_style_exported" in path_to_save:
            if not '.blend' in path_to_save:
                path_to_save += '.blend'
            
            lines_append = [
                "\n",
                "\n",
                "bpy.ops.wm.open_mainfile(filepath=r'" + default_path + "') \n",
                "load_settings(r'" + bpy.data.filepath + "') \n",
                "bpy.ops.wm.save_as_mainfile(filepath=r'" + path_to_save + "')"
            ]
            
            with open(path, "r") as file:
                lines = file.readlines()
                for line in lines:
                    if "bpy.ops.wm.open_mainfile" in line:
                        lines = lines[:-5]
                        break
                with open(path, "w") as file_save:
                    lines.extend(lines_append)
                    file_save.writelines(lines)
            #
            blender_path = bpy.app.binary_path
            #
            start_b_process = blender_path + ' --background --python "' + path + '"'
            os.system(start_b_process)					
            #
            self.report({'INFO'}, 'Settings were exported successfully!') 
            return {'FINISHED'}	
        else:
            self.report({'INFO'}, 'ERROR, style was not exported because the name of exporting file can NEVER be "sketch_style_exported"! Choose another name and try again.')
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
class Load_All_Operator(Operator):					     					
    bl_idname  = "object.ss_load_all"						
    bl_label   = "Load All Settings"	
    bl_description = "Choose .blend file to load settings from"				
    bl_options = {'REGISTER', 'UNDO'}  	
    
    directory: StringProperty(subtype="FILE_PATH")
    filepath: StringProperty(subtype="FILE_PATH")
    
    def execute(self,context):
        props = getSettings()
        #
        if bpy.data.scenes.get("SketchStyle"):
            bpy.ops.scene.delete({"scene": bpy.data.scenes["SketchStyle"]})
        if bpy.data.materials.get("cw_SketchStyle"):
            bpy.data.materials.remove(bpy.data.materials["cw_SketchStyle"])
        if bpy.data.worlds.get("SketchStyle"):
            bpy.data.worlds.remove(bpy.data.worlds["SketchStyle"])
        #					
        load_settings(self.filepath)
        #
        bpy.context.window.scene = bpy.data.scenes["SketchStyle"]
        props.mode = "SKETCH"
        deselect_all(bpy.data.scenes["SketchStyle"])
        return {'FINISHED'}

    def invoke(self, context, event):
        abpath = getBasePath()
        self.directory = abpath + os.sep + "settings" + os.sep
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

class SS_OT_next_thumb(bpy.types.Operator):
    """Change style to the next one in the styles list"""
    bl_idname = "object.next_thumb"
    bl_label = "Next Style"

    @classmethod
    def poll(cls, context):
        props = getSettings()
        thumbnails = props.thumbnails
        active_index = props.active_index
        if active_index + 1 == len(thumbnails):
            return False

        return not len(thumbnails) == 0

    def execute(self, context):
        props = getSettings()
        current_thumb = props.current_thumb
        active_index = props.active_index
        thumbnails = props.thumbnails
        thumbs_count = len (thumbnails)
        
        if active_index +1 < thumbs_count:
            current_thumb = [th.name for th in thumbnails if th.index == active_index + 1][0]

        bpy.context.window_manager.sketch_style.current_thumb = current_thumb
        return {'FINISHED'}

class SS_OT_previous_thumb(bpy.types.Operator):
    """Change style to the previous one in the styles list"""
    bl_idname = "object.previous_thumb"
    bl_label = "Previous Style"

    @classmethod
    def poll(cls, context):
        props = getSettings()
        thumbnails = props.thumbnails
        active_index = props.active_index
        if active_index == 0:
            return False

        return not len(thumbnails) == 0

    def execute(self, context):
        props = getSettings()
        current_thumb = props.current_thumb
        active_index = props.active_index
        thumbnails = props.thumbnails
        thumbs_count = len (thumbnails)
        
        if active_index > 0:
            current_thumb = [th.name for th in thumbnails if th.index == active_index - 1][0]

        bpy.context.window_manager.sketch_style.current_thumb = current_thumb
        return {'FINISHED'}

class SS_OT_load_ss_setting(bpy.types.Operator):
    """Load selected sketch style setting"""
    bl_idname = "object.load_ss_setting"
    bl_label = "Load SKETCH STYLE setting"
    bl_options = {'REGISTER', 'UNDO'} 

    @classmethod
    def poll(cls, context):
        props = getSettings()
        thumbnails = props.thumbnails
        return not len(thumbnails) == 0

    def execute(self, context):
        props = getSettings()
        blend_path = get_blend_path(props.current_thumb)
        props = getSettings()
        #
        if bpy.data.scenes.get("SketchStyle"):
            bpy.ops.scene.delete({"scene": bpy.data.scenes["SketchStyle"]})
        if bpy.data.materials.get("cw_SketchStyle"):
            bpy.data.materials.remove(bpy.data.materials["cw_SketchStyle"])
        if bpy.data.worlds.get("SketchStyle"):
            bpy.data.worlds.remove(bpy.data.worlds["SketchStyle"])
        #
        load_settings(blend_path) #pass the thumbs menu selection to this function
        #
        bpy.context.window.scene = bpy.data.scenes["SketchStyle"]
        props.mode = "SKETCH"
        deselect_all(bpy.data.scenes["SketchStyle"])
        
        return {'FINISHED'}

class SS_OT_open_presets_folder(bpy.types.Operator):
    """Open presets folder in system file browser"""
    bl_idname = "object.open_presets_folder"
    bl_label = "Open Presets Folder"

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        base_path = getBasePath()
        settings_folder_path = os.path.join(base_path, "settings")
        open_file_explorer(settings_folder_path)
        return {'FINISHED'}
# -----------------------------------------------
# OPERATORS
    
    
# PANEL
# ---------------------------------------------------------------------------
class SketchStyle_Panel_Main(Panel):
    bl_idname      = "SKETCHSTYLE_PT_Main"				
    bl_label       = "SKETCH STYLE Render"
    bl_category    = "Sketch Style"						
    bl_space_type  = "VIEW_3D"							
    bl_region_type = "UI"
    
    def draw(self, context):
        props = getSettings()
        #
        lay = self.layout
        lay.prop(props, "mode", expand=True)
        
        if props.mode == "SKETCH" and bpy.context.scene.render.engine == 'CYCLES':
            lay.label(text="Render device")
            lay.prop(props, "render_device", expand=True)
        lay.operator("render.render", text="RENDER")

class SketchStyle_Panel_Line(Panel):
    bl_idname 	   = "SKETCHSTYLE_PT_Linesettings"
    bl_label 	   = "Line settings"
    bl_category    = "Sketch Style"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id   = 'SKETCHSTYLE_PT_Main'
    
    @classmethod
    def poll(cls, context):
        props = getSettings()
        if props.mode == "SKETCH":
            return True
        return False
    
    def draw(self, context):
        props = getSettings()
        #
        lay = self.layout
        #
        if not bpy.data.scenes.get("SketchStyle"):
            lay.label(text="Press Sketch to start")
        else:
            for i in range(NUMBER_OF_LINESETS):
                si = str(i + 1)
                #
                a = '''
if getattr(props, "ls_{}_name") != "":
    row = lay.row().split(factor=0.1)
    col1, col2 = row.column(), row.column()
    #
    col1.prop(props, "ls_{}_use")
    col2.label(text=getattr(props, "ls_{}_name"))
    if props.ls_{}_use:
        col2.prop(props, "ls_{}_thickness")
        col2.prop(props, "ls_{}_alpha")
        col2.prop(props, "ls_{}_extend_lines")
        col2.prop(props, "ls_{}_color")
'''.format(si, si, si, si, si, si, si, si)
                exec(a)           

class SketchStyle_Panel_Material(Panel):
    bl_idname 	   = "SKETCHSTYLE_PT_Materialsettings"
    bl_label 	   = "Material settings"
    bl_category    = "Sketch Style"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id   = 'SKETCHSTYLE_PT_Main'
    
    @classmethod
    def poll(cls, context):
        props = getSettings()
        if props.mode == "SKETCH":
            return True
        return False
    
    def draw(self, context):
        props = getSettings()
        #
        #if props.mode == "SKETCH":
        lay = self.layout
        #
        row = lay.row().split(factor=0.1)
        col1, col2 = row.column(), row.column()
        #
        col1.label()
        #
        row = col2.row()
        row.operator("object.override_o", text="Override")
        row.operator("object.override_m", text="Materials")
        #
        col2.label(text="Color")
        col2.prop(props, "ms_color")
                
        col2.label(text="Ambient Occlusion")
        col2.prop(props, "ms_ao")
        
class SketchStyle_Panel_World(Panel):
    bl_idname 	   = "SKETCHSTYLE_PT_Worldsettings"
    bl_label 	   = "World settings"
    bl_category    = "Sketch Style"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id   = 'SKETCHSTYLE_PT_Main'
    
    @classmethod
    def poll(cls, context):
        props = getSettings()
        if props.mode == "SKETCH":
            return True
        return False
    
    def draw(self, context):
        props = getSettings()
        #
        lay = self.layout
        #
        row = lay.row().split(factor=0.1)
        col1, col2 = row.column(), row.column()
        #
        col1.label()
        #
        col2.label(text="Background color")
        col2.prop(props, "ws_bg_color")
        
        col2.label(text="Brightness color")
        col2.prop(props, "ws_brightness_color")
        col2.prop(props, "ws_brightness")
        
class SketchStyle_Panel_Render(Panel):
    bl_idname 	   = "SKETCHSTYLE_PT_Rendersettings"
    bl_label 	   = "Render settings"
    bl_category    = "Sketch Style"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id   = 'SKETCHSTYLE_PT_Main'
    
    @classmethod
    def poll(cls, context):
        props = getSettings()
        if props.mode == "SKETCH":
            return True
        return False
    
    def draw(self, context):
        props = getSettings()
        #
        lay = self.layout
        #
        row = lay.row().split(factor=0.1)
        col1, col2 = row.column(), row.column()
        #
        col1.label()
        #
        row = col2.row()
        row.operator("object.render_engine_cycles", text="Cycles")
        row.operator("object.render_engine_eevee", text="Eevee")
        
        if bpy.context.scene.render.engine == 'CYCLES':
            col2.prop(props, "rs_samples")
            
        col2.prop(props, "rs_view_map_cache")
        
        if bpy.context.scene.render.engine == 'CYCLES':
            col2.prop(props, "rs_use_denoising")
        
class SketchStyle_Panel_Last(Panel):
    bl_idname      = "SKETCHSTYLE_PT_Last"				
    bl_label       = "SKETCH STYLE Utilities"
    bl_category    = "Sketch Style"						
    bl_space_type  = "VIEW_3D"							
    bl_region_type = "UI"
    
    def draw(self, context):
        props = getSettings()
        #
        lay = self.layout
        #
        row = lay.row()

        if props.mode == "NORMAL":
            #the previews interface
            sub = row.row(align=True)
            sub.scale_y = 6
            sub.operator('object.previous_thumb', text='', icon='TRIA_LEFT')

            row.template_icon_view(props, "current_thumb", show_labels=True)

            sub = row.row(align=True)
            sub.scale_y = 6
            sub.operator('object.next_thumb', text='', icon='TRIA_RIGHT')

            row = lay.row()
            sub = row.row(align=True)
            sub.alignment = 'CENTER'
            label_text = bpy.context.window_manager.sketch_style.current_thumb[:-4].replace("_", " ").capitalize()
            sub.label(text=label_text)

            row = lay.row()
            row.operator("object.load_ss_setting")
            row.scale_y = 1.2
            row = lay.row()
            row = lay.row()

            row = lay.row()
            row.operator("object.ss_load_all", text="LOAD")
        else:
            row.operator("object.reset_all", text="RESET ALL")
        row.operator("object.ss_export_all", text="EXPORT")
        
        if props.mode == "NORMAL":
            lay.operator("object.remove_ss_scene", text="Delete SketchStyle Scene")
            row = lay.row()
            row.operator("object.open_presets_folder")

        
        row = lay.row()
        split = row.split()
        col = split.column()
        col = split.column()
        
        col.operator("object.sketch_style_help", text="HELP")
        
# ---------------------------------------------------------------------------
# PANEL

    
# CLASS REGISTRATION
# ---------------------------------------------------------------------------
# creating the previews dictionary
preview_collections = {}

classes_to_reg = (ThumbEntry, SketchStyle_Props, SketchStyle_LineSet, SketchStyle_DefaultProps,

                  SketchStyle_Panel_Main, SketchStyle_Panel_Line, 
                  SketchStyle_Panel_Material, SketchStyle_Panel_World,
                  SketchStyle_Panel_Render, SketchStyle_Panel_Last,
                  
                  Reset_All_Operator, Override_O_Operator, Override_M_Operator,
                  Help_Operator, Export_All_Operator, Load_All_Operator,
                  RE_Cycles_Operator, RE_Eevee_Operator, Remove_SS_Scene_Operator,
                  SS_OT_next_thumb, SS_OT_previous_thumb, SS_OT_load_ss_setting,
                  SS_OT_open_presets_folder
                  )

def register():
    for cl in classes_to_reg:
        register_class(cl)

    WindowManager.sketch_style = PointerProperty(type=SketchStyle_Props)
    WindowManager.sketch_style_default = PointerProperty(type=SketchStyle_DefaultProps)

    #for the thumbnails preview functionality
    pcoll = bpy.utils.previews.new()
    pcoll.my_previews_dir = ""
    pcoll.current_thumb = ()
    preview_collections["main"] = pcoll

def unregister():
    del WindowManager.sketch_style
    del WindowManager.sketch_style_default

    for cl in classes_to_reg:
        unregister_class(cl)

    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()

    
    

    
 
    
# Saves addon props and default props in a file
def save_props(mode):
    def write_file(prop_group, name):
        if bpy.data.texts.get(name):
            text = bpy.data.texts[name]
            bpy.data.texts.remove(text)
        bpy.ops.text.new()
        text = bpy.data.texts["Text"]
        text.name = name
        text.write("settings = { \n")
        for prop in prop_group.items():
            value = prop[1]
            
            if prop[0] == "mode":
                if prop[1] == 0:
                    value = '"NORMAL"'
                else:
                    value = '"SKETCH"'
            elif prop[0] == "render_device":
                if prop[1] == 0:
                    value = '"0"'
                else:
                    value = '"1"'
            elif prop[0] == "ms_manual_override":
                if prop[1] == 0:
                    value = '"OVERRIDE"'
                else:
                    value = '"MATERIALS"'
            elif prop[0] == "rs_render_engine":
                if prop[1] == 0:
                    value = '"CYCLES"'
                else:
                    value = '"EEVEE"'
            
            if type(prop[1]) == str:
                value = '"{}"'.format(prop[1])
            elif type(prop[1]) == idprop.types.IDPropertyArray:
                value = '[{}, {}, {}]'.format(prop[1][0], prop[1][1], prop[1][2])
            line = '"{}":{}, \n'.format(prop[0], value)
            text.write(line)
        text.write("} \n")
    write_file(getSettings(), "sketchstyle_settings.py")
    write_file(getDefaultSettings(), "sketchstyle_default_settings.py")
    
#
def load_props():
    def load_props_g(prop_group, name):
        text = bpy.data.texts[name]
        data = ""
        for line in text.lines:
            data += line.body
        data += "\n"
        data += '''
for k, v in settings.items():
    value = v
    if type(v) == idprop.types.IDPropertyArray:
        if not 'ls_' in k:
            value.extend([1])
    setattr({}, k, value)
        '''.format(prop_group)
        exec(data)
    
    if bpy.data.scenes.get("SketchStyle"):
        load_props_g("getSettings()", "sketchstyle_settings.py")
        load_props_g("getDefaultSettings()", "sketchstyle_default_settings.py")
    
    
# Called when user deletes SketchStyle scene
@persistent
def scene_deletion_handler(scene):
    props = getSettings()
    if not bpy.data.scenes.get("SketchStyle") and props.mode == "SKETCH":
        props.mode = "NORMAL"
        props.initial_scene = bpy.data.scenes[0].name
        # Set materials back as they were before (for EEVEE purposes)
        remove_mat_override = False
        try:
            for obj in scene.objects:
                if obj["sketchstyle_mats_to_restore"]:
                    for i in range(len(obj.material_slots)):
                        mat_slot = obj.material_slots[i]
                        mat_slot.material = obj["sketchstyle_mats_to_restore"][str(i)]
                    obj["sketchstyle_mats_to_restore"].clear()
                    if not remove_mat_override:
                        remove_mat_override = True
                    
            if remove_mat_override:
                for layer in bpy.data.scenes["SketchStyle"].view_layers:
                    layer.material_override = None
            bpy.data.materials.remove(bpy.data.materials["cw_SketchStyle"])
        except:
            pass
        
@persistent
def scene_deletion_handler1(scene):
    pass
            
# Called when file gets saved
@persistent
def scene_save_handler(cls):
    if bpy.data.scenes.get("SketchStyle"):
        try:
            props = getSettings()
            mode = props.mode
            props.mode = "SKETCH"
            save_props(mode)
            props.mode = mode
        except:
            pass
    
# Called when file gets loaded
@persistent
def scene_load_handler(cls):
    try:
        if bpy.data.filepath != '':
            load_props()
        else:
            try:
                bpy.ops.object.remove_ss_scene()
            except:
                pass
    except Exception as e:
        print(e)
        if bpy.data.scenes.get("SketchStyle"):
            bpy.ops.scene.delete({"scene": bpy.data.scenes["SketchStyle"]})
        

# SOME HANDLERS
bpy.app.handlers.depsgraph_update_post.append(scene_deletion_handler)
bpy.app.handlers.load_post.append(scene_load_handler)
bpy.app.handlers.save_pre.append(scene_save_handler)
# SOME HANDLERS
# ---------------------------------------------------------------------------
# CLASS REGISTRATION


# DO NOT FORGET TO REMOVE THIS IN PRODUCTION
if __name__ == "__main__":
    register()
# DO NOT FORGET TO REMOVE THIS IN PRODUCTION