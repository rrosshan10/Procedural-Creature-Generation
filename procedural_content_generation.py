import bpy
import bmesh
from math import cos, sin, pi, radians, sqrt, acos, atan2
import math
from mathutils import Matrix, Vector, Euler


def create_sphere(bm, center, radius, num_verts_theta=32, num_verts_phi=16):
    verts = []
    for i in range(num_verts_theta):
        theta = math.pi * i / (num_verts_theta - 1)
        for j in range(num_verts_phi):
            phi = 2 * math.pi * j / num_verts_phi
            x = center[0] + radius * math.sin(theta) * math.cos(phi)
            y = center[1] + radius * math.sin(theta) * math.sin(phi)
            z = center[2] + radius * math.cos(theta)
            vert = bm.verts.new((x, y, z))
            verts.append(vert)
    return verts

def create_faces(bm, verts, num_verts_theta, num_verts_phi):
    for i in range(len(verts) - num_verts_phi):
        if (i + 1) % num_verts_phi == 0:
            continue
        v1 = verts[i]
        v2 = verts[i + 1]
        v3 = verts[i + num_verts_phi]
        v4 = verts[i + num_verts_phi + 1]
        bm.faces.new([v1, v2, v4, v3])
        
    # Closing the sphere
    bm.faces.new(verts[:num_verts_phi])
    bm.faces.new(verts[-num_verts_phi:][::-1])

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

def create_head(center, radius, scale_x=1.0, scale_y=1.0, scale_z=1.0, num_verts_theta=100, num_verts_phi=100):
    # Apply scaling to the radius
    scaled_radius_x = radius * scale_x
    scaled_radius_y = radius * scale_y
    scaled_radius_z = radius * scale_z

    # Create a new mesh and bmesh
    mesh = bpy.data.meshes.new("Head")
    bm = bmesh.new()

    # Create sphere vertices
    verts = create_sphere(bm, center, radius, num_verts_theta, num_verts_phi)

    # Apply scaling to the vertices
    for v in verts:
        v.co.x *= scale_x
        v.co.y *= scale_y
        v.co.z *= scale_z

    # Create sphere faces
    create_faces(bm, verts, num_verts_theta, num_verts_phi)

    # Update the bmesh and create the mesh
    bm.to_mesh(mesh)
    mesh.update()

    # Link the mesh to a new object
    obj = bpy.data.objects.new("Head_Object", mesh)
    bpy.context.collection.objects.link(obj)

    return obj


if __name__ == "__main__":
    
    body_height = 0.0

    body_obj, top_center, bottom_center, last_center, top_radius = create_body(
        length=15.0, start_radius=1.9, max_radius=1.5, wave_amplitude=0.3, wave_frequency=20, num_verts=100
    )
    
    body_dimensions = body_obj.dimensions
    body_length = body_dimensions[0]
    top_center = (body_length, 0, 0)
    
    print(body_length)

    # Create tail
    tail_obj = create_tail(
        start_center=bottom_center, 
        start_radius=top_radius, 
        length=2.0, 
        tip_radius=0.01, 
        wave_amplitude=0.2, 
        wave_frequency=50, 
        num_verts=100
    )
    # Make tail the child of the body
    tail_obj.parent = body_obj
    
    # Create neck
    neck_obj = create_neck(
        start_center=top_center, 
        start_radius=top_radius, 
        length=1.5, 
        end_radius=0.2, 
        orientation='x', 
        wave_amplitude=0.1, 
        wave_frequency=15, 
        num_verts=100
    )
    
    neck_dimensions = neck_obj.dimensions
    neck_length = neck_dimensions[0] # Length of the neck segment
    neck_position = Vector(top_center) + Vector((neck_length, 0, 0))
    print('n', neck_position)
    # Make neck the child of the body
    neck_obj.parent = body_obj
    
    thigh_height = 1.5  # Height of the thigh segment of the legs
    shin_height = 5.0   # Height of the shin segment of the legs
    foot_height = 0.5   # Height of the foot segment of the legs
    thigh_radius = 0.2  # Radius of the thigh segment of the legs
    shin_radius = 0.2   # Radius of the shin segment of the legs
    foot_radius = 0.1   # Radius of the foot segment of the legs
    leg_distance = 0.0 # Distance of the legs from the body's central axis along the Z-axis
    leg_height = 0.0

    attachment_points = visualize_leg_points(body_obj, leg_distance=leg_distance, leg_height=0.1, thigh_height=thigh_height, shin_height=shin_height, foot_height=foot_height, thigh_radius=thigh_radius, shin_radius=shin_radius, foot_radius=foot_radius)
    
    head_radius = 4.5  # Assuming uniform scaling along all axes
    head_position = neck_obj.matrix_world @ Vector(( neck_position[0], 0, 0))
    print(head_position)

    # Calculate the radius of the head based on some predetermined value
     # You can adjust this value as needed

    # Call the create_head function to create the head object
    head_obj = create_head(head_position, head_radius, scale_x=1.2, scale_y=1.5, scale_z=1.0)
        
    body_obj.rotation_euler = (radians(-90), 0, 0)
    neck_obj.rotation_euler = (radians(90), 0, 0)
    tail_obj.rotation_euler = (radians(-180), 0, 0)
    head_obj.rotation_euler = (radians(-90), 0, 0)
    
    
    # Rotate the entire object by -90 degrees on the x-axis
    bpy.context.view_layer.objects.active = body_obj
    bpy.ops.transform.rotate(value=-math.radians(90), orient_axis='X')
