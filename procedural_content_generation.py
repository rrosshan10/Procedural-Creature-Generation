import bpy
import bmesh
from math import cos, sin, pi, radians, sqrt, acos, atan2
import math
from mathutils import Matrix, Vector, Euler
import os

'''Generate a series of rings for the triangles to connect. The main anchor for the mesh generation.'''

def create_ring(bm, center, radius, num_verts=100):
    verts = []
    #Loop to generate a series of connection points for the triangles.
    for i in range(num_verts):
        angle = 2 * pi * i / num_verts
        #Location where the rings are generated
        y = center[1] + radius * cos(angle)
        z = center[2] + radius * sin(angle)
        x = center[0]
        vert = bm.verts.new((x, y, z))
        verts.append(vert)
    return verts

''' Generate a series for rings for the legs as it requires different set of parameters for the leg generation'''
def create_leg_ring(bm, center, radius, num_verts=100):
    verts = []
    #Loop to generate a series of connection points for the triangles.
    for i in range(num_verts):
        angle = 2 * pi * i / num_verts
        x = center[0] + radius * cos(angle)
        y = center[1] + radius * sin(angle)
        z = center[2]
        vert = bm.verts.new((x, y, z))
        verts.append(vert)
    return verts

'''Generate the triangle and its faces with the rings to generate a shape'''
def bridge_rings(bm, verts_a, verts_b):
    #Checks if the vertices are of equal weight.
    if len(verts_a) != len(verts_b):
        return
    '''Loops to connect the triangles based on the weight of each vertices and takes into consideration and swaps the vertices
    if the weight do not match.'''
    for i in range(len(verts_a)):
        v1 = verts_a[i]
        v2 = verts_a[(i + 1) % len(verts_a)]
        v3 = verts_b[i]
        v4 = verts_b[(i + 1) % len(verts_b)]
        
        '''The process of triangulation and generates a series of triangles( i.e. three vertices for triangles, change this for
        different polygons'''
        bm.faces.new([v1, v2, v3])
        bm.faces.new([v2, v3, v4])
    
'''Generate rings for the head. A seperate function for the head as the logic behind creating a head requires more consideration
due to different mathematical factors '''

def create_head_ring(bm, center, ring_radius, ellipsoid_radius, num_verts):
    verts = []
    #Similar to create_ring function but with two additional parameter to consider due to the hade shape being slighlty different.
    for i in range(num_verts):
        angle = 2 * pi * i / num_verts
        x = center[0] + ellipsoid_radius * cos(angle)
        y = center[1] + ring_radius * sin(angle)
        z = center[2]
        vert = bm.verts.new((x, y, z))
        verts.append(vert)
    return verts

'''Generate a series of triangles to connect each of the triangles generated based on the parameters'''
def head_bridge_rings(bm, verts_a, verts_b):
    for i in range(len(verts_a)):
        v1 = verts_a[i]
        v2 = verts_a[(i + 1) % len(verts_a)]
        v3 = verts_b[i]
        v4 = verts_b[(i + 1) % len(verts_b)]
        face_verts = [v1, v2, v4, v3]
        bm.faces.new(face_verts)

'''Logical algorithm for the generation of head after the triangles are generated. 
The head usually is an ellipsoid shape so the generation of head at the start generates a simple ellipsoid shape but changes with
parameters provided by the user to give a more organic head.'''
def create_head(bm, center, radii, num_segments=200, num_rings=100):
    # Create vertex rings for the ellipsoid
    for i in range(num_rings + 1):
        z_angle = pi * i / num_rings
        z = center[2] + cos(z_angle) * radii[2]
        ring_radius = sin(z_angle) * radii[1]

        # A logical statement that provides a smooth curve by adjusting the num_segments at the top.
        if i < num_rings * 0.25:
            num_segments_top = num_segments
        else:
            num_segments_top = int(num_segments * 1.5)

        verts = []
        # Loops over to generate the head by adjusting the shape and othedr factors of the head.
        for j in range(num_segments_top):
            angle = 2 * pi * j / num_segments
            x = center[0] + radii[0] * cos(angle)

            # Adjust the y-coordinate for the top vertices to create a rounded shape
            y = center[1] + ring_radius * sin(angle) * 1.2  # Adjust this factor for desired roundness

            vert = bm.verts.new((x, y, z))
            verts.append(vert)
        #Checks to see if the num_rings is not 0. If it is, the generation of triangles fails.
        if i > 0:
            head_bridge_rings(bm, prev_verts, verts)
        prev_verts = verts

