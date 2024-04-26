import bpy

def load_settings(settings_path):
    with bpy.data.libraries.load(settings_path) as (data_from, data_to):
        for attr in dir(data_to):
            if attr in ["scenes"]:
                setattr(data_to, attr, getattr(data_from, attr))
                break
    # Take only some properties that we need, then remove the scene
    # so we create a linked scene that later will be filled with 
    # properties from scene loaded from settings file and renamed to SketchStyle
    bpy.context.window.scene = bpy.data.scenes["Scene_For_Sketch_Style_Export_Files"]
    scene = bpy.context.scene
    # Copy neccessary properties
    bpy.context.scene.render.engine = 'CYCLES'
    scene.render.use_freestyle = True
    scene.render.line_thickness_mode = 'RELATIVE'
    scene.view_settings.view_transform = 'Standard'
    #
    samples = bpy.data.scenes["SketchStyle"].view_layers[0].samples
    use_denoising = bpy.data.scenes["SketchStyle"].view_layers[0].cycles.use_denoising
    use_view_map_cache = bpy.data.scenes["SketchStyle"].view_layers[0].freestyle_settings.use_view_map_cache
    # 
    for i in bpy.data.materials:
        if i.name == 'cw_SketchStyle.001' or i.name == 'cw_SketchStyle':
            pass
        else:
            bpy.data.materials.remove(i)
            
    for i in bpy.data.materials:
        print(i.name)
            
    if bpy.data.materials.get('cw_SketchStyle.001'):
        bpy.data.materials.remove(bpy.data.materials.get('cw_SketchStyle'))
        mat = bpy.data.materials["cw_SketchStyle.001"]
        mat.name = 'cw_SketchStyle'
    else:
        mat = bpy.data.materials["cw_SketchStyle"]
    #
    ls_i = 0
    for layer in scene.view_layers:
        layer.samples = samples
        layer.material_override = mat
        layer.cycles.use_denoising = use_denoising
        layer.freestyle_settings.use_view_map_cache = use_view_map_cache
        layer.freestyle_settings.use_smoothness = True
        
        # Remove all linessets from the scene
        freestyle = layer.freestyle_settings
        for lineset in freestyle.linesets:
            freestyle.linesets.remove(lineset)
        # Now load linesets from the settings file
        freestyle_loaded = bpy.data.scenes["SketchStyle"].view_layers[0].freestyle_settings
        #
        for ls in freestyle_loaded.linesets:
            if ls_i < 10:
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
                #
                ls_i += 1
            else:
                break
        ls_i = 0
    #
    for i in bpy.data.scenes:
        if i.name != "Scene_For_Sketch_Style_Export_Files":
            bpy.data.scenes.remove(bpy.data.scenes[i.name])
    #
    bpy.data.objects["Object"].data.materials[0] = mat
    scene.name = "SketchStyle"
    #
    for i in bpy.data.worlds:
        if i.name != "SketchStyle.001":
            bpy.data.worlds.remove(i)
    bpy.data.worlds["SketchStyle.001"].name = "SketchStyle"   
    #
    scene.world = bpy.data.worlds["SketchStyle"]


bpy.ops.wm.open_mainfile(filepath=r'D:\UpWork\Clients\Chipp Walters\SketchStyle\WORK_HERE\sketch_style_working\sketch_style\sketchstyle_exported.blend') 
load_settings(r'D:\UpWork\Clients\Chipp Walters\SketchStyle\WORK_HERE\development.blend') 
bpy.ops.wm.save_as_mainfile(filepath=r'D:\UpWork\Clients\Chipp Walters\SketchStyle\WORK_HERE\assas.blend')