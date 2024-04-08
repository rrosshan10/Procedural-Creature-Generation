import bpy
import bmesh
from math import cos, sin, pi, radians, sqrt, acos, atan2
import math
from mathutils import Matrix, Vector, Euler
import os
from scipy.spatial import Delaunay

def create_ring(bm, center, radius, num_verts=100):
    verts = []
    for i in range(num_verts):
        angle = 2 * pi * i / num_verts
        # Swap y and z for the new orientation along the x-axis
        y = center[1] + radius * cos(angle)
        z = center[2] + radius * sin(angle)
        x = center[0]
        vert = bm.verts.new((x, y, z))
        verts.append(vert)
    return verts

def create_leg_ring(bm, center, radius, num_verts=100):
    verts = []
    for i in range(num_verts):
        angle = 2 * pi * i / num_verts
        x = center[0] + radius * cos(angle)
        y = center[1] + radius * sin(angle)
        z = center[2]
        vert = bm.verts.new((x, y, z))
        verts.append(vert)
    return verts


def bridge_rings(bm, verts_a, verts_b):
    if len(verts_a) != len(verts_b):
        return
    
    for i in range(len(verts_a)):
        v1 = verts_a[i]
        v2 = verts_a[(i + 1) % len(verts_a)]
        v3 = verts_b[i]
        v4 = verts_b[(i + 1) % len(verts_b)]
        
        # Create faces using triangles
        bm.faces.new([v1, v2, v3])
        bm.faces.new([v2, v3, v4])

def create_head_ring(bm, center, ring_radius, ellipsoid_radius, num_verts):
    verts = []
    for i in range(num_verts):
        angle = 2 * pi * i / num_verts
        x = center[0] + ellipsoid_radius * cos(angle)
        y = center[1] + ring_radius * sin(angle)
        z = center[2]
        vert = bm.verts.new((x, y, z))
        verts.append(vert)
    return verts

def head_bridge_rings(bm, verts_a, verts_b):
    for i in range(len(verts_a)):
        v1 = verts_a[i]
        v2 = verts_a[(i + 1) % len(verts_a)]
        v3 = verts_b[i]
        v4 = verts_b[(i + 1) % len(verts_b)]
        face_verts = [v1, v2, v4, v3]
        bm.faces.new(face_verts)

def create_head(bm, center, radii, num_segments=200, num_rings=100):
    # Create vertex rings for the ellipsoid
    for i in range(num_rings + 1):
        z_angle = pi * i / num_rings
        z = center[2] + cos(z_angle) * radii[2]
        ring_radius = sin(z_angle) * radii[1]

        # Adjust the number of segments towards the top for a smoother curve
        if i < num_rings * 0.25:
            num_segments_top = num_segments
        else:
            num_segments_top = int(num_segments * 1.5)

        verts = []
        for j in range(num_segments_top):
            angle = 2 * pi * j / num_segments
            x = center[0] + radii[0] * cos(angle)

            # Adjust the y-coordinate for the top vertices to create a rounded shape
            y = center[1] + ring_radius * sin(angle) * 1.2  # Adjust this factor for desired roundness

            vert = bm.verts.new((x, y, z))
            verts.append(vert)

        if i > 0:
            head_bridge_rings(bm, prev_verts, verts)
        prev_verts = verts


def create_head_mesh():
    # Create a new mesh
    mesh = bpy.data.meshes.new("HeadMesh")
    bm = bmesh.new()

    # Define the center and radii of the head
    center = (0, 0, 0)
    radii = (0.5, 1.5, 0.5)  # a, b, and c from your image

    # Create the head mesh using the defined parameters
    create_head(bm, center, radii)

    # Assign the mesh data to the bmesh
    bm.to_mesh(mesh)
    bm.free()

    return mesh

# Function to create the head object and attach it to the body
def create_and_attach_head(body_obj, neck_length):
    # Check if the 'Head' object already exists in the scene collection
    head_obj = bpy.data.objects.get("Head")

    if head_obj is None:
        # Create the head mesh only if it doesn't exist
        head_mesh = create_head_mesh()
        head_obj = bpy.data.objects.new("Head", head_mesh)
        bpy.context.collection.objects.link(head_obj)

    # Position the head object at the end of the neck
    head_tip_position = Vector((neck_length, 0, 0))
    head_obj.location = body_obj.location + body_obj.matrix_world @ head_tip_position

    # Make the head the child of the body
    head_obj.parent = body_obj

    return head_obj

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

    # Create a new object and link it to the scene
    obj = bpy.data.objects.new("Body", mesh)
    bpy.context.collection.objects.link(obj)

    # Return the object
    return obj, top_center, bottom_center, last_center, last_radius

