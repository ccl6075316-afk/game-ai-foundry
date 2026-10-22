// Static imported mesh attributes, independent of the GPU skin pose.
uniform sampler2D rest114_positions:filter_nearest,repeat_disable;
uniform sampler2D rest114_normals:filter_nearest,repeat_disable;
uniform sampler2D rest114_uvs:filter_nearest,repeat_disable;
uniform ivec2 rest114_size;
uniform int rest114_count;
varying vec3 rest114_position;
varying vec3 rest114_normal;
varying float rest114_error;