'''Properties and parameters for the head shape and assigning an empty mesh to the head.'''
def create_head_mesh(head_radii):
    # Create a new mesh
    mesh = bpy.data.meshes.new("HeadMesh")
    bm = bmesh.new()

    # Define the center and radii of the head
    center = (0, 0, 0)

    # Create the head mesh using the defined parameters
    create_head(bm, center, head_radii)

    # Assign the mesh data to the bmesh
    bm.to_mesh(mesh)
    bm.free()

    return mesh

'''Attach the head mesh to the body'''
def create_and_attach_head(body_obj, neck_length, head_radii):
    # Check if the 'Head' object already exists in the scene collection
    head_obj = bpy.data.objects.get("Head")

    if head_obj is None:
        # Create the head mesh only if it doesn't exist
        head_mesh = create_head_mesh(head_radii)
        head_obj = bpy.data.objects.new("Head", head_mesh)
        bpy.context.collection.objects.link(head_obj)

    # Position the head object at the end of the neck
    head_tip_position = Vector((neck_length, 0, 0))
    head_obj.location = body_obj.location + body_obj.matrix_world @ head_tip_position

    # Head becomes the child of the parent i.e. body
    head_obj.parent = body_obj

    return head_obj

'''Generate the body mesh based on the parameters'''
def create_body(length, start_radius, max_radius, wave_amplitude, wave_frequency, num_verts=100):
    # Create a new mesh
    mesh = bpy.data.meshes.new("BodyMesh")
    bm = bmesh.new()

    step_size = 0.1
    steps = int(length / step_size)

    prev_ring_verts = None
    last_center = (0, 0, 0)
    last_radius = start_radius
    top_center = (length, 0, 0)
    bottom_center = (0, 0, 0)
    #Loop to generate the body mesh after the parameters are provided by the user.
    for i in range(steps + 1):
        radius = start_radius + (max_radius - start_radius) * abs(sin(pi * i / steps))
        wave_y = wave_amplitude * sin(i / wave_frequency * 2 * pi)
        
        center = (i * step_size, wave_y, 0)
        last_center = center
        last_radius = radius
        ring_verts = create_ring(bm, center, radius, num_verts)
        
        if prev_ring_verts:
            bridge_rings(bm, prev_ring_verts, ring_verts)

        prev_ring_verts = ring_verts
    
    # Assign the mesh data to the bmesh
    bm.to_mesh(mesh)
    bm.free()

    # Create a new body object and link it to the scene
    obj = bpy.data.objects.new("Body", mesh)
    bpy.context.collection.objects.link(obj)

    # Return the object
    return obj, top_center, bottom_center, last_center, last_radius