def create_tail(start_center, start_radius, length, tip_radius, wave_amplitude, wave_frequency, num_verts=100):
    # Create a new mesh
    mesh = bpy.data.meshes.new("TailMesh")
    bm = bmesh.new()

    step_size = length / num_verts
    steps = num_verts

    prev_ring_verts = None
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

    # Create a new object and link it to the scene
    obj = bpy.data.objects.new("Tail", mesh)
    bpy.context.collection.objects.link(obj)

    # Return the object
    return obj

def create_neck(start_center, start_radius, length, end_radius, orientation='x', wave_amplitude=0.3, wave_frequency=30, num_verts=100):
    # Create a new mesh
    mesh = bpy.data.meshes.new("NeckMesh")
    bm = bmesh.new()

    step_size = length / num_verts
    steps = num_verts

    prev_ring_verts = None
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

    # Rotate the neck along the Z-axis if necessary
    if orientation == 'x':
        obj.rotation_euler[0] = math.radians(90.0)

    # Return the object
    return obj

def create_leg(start_point, end_point, radius, thigh_height, shin_height, foot_height, thigh_radius, shin_radius, foot_radius, num_segments=20):
    # Create a new mesh and object
    mesh = bpy.data.meshes.new("AnimalLeg")
    obj = bpy.data.objects.new("AnimalLeg", mesh)

    # Link the object to the scene
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

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

def visualize_leg_points(body_obj, leg_distance=0.5, leg_height=0.5, thigh_height=1.5, shin_height=1.0, foot_height=0.5, thigh_radius=0.2, shin_radius=0.2, foot_radius=0.1):
    """
    Visualizes leg attachment points on the body for both positive and negative z-axis positions.
    
    :param body_obj: The Blender object representing the body.
    :param leg_distance: Distance of the legs from the body's central axis along the Z-axis.
    :param leg_height: Height of the legs from the ground level.
    :param thigh_height: Height of the thigh segment of the legs.
    :param shin_height: Height of the shin segment of the legs.
    :param foot_height: Height of the foot segment of the legs.
    :param thigh_radius: Radius of the thigh segment of the legs.
    :param shin_radius: Radius of the shin segment of the legs.
    :param foot_radius: Radius of the foot segment of the legs.
    :return: A list of attachment points for the legs.
    """
    attachment_points = []

    if body_obj is None:
        print("Error: body_obj is None. Make sure to create the body object first.")
        return attachment_points

    # Get the dimensions of the body object
    body_dimensions = body_obj.dimensions
    body_length = body_dimensions[0]

    # Calculate the X-coordinates for the top and bottom pairs of legs
    top_leg_x = body_length - 0.5
    bottom_leg_x = 0 + 0.5

    # Calculate the Z-coordinate for the top pair of legs
    top_leg_z = 0 + 0.55

    # Visualize attachment points and create legs for the top pair of legs (positive z-axis)
    for i in range(2):
        z_offset = top_leg_z if i == 0 else -top_leg_z

        # Create leg object with a unique name based on its position
        leg_name = f"Leg_{i+1}_{'Top' if i == 0 else 'Bottom'}"  # Example: Leg_1_Top
        leg_obj = create_leg(Vector((top_leg_x, 0, z_offset)), Vector((top_leg_x, 0, z_offset - leg_height)), radius=0.1, thigh_height=thigh_height, shin_height=shin_height, foot_height=foot_height, thigh_radius=thigh_radius, shin_radius=shin_radius, foot_radius=foot_radius)
        leg_obj.name = leg_name  # Assign unique name to the leg object

        # Position leg
        leg_obj.location = Vector((top_leg_x, 0, z_offset))

        attachment_points.append(leg_obj.location)
    
        if i == 1:
            leg_obj.rotation_euler = (math.radians(180), 0, math.radians(90))
        elif i == 0:
            leg_obj.rotation_euler = (0, 0, math.radians(90))

    # Visualize attachment points and create legs for the bottom pair of legs (positive z-axis)
    for i in range(2):
        z_offset = top_leg_z if i == 0 else -top_leg_z

        # Create leg object with a unique name based on its position
        leg_name = f"Leg_{i+3}_{'Top' if i == 0 else 'Bottom'}"  # Example: Leg_3_Top
        leg_obj = create_leg(Vector((bottom_leg_x, 0, z_offset)), Vector((bottom_leg_x, 0, z_offset - leg_height)), radius=0.1, thigh_height=thigh_height, shin_height=shin_height, foot_height=foot_height, thigh_radius=thigh_radius, shin_radius=shin_radius, foot_radius=foot_radius)
        leg_obj.name = leg_name  # Assign unique name to the leg object

        # Position leg
        leg_obj.location = Vector((bottom_leg_x, 0, z_offset))

        attachment_points.append(leg_obj.location)

        # Rotate leg by 180 degrees on the X-axis and then by 90 degrees on the Z-axis
        if i == 1:
            leg_obj.rotation_euler = (math.radians(180), 0, math.radians(90))
        elif i == 0:
            leg_obj.rotation_euler = (0, 0, math.radians(90))

    return attachment_points

