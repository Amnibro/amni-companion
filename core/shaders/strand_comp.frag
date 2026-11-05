layout(set = 2, binding = 0) uniform sampler2D tex_hair;
layout(location = 0) out vec4 out_col;
void main() {
	out_col = texelFetch(tex_hair, ivec2(gl_FragCoord.xy), 0);
}