'''Generate the tail for the creature based on the parameters provided'''
def create_tail(body_obj, start_center, start_radius, length, tip_radius, wave_amplitude, wave_frequency, num_verts=100):
    # Create a new mesh
    mesh = bpy.data.meshes.new("TailMesh")
    bm = bmesh.new()

    step_size = length / num_verts
    steps = num_verts

    prev_ring_verts = None
    #Loop to generate the tail mesh after the parameters are provided by the user.
    for i in range(steps + 1):
        radius = start_radius - (start_radius - tip_radius) * (i / steps)
        wave_x = wave_amplitude * sin(i / wave_frequency * 2 * pi)
        
        center = (start_center[0] - i * step_size, start_center[1] + wave_x, start_center[2])
        ring_verts = create_ring(bm, center, radius, num_verts)
        
        if prev_ring_verts:
            bridge_rings(bm, prev_ring_verts, ring_verts)

        prev_ring_verts = ring_verts

    # Assign the mesh data to the bmesh
    bm.to_mesh(mesh)
    bm.free()

    # Create a new tail object and link it to the scene
    obj = bpy.data.objects.new("Tail", mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = body_obj

    # Return the object
    return obj

'''Generate the neck for the creature based on the parameters provided'''
def create_neck(body_obj, start_center, start_radius, length, end_radius, orientation='x', wave_amplitude=0.3, wave_frequency=30, num_verts=100):
    # Create a new mesh
    mesh = bpy.data.meshes.new("NeckMesh")
    bm = bmesh.new()

    step_size = length / num_verts
    steps = num_verts

    prev_ring_verts = None
    #Loop to generate the tail mesh after the parameters are provided by the user.
    for i in range(steps + 1):
        radius = start_radius + (end_radius - start_radius) * (i / steps)
        wave_offset = wave_amplitude * math.sin(i / steps * math.pi * 2)
        
        center = (start_center[0] + i * step_size, start_center[1], start_center[2] + wave_offset)
        ring_verts = create_ring(bm, center, radius, num_verts)
        
        if prev_ring_verts:
            bridge_rings(bm, prev_ring_verts, ring_verts)

        prev_ring_verts = ring_verts

    # Assign the mesh data to the bmesh
    bm.to_mesh(mesh)
    bm.free()

    # Create a new object and link it to the scene
    obj = bpy.data.objects.new("Neck", mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = body_obj

    # Rotate the neck along the Z-axis if necessary
    if orientation == 'x':
        obj.rotation_euler[0] = math.radians(90.0)

    # Return the object
    return obj

'''Generate the neck for the creature based on the parameters provided. Legs have additional parameters due to the 
nature of the leg as it has more elements'''
def create_leg(start_point, end_point, radius, position, thigh_height, shin_height, foot_height, thigh_radius, shin_radius, foot_radius, num_segments=20):
    # Create a new mesh and object
    mesh = bpy.data.meshes.new("AnimalLeg")
    obj = bpy.data.objects.new("AnimalLeg", mesh)

    # Link the object to the scene
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    # Set the position of the leg object
    obj.location = position

    # Initialize a bmesh object and start with the thigh
    bm = bmesh.new()

    # Parameters for the leg parts
    segments = 100  # Number of segments per part of the leg

    prev_verts = None

    # New bending parameters
    thigh_bend = -0.5
    shin_bend = -0.1
    foot_bend = 0.5

    for i in range(segments):
        # Calculate the radius and center for this segment with bending
        if i < segments / 3:
            # Thigh with bend
            radius = thigh_radius - (i / segments) * (thigh_radius - shin_radius)
            height = (i / segments) * thigh_height
            center_offset = thigh_bend  # bend for thigh
        elif i < 2 * segments / 3:
            # Shin with bend
            radius = shin_radius - ((i - segments / 3) / segments) * (shin_radius - foot_radius)
            height = thigh_height + ((i - segments / 3) / segments) * shin_height
            center_offset = shin_bend  # bend for shin
        else:
            # Foot with bend
            radius = foot_radius
            height = thigh_height + shin_height + ((i - 2 * segments / 3) / segments) * foot_height
            center_offset = foot_bend  # bend for foot

        # Apply bending to the center offset based on the segment's height
        center = (center_offset * height, 0, height)
        new_verts = create_leg_ring(bm, center, radius)

        if prev_verts:
            bridge_rings(bm, prev_verts, new_verts)
        prev_verts = new_verts

    # Assign the mesh data to the bmesh
    bm.to_mesh(mesh)
    bm.free()

    return obj

def visualize_leg_points(body_obj, num_legs=8, leg_distance=0.5, leg_height=0.5, thigh_height=1.5, shin_height=1.0, foot_height=0.5, thigh_radius=0.2, shin_radius=0.2, foot_radius=0.1):
    
    attachment_points = []

    if body_obj is None:
        print("Error: body_obj is None. Make sure to create the body object first.")
        return attachment_points

    # Get the dimensions of the body object
    body_dimensions = body_obj.dimensions
    body_length = body_dimensions[0]

    # Calculate the Z-coordinate for the legs
    leg_z = 0 + 0.55

    # Calculate the X-offset for legs
    x_offset_step = body_length / ((num_legs // 2) + 1)  # Divide by 2 because each pair of legs shares the same x-offset

    # Use the same x-offset for both odd and even numbered legs
    x_offset = x_offset_step

    # If num_legs is odd, adjust the x_offset for the last leg
    if num_legs % 2 != 0:
        x_offset = body_length  / (num_legs + 1)

    # Visualize attachment points and create legs
    for i in range(num_legs):

        # Create leg object with a unique name based on its position
        leg_name = f"Leg_{i+1}" 
        leg_obj = create_leg(Vector((x_offset, 0, leg_z)), Vector((x_offset, 0, leg_z - leg_height)), radius=0.1, position=Vector((x_offset, 0, leg_z)), thigh_height=thigh_height, shin_height=shin_height, foot_height=foot_height, thigh_radius=thigh_radius, shin_radius=shin_radius, foot_radius=foot_radius)
        leg_obj.name = leg_name  # Assign unique name to the leg object

        # Set rotation for the leg

        # Update x-offset for the next leg
        if (i + 1) % 2 == 0:
            # Even numbered legs
            x_offset += x_offset_step

        attachment_points.append(leg_obj.location)

    # Modify rotation for all legs after they are generated
    for leg_obj in bpy.data.objects:
        if leg_obj.name.startswith("Leg"):
            if int(leg_obj.name.split("_")[1]) % 2 == 0:
                # Even numbered legs
                leg_obj.rotation_euler = Euler((math.radians(-90), math.radians(270), math.radians(0)), 'XYZ')
            else:
                # Odd numbered legs
                leg_obj.rotation_euler = Euler((math.radians(90), math.radians(270), math.radians(0)), 'XYZ')

    return attachment_points


'''Generate the wings for the creature based on the parameters provided by the user.'''

def create_wing(body_obj, position, wing_length, wing_thickness, start_width, end_width, num_verts=20, num_verts_w=10):
    bm = bmesh.new()
    verts = []

    for i in range(num_verts):
        for j in range(num_verts_w):
            # Calculate the width of the wing at this position based on the start and end widths
            width = start_width + (end_width - start_width) * (i / num_verts)

            # Calculate the position of each vertex relative to the origin
            x = (wing_length / num_verts) * i
            z = (width / num_verts_w) * j * (-1 if j % 2 == 0 else 1)  # Zigzag pattern

            # Apply a sine function to the y-coordinate to create irregularities
            y_offset = (width / 2) * math.sin((i / num_verts) * math.pi) * math.cos((j / num_verts_w) * math.pi)

            # Create the vertex
            vert = bm.verts.new((x, y_offset, z))
            verts.append(vert)

    # Bridge vertices to create faces
    for i in range(num_verts - 1):
        for j in range(num_verts_w - 1):
            v1 = verts[i * num_verts_w + j]
            v2 = verts[i * num_verts_w + (j + 1)]
            v3 = verts[(i + 1) * num_verts_w + (j + 1)]
            v4 = verts[(i + 1) * num_verts_w + j]
            face_verts = [v1, v2, v3, v4]
            bm.faces.new(face_verts)

    # Create a new mesh
    mesh = bpy.data.meshes.new("WingMesh")
    # Assign the mesh data to the bmesh
    bm.to_mesh(mesh)
    bm.free()

    # Create a new object and link it to the scene
    obj = bpy.data.objects.new("Wing", mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = body_obj
    obj.location = position

    # Return the object
    return obj



'''Visualizae the points in the body where the wings will be placed. A simple logic has been applied to position the wings at the center
of the body. '''

def visualize_wing_points(body_obj, num_wings=2, wing_distance=0.1, wing_height=1.0, wing_length=20.0, wing_thickness=0.1, start_width=2.0, end_width=1.0):
    attachment_points = []

    if body_obj is None:
        print("Error: body_obj is None. Make sure to create the body object first.")
        return attachment_points
    
    body_dimensions = body_obj.dimensions
    body_length = body_dimensions[0]
    
    wing_z = 0.55
    wing_y = 0.55

    # Calculate the X-offset for wings
    x_offset_step = body_length / 2  # Divide by 2 because each pair of wings shares the same x-offset

    # Use the same x-offset for both odd and even numbered wings
    x_offset = x_offset_step

    # Visualize attachment points and create wings
    for i in range(num_wings):
        # Create wing object with a unique name based on its position
        wing_name = f"Wing_{i+1}" 
        wing_obj = create_wing(body_obj, Vector((x_offset, wing_y, wing_z)), wing_length, wing_thickness, start_width, end_width)
        wing_obj.name = wing_name  # Assign unique name to the wing object

        # Apply rotation for odd and even numbered wings
        if (i + 1) % 2 == 1:
            # Odd numbered wings
            wing_obj.rotation_euler = Euler((math.radians(90), math.radians(-90), math.radians(90)), 'XYZ')
        else:
            # Even numbered wings
            wing_obj.rotation_euler = Euler((math.radians(-90), math.radians(-270), math.radians(90)), 'XYZ')

        # Additional rotation for the first and last two wings when num_wings > 2
        if num_wings > 2:
            if i == 0 or i == 1:
                # Front two wings
                wing_obj.rotation_euler.rotate_axis('Y', math.radians(-40))
            elif i == num_wings - 2 or i == num_wings - 1:
                # Back two wings
                wing_obj.rotation_euler.rotate_axis('Y', math.radians(40))

        attachment_points.append(wing_obj.location)

        # Update x-offset for the next wing
        x_offset += wing_distance

    return attachment_points


'''Applying texture to the mesh by the image provided by the user and adjust the size, shape, color and other factos based on the image nodes'''
def create_painted_texture_material(image_path, tex_coord_location=(-600, 0),
                                    image_texture_location=(-400, 0),
                                    mapping_location=(-200, 0),
                                    output_location=(200, 0)):
    # Create a new material
    material = bpy.data.materials.new(name="PaintedTextureMaterial")
    material.use_nodes = True

    # Clear default nodes
    nodes = material.node_tree.nodes
    nodes.clear()

    # Create texture coordinate node
    tex_coord_node = nodes.new(type='ShaderNodeTexCoord')
    tex_coord_node.location = tex_coord_location

    # Create image texture node
    image_texture_node = nodes.new(type='ShaderNodeTexImage')
    image_texture_node.location = image_texture_location
    try:
        image_texture_node.image = bpy.data.images.load(image_path)  # Load the image from file
    except:
        print("Failed to load image:", image_path)

    # Create mapping node to adjust texture coordinates
    mapping_node = nodes.new(type='ShaderNodeMapping')
    mapping_node.location = mapping_location
    mapping_node.inputs['Scale'].default_value = (0.1, 0.1, 0.1)  # Adjust scale as needed

    # Create texture coordinate mapping
    material.node_tree.links.new(tex_coord_node.outputs['Generated'], mapping_node.inputs['Vector'])
    material.node_tree.links.new(mapping_node.outputs['Vector'], image_texture_node.inputs['Vector'])

    # Create output node
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = output_location
    material.node_tree.links.new(image_texture_node.outputs['Color'], output_node.inputs['Surface'])

    return material

'''Assigning the materail to the creature and checks if the materials has been assigned properly. Also replaces the materials
if it is alread assigned with the new material'''
def assign_material_to_objects(material):
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            if obj.data.materials:
                # If the object already has materials assigned, replace the first material slot with the new material
                obj.data.materials[0] = material
            else:
                # If the object has no materials assigned, append the new material to its material slots
                obj.data.materials.append(material)

'''Class for different properties of the body and the default value and minimum values assigned.'''
class CreatureProperties(bpy.types.PropertyGroup):
    # Body Properties
    body_length: bpy.props.FloatProperty(name="Length", default=10.0, min=0.0)
    body_start_radius: bpy.props.FloatProperty(name="Start Radius", default=0.5, min=0.0)
    body_max_radius: bpy.props.FloatProperty(name="Max Radius", default=1.5, min=0.0)
    body_wave_amplitude: bpy.props.FloatProperty(name="Wave Amplitude", default=0.3, min=0.0)
    body_wave_frequency: bpy.props.FloatProperty(name="Wave Frequency", default=50, min=0.0)
    body_num_verts: bpy.props.IntProperty(name="Number of Vertices", default=100, min=3)

    # Neck Properties
    neck_length: bpy.props.FloatProperty(name="Length", default=3.5, min=0.0)
    neck_end_radius: bpy.props.FloatProperty(name="End Radius", default=0.2, min=0.0)
    neck_wave_amplitude: bpy.props.FloatProperty(name="Wave Amplitude", default=0.1, min=0.0)
    neck_wave_frequency: bpy.props.FloatProperty(name="Wave Frequency", default=60, min=0.0)
    neck_num_verts: bpy.props.IntProperty(name="Number of Vertices", default=100, min=3)

    # Tail Properties
    tail_length: bpy.props.FloatProperty(name="Length", default=5.0, min=0.0)
    tail_tip_radius: bpy.props.FloatProperty(name="Tip Radius", default=0.01, min=0.0)
    tail_wave_amplitude: bpy.props.FloatProperty(name="Wave Amplitude", default=0.2, min=0.0)
    tail_wave_frequency: bpy.props.FloatProperty(name="Wave Frequency", default=50, min=0.0)
    tail_num_verts: bpy.props.IntProperty(name="Number of Vertices", default=100, min=3)

    # Leg Properties
    num_legs: bpy.props.IntProperty(name = "Number of Legs", default=4, min=1)
    thigh_height: bpy.props.FloatProperty(name="Thigh Height", default=1.5, min=0.0)
    shin_height: bpy.props.FloatProperty(name="Shin Height", default=5.0, min=0.0)
    foot_height: bpy.props.FloatProperty(name="Foot Height", default=0.5, min=0.0)
    thigh_radius: bpy.props.FloatProperty(name="Thigh Radius", default=0.2, min=0.0)
    shin_radius: bpy.props.FloatProperty(name="Shin Radius", default=0.2, min=0.0)
    foot_radius: bpy.props.FloatProperty(name="Foot Radius", default=0.1, min=0.0)
    leg_distance: bpy.props.FloatProperty(name="Leg Distance", default=0.0, min=0.0)
    leg_height: bpy.props.FloatProperty(name="Leg Height", default=0.0, min=0.0)   
    generate_legs: bpy.props.BoolProperty(name="Generate Legs", default=False)

    # Head Properties
    head_num_segments: bpy.props.IntProperty(name="Number of Segments", default=200, min=3)
    head_num_rings: bpy.props.IntProperty(name="Number of Verts", default=100, min=3)
    head_radii_x: bpy.props.FloatProperty(name="X Radius", default=1.0, min=0.0)
    head_radii_y: bpy.props.FloatProperty(name="Y Radius", default=1.0, min=0.0)
    head_radii_z: bpy.props.FloatProperty(name="Z Radius", default=1.0, min=0.0)
    
    #Wing Properties
    num_wings: bpy.props.IntProperty(name="Number of Wings", default=2, min=1)
    wing_distance: bpy.props.FloatProperty(name="Wing Distance", default=0.1, min=0.0)
    wing_length: bpy.props.FloatProperty(name="Wing Length", default=10.0, min=0.0)
    wing_thickness: bpy.props.FloatProperty(name="Wing Thickness", default=0.1, min=0.0)
    wing_start_width: bpy.props.FloatProperty(name="Wing Start Width", default=2.0, min=0.0)
    wing_end_width: bpy.props.FloatProperty(name="Wing End Width", default=1.0, min=0.0)
    
    
    generate_wings: bpy.props.BoolProperty(name="Generate Wings", default=False)
    
    #Material Property
    material_path: bpy.props.StringProperty(name="Material Path", default="", subtype='FILE_PATH')


''' Define the panel to display the creature properties. The panel is generated in the blender scene below the view tab.'''
class CreaturePropertiesPanel(bpy.types.Panel):
    bl_label = "Creature Properties"
    bl_idname = "VIEW3D_PT_CreaturePropertiesPanel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'  # Set to 'UI' to display in the sidebar
    bl_category = "Creature"

    def draw(self, context):
        layout = self.layout
        props = context.scene.creature_properties

        # Body Properties
        layout.label(text="Body Properties:")
        layout.prop(props, "body_length")
        layout.prop(props, "body_start_radius")
        layout.prop(props, "body_max_radius")
        layout.prop(props, "body_wave_amplitude")
        layout.prop(props, "body_wave_frequency")
        layout.prop(props, "body_num_verts")

        # Neck Properties
        layout.label(text="Neck Properties:")
        layout.prop(props, "neck_length")
        layout.prop(props, "neck_end_radius")
        layout.prop(props, "neck_wave_amplitude")
        layout.prop(props, "neck_wave_frequency")
        layout.prop(props, "neck_num_verts")

        # Tail Properties
        layout.label(text="Tail Properties:")
        layout.prop(props, "tail_length")
        layout.prop(props, "tail_tip_radius")
        layout.prop(props, "tail_wave_amplitude")
        layout.prop(props, "tail_wave_frequency")
        layout.prop(props, "tail_num_verts")

        # Leg Properties
        
        layout.label(text="Leg Properties:")
        layout.prop(props, "generate_legs", text="Generate Legs")
        layout.prop(props, "num_legs")
        layout.prop(props, "thigh_height")
        layout.prop(props, "shin_height")
        layout.prop(props, "foot_height")
        layout.prop(props, "thigh_radius")
        layout.prop(props, "shin_radius")
        layout.prop(props, "foot_radius")
        layout.prop(props, "num_segments")

        # Head Properties
        layout.label(text="Head Properties:")
        layout.prop(props, "head_num_segments")
        layout.prop(props, "head_num_rings")
        layout.prop(props, "head_radii_x")
        layout.prop(props, "head_radii_y")
        layout.prop(props, "head_radii_z")
        
        #Wing Properties
        
        layout.label(text="Wing Properties:")
        layout.prop(props, "generate_wings", text="Generate Wings")
        layout.prop(props, "num_wings")
        layout.prop(props, "wing_distance")
        layout.prop(props, "wing_length")
        layout.prop(props, "wing_thickness")
        layout.prop(props, "wing_start_width")
        layout.prop(props, "wing_end_width")
        
        #Material Properties
        layout.prop(props, "material_path", text="Material File")

        layout.operator("object.generate_creature", text="Generate Creature")

'''Anchor to take in all the values provided by the user. Assigned to the generate creature button and onclick generates the creatures
based on the values of the user.'''
class OBJECT_OT_GenerateCreature(bpy.types.Operator):
    bl_idname = "object.generate_creature"
    bl_label = "Generate Creature"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        # Clear the scene and delete all existing objects
        bpy.ops.object.select_all(action='DESELECT')
        bpy.ops.object.select_by_type(type='MESH')
        bpy.ops.object.delete()

        # Get the creature properties
        props = context.scene.creature_properties

        # Generate the body, neck, and tail
        body_obj, top_center, bottom_center, last_center, top_radius = create_body(
            length=props.body_length,
            start_radius=props.body_start_radius,
            max_radius=props.body_max_radius,
            wave_amplitude=props.body_wave_amplitude,
            wave_frequency=props.body_wave_frequency,
            num_verts=props.body_num_verts
        )
        
        neck_obj = create_neck(body_obj,
            start_center=top_center,
            start_radius=top_radius,
            length=props.neck_length,
            end_radius=props.neck_end_radius,
            orientation='x',
            wave_amplitude=props.neck_wave_amplitude,
            wave_frequency=props.neck_wave_frequency,
            num_verts=props.neck_num_verts
        )

        tail_obj = create_tail(body_obj,
            start_center=bottom_center,
            start_radius=top_radius,
            length=props.tail_length,
            tip_radius=props.tail_tip_radius,
            wave_amplitude=props.tail_wave_amplitude,
            wave_frequency=props.tail_wave_frequency,
            num_verts=props.tail_num_verts
        )
        
        if props.generate_legs:
            thigh_height = props.thigh_height
            shin_height = props.shin_height
            foot_height = props.foot_height
            thigh_radius = props.thigh_radius
            shin_radius = props.shin_radius
            foot_radius = props.foot_radius
            leg_distance = 0.0  # Distance of the legs from the body's central axis along the Z-axis
            leg_height = 0.0

            attachment_points = visualize_leg_points(
                body_obj,
                num_legs=props.num_legs,
                leg_distance=leg_distance,
                leg_height=0.1,
                thigh_height=thigh_height,
                shin_height=shin_height,
                foot_height=foot_height,
                thigh_radius=thigh_radius,
                shin_radius=shin_radius,
                foot_radius=foot_radius,
        )

        # Attach head to the body
        head_obj = create_and_attach_head(body_obj, props.body_length + props.neck_length, 
                                           (props.head_radii_x, props.head_radii_y, props.head_radii_z))
        
        if props.generate_wings:
            wing_attachment_points = visualize_wing_points(body_obj,
                num_wings=props.num_wings, 
                wing_distance= props.wing_distance, 
                wing_length= props.wing_length, 
                wing_thickness= props.wing_thickness, 
                start_width = props.wing_start_width, 
                end_width = props.wing_end_width
            )

        # Rotate objects as needed
        body_obj.rotation_euler = (math.radians(-90), 0, 0)
        neck_obj.rotation_euler = (math.radians(90), 0, 0)
        tail_obj.rotation_euler = (math.radians(-180), 0, 0)
        head_obj.rotation_euler = (0, 0, math.radians(90))

        
        
        material_path = bpy.path.abspath(props.material_path)
        material = create_painted_texture_material(material_path)
        if material:
            for obj in bpy.data.objects:
                if obj.type == 'MESH':
                    obj.data.materials.clear()
                    obj.data.materials.append(material)
        else:
            print("Material creation failed or material path is invalid.")

        return {'FINISHED'}

''' Register the PropertyGroup and Panel classes to the Blender scene'''
def register():
    bpy.utils.register_class(CreatureProperties)
    bpy.utils.register_class(CreaturePropertiesPanel)
    bpy.utils.register_class(OBJECT_OT_GenerateCreature)
    bpy.types.Scene.creature_properties = bpy.props.PointerProperty(type=CreatureProperties)

'''Unregisters the previous properties and appends it with new one in case there are changes to the properties and panel class'''
def unregister():
    bpy.utils.unregister_class(CreatureProperties)
    bpy.utils.unregister_class(CreaturePropertiesPanel)
    bpy.utils.unregister_class(OBJECT_OT_GenerateCreature)
    del bpy.types.Scene.creature_properties

'''Main function to run the script.'''
if __name__ == "__main__":
        
    register()