def create_wing(base_center, wing_length, wing_thickness, start_width, end_width, num_verts_length=20, num_verts_width=10):
    bm = bmesh.new()
    verts = []

    for i in range(num_verts_length):
        for j in range(num_verts_width):
            # Calculate the width of the wing at this position based on the start and end widths
            width = start_width + (end_width - start_width) * (i / num_verts_length)

            # Calculate the position of each vertex
            x = base_center[0] + (wing_length / num_verts_length) * i
            z = base_center[2] + (width / num_verts_width) * j * (-1 if j % 2 == 0 else 1)  # Zigzag pattern

            # Apply a sine function to the y-coordinate to create irregularities
            y_offset = (width / 2) * math.sin((i / num_verts_length) * math.pi) * math.cos((j / num_verts_width) * math.pi)
            y = base_center[1] + y_offset

            vert = bm.verts.new((x, y, z))
            verts.append(vert)

    # Bridge vertices to create faces
    for i in range(num_verts_length - 1):
        for j in range(num_verts_width - 1):
            v1 = verts[i * num_verts_width + j]
            v2 = verts[i * num_verts_width + (j + 1)]
            v3 = verts[(i + 1) * num_verts_width + (j + 1)]
            v4 = verts[(i + 1) * num_verts_width + j]
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

    # Set the location of the wing object to match the base center
    obj.location = base_center

    # Return the object
    return obj


def visualize_wing_points(body_obj, wing_distance=0.1, wing_height=1.0, wing_length=20.0, wing_thickness=0.1, start_width=2.0, end_width=1.0):
    """
    Visualizes wing attachment points on the body.
    
    :param body_obj: The Blender object representing the body.
    :param wing_distance: Distance of the wings from the body's central axis along the Y-axis.
    :param wing_height: Height of the wings from the ground level.
    :param wing_length: Length of the wings.
    :param wing_thickness: Thickness of the wings.
    :return: A list of attachment points for the wings.
    """
    attachment_points = []

    if body_obj is None:
        print("Error: body_obj is None. Make sure to create the body object first.")
        return attachment_points
    
    body_dimensions = body_obj.dimensions
    body_length = body_dimensions[0]
    
    wing_x = body_length / 1.8
    wing_y = 0.4
    wing_z = 0

    # Global position and rotation for the wings
    global_position = Vector((0, 0, 0))
    global_rotation = Euler((math.radians(90), math.radians(-90), math.radians(90)))

    # Create left wing
    left_wing_name = "Left_Wing"
    left_wing_obj = create_wing(global_position, wing_length, wing_thickness, start_width, end_width)
    left_wing_obj.name = left_wing_name
    left_wing_obj.rotation_euler = global_rotation
    left_wing_obj.location = Vector((wing_x, wing_y, wing_z))
    left_wing_obj.parent = body_obj
    attachment_points.append(left_wing_obj.location)

    # Create right wing
    right_wing_name = "Right_Wing"
    right_wing_obj = create_wing(global_position, wing_length, wing_thickness, start_width, end_width)
    right_wing_obj.name = right_wing_name
    right_wing_obj.rotation_euler = global_rotation.copy()
    right_wing_obj.rotation_euler[2] = math.radians(90)  # Adjust Z rotation for the mirror wing
    right_wing_obj.rotation_euler[1] = math.radians(90)  # Adjust Z rotation for the mirror wing
    right_wing_obj.rotation_euler[0] = math.radians(270)  # Adjust Z rotation for the mirror wing
    right_wing_obj.location = Vector((wing_x, wing_y, wing_z))
    right_wing_obj.parent = body_obj
    attachment_points.append(right_wing_obj.location)

    return attachment_points



def create_painted_texture_material(image_path):
    # Create a new material
    material = bpy.data.materials.new(name="PaintedTextureMaterial")
    material.use_nodes = True

    # Clear default nodes
    nodes = material.node_tree.nodes
    nodes.clear()

    # Create texture coordinate node
    tex_coord_node = nodes.new(type='ShaderNodeTexCoord')
    tex_coord_node.location = (-600, 0)

    # Create image texture node
    image_texture_node = nodes.new(type='ShaderNodeTexImage')
    image_texture_node.location = (-400, 0)
    image_texture_node.image = bpy.data.images.load(image_path)  # Load the image from file

    # Create mapping node to adjust texture coordinates
    mapping_node = nodes.new(type='ShaderNodeMapping')
    mapping_node.location = (-200, 0)
    mapping_node.inputs['Scale'].default_value = (0.1, 0.1, 0.1)  # Adjust scale as needed

    # Create texture coordinate mapping
    material.node_tree.links.new(tex_coord_node.outputs['Generated'], mapping_node.inputs['Vector'])
    material.node_tree.links.new(mapping_node.outputs['Vector'], image_texture_node.inputs['Vector'])

    # Create output node
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (200, 0)
    material.node_tree.links.new(image_texture_node.outputs['Color'], output_node.inputs['Surface'])

    return material


def assign_material_to_objects(material):
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            if obj.data.materials:
                # If the object already has materials assigned, replace the first material slot with the new material
                obj.data.materials[0] = material
            else:
                # If the object has no materials assigned, append the new material to its material slots
                obj.data.materials.append(material)

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
    neck_start_radius: bpy.props.FloatProperty(name="Start Radius", default=1.5, min=0.0)
    neck_end_radius: bpy.props.FloatProperty(name="End Radius", default=0.2, min=0.0)
    neck_wave_amplitude: bpy.props.FloatProperty(name="Wave Amplitude", default=0.1, min=0.0)
    neck_wave_frequency: bpy.props.FloatProperty(name="Wave Frequency", default=60, min=0.0)
    neck_num_verts: bpy.props.IntProperty(name="Number of Vertices", default=100, min=3)

    # Tail Properties
    tail_length: bpy.props.FloatProperty(name="Length", default=5.0, min=0.0)
    tail_start_radius: bpy.props.FloatProperty(name="Start Radius", default=1.5, min=0.0)
    tail_tip_radius: bpy.props.FloatProperty(name="Tip Radius", default=0.01, min=0.0)
    tail_wave_amplitude: bpy.props.FloatProperty(name="Wave Amplitude", default=0.2, min=0.0)
    tail_wave_frequency: bpy.props.FloatProperty(name="Wave Frequency", default=50, min=0.0)
    tail_num_verts: bpy.props.IntProperty(name="Number of Vertices", default=100, min=3)

    # Leg Properties
    thigh_height: bpy.props.FloatProperty(name="Thigh Height", default=1.5, min=0.0)
    shin_height: bpy.props.FloatProperty(name="Shin Height", default=5.0, min=0.0)
    foot_height: bpy.props.FloatProperty(name="Foot Height", default=0.5, min=0.0)
    thigh_radius: bpy.props.FloatProperty(name="Thigh Radius", default=0.2, min=0.0)
    shin_radius: bpy.props.FloatProperty(name="Shin Radius", default=0.2, min=0.0)
    foot_radius: bpy.props.FloatProperty(name="Foot Radius", default=0.1, min=0.0)
    leg_distance: bpy.props.FloatProperty(name="Leg Distance", default=0.0, min=0.0)
    leg_height: bpy.props.FloatProperty(name="Leg Height", default=0.0, min=0.0)

    # Head Properties
    head_num_segments: bpy.props.IntProperty(name="Number of Segments", default=200, min=3)
    head_num_rings: bpy.props.IntProperty(name="Number of Rings", default=100, min=3)
    
    #Wing Properties
    wing_distance: bpy.props.FloatProperty(name="Wing Distance", default=0.1, min=0.0)
    wing_height: bpy.props.FloatProperty(name="Wing Height", default=1.0, min=0.0)
    wing_length: bpy.props.FloatProperty(name="Wing Length", default=10.0, min=0.0)
    wing_thickness: bpy.props.FloatProperty(name="Wing Thickness", default=0.1, min=0.0)
    wing_start_width: bpy.props.FloatProperty(name="Wing Start Width", default=2.0, min=0.0)
    wing_end_width: bpy.props.FloatProperty(name="Wing End Width", default=1.0, min=0.0)
    
    #Material Property
    material_path: bpy.props.StringProperty(name="Material Path", default="", subtype='FILE_PATH')


# Define the panel to display the creature properties
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
        layout.prop(props, "neck_start_radius")
        layout.prop(props, "neck_end_radius")
        layout.prop(props, "neck_wave_amplitude")
        layout.prop(props, "neck_wave_frequency")
        layout.prop(props, "neck_num_verts")

        # Tail Properties
        layout.label(text="Tail Properties:")
        layout.prop(props, "tail_start_radius")
        layout.prop(props, "tail_length")
        layout.prop(props, "tail_tip_radius")
        layout.prop(props, "tail_wave_amplitude")
        layout.prop(props, "tail_wave_frequency")
        layout.prop(props, "tail_num_verts")

        # Leg Properties
        layout.label(text="Leg Properties:")
        layout.prop(props, "thigh_height")
        layout.prop(props, "shin_height")
        layout.prop(props, "foot_height")
        layout.prop(props, "thigh_radius")
        layout.prop(props, "shin_radius")
        layout.prop(props, "foot_radius")

        # Head Properties
        layout.label(text="Head Properties:")
        layout.prop(props, "head_num_segments")
        layout.prop(props, "head_num_rings")
        
        #Wing Properties
        layout.label(text="Wing Properties:")
        layout.prop(props, "wing_distance")
        layout.prop(props, "wing_height")
        layout.prop(props, "wing_length")
        layout.prop(props, "wing_thickness")
        layout.prop(props, "wing_start_width")
        layout.prop(props, "wing_end_width")
        
        #Material Properties
        layout.prop(props, "material_path", text="Material File")

        layout.operator("object.generate_creature", text="Generate Creature")


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
        
        neck_obj = create_neck(
            start_center=top_center,
            start_radius=top_radius,
            length=props.neck_length,
            end_radius=props.neck_end_radius,
            orientation='x',
            wave_amplitude=props.neck_wave_amplitude,
            wave_frequency=props.neck_wave_frequency,
            num_verts=props.neck_num_verts
        )

        tail_obj = create_tail(
            start_center=bottom_center,
            start_radius=top_radius,
            length=props.tail_length,
            tip_radius=props.tail_tip_radius,
            wave_amplitude=props.tail_wave_amplitude,
            wave_frequency=props.tail_wave_frequency,
            num_verts=props.tail_num_verts
        )
        
        # Generate the legs
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
            leg_distance=leg_distance,
            leg_height=0.1,
            thigh_height=thigh_height,
            shin_height=shin_height,
            foot_height=foot_height,
            thigh_radius=thigh_radius,
            shin_radius=shin_radius,
            foot_radius=foot_radius
        )

        # Attach head to the body
        head_obj = create_and_attach_head(body_obj, props.body_length + props.neck_length)
        
        wing_attachment_points = visualize_wing_points(body_obj, 
            wing_distance= props.wing_distance, 
            wing_height= props.wing_height, 
            wing_length= props.wing_length, 
            wing_thickness= props.wing_thickness, 
            start_width = props.wing_start_width, 
            end_width = props.wing_end_width
        )

        # Rotate objects as needed
        body_obj.rotation_euler = (math.radians(-90), 0, 0)
        neck_obj.rotation_euler = (math.radians(180), 0, 0)
        tail_obj.rotation_euler = (math.radians(-180), 0, 0)
        head_obj.rotation_euler = (0, 0, math.radians(90))

        bpy.context.view_layer.objects.active = body_obj
        bpy.ops.transform.rotate(value=-math.radians(90), orient_axis='X')
        
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
    
# Register the PropertyGroup and Panel classes
def register():
    bpy.utils.register_class(CreatureProperties)
    bpy.utils.register_class(CreaturePropertiesPanel)
    bpy.utils.register_class(OBJECT_OT_GenerateCreature)
    bpy.types.Scene.creature_properties = bpy.props.PointerProperty(type=CreatureProperties)

def unregister():
    bpy.utils.unregister_class(CreatureProperties)
    bpy.utils.unregister_class(CreaturePropertiesPanel)
    bpy.utils.unregister_class(OBJECT_OT_GenerateCreature)
    del bpy.types.Scene.creature_properties
    
if __name__ == "__main__":
        
    register()
