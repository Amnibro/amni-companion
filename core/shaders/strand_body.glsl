layout(std430, set = 0, binding = 2) readonly buffer Sim { vec4 sm[]; };
layout(std430, set = 0, binding = 3) readonly buffer Sdf { vec2 sdf[]; };
mat4 m4(uint o) { return mat4(sm[o], sm[o + 1u], sm[o + 2u], sm[o + 3u]); }
float sdv(uint off, ivec3 d, ivec3 c) { return sdf[off + uint((c.z * d.y + c.y) * d.x + c.x)].x; }
vec4 partSd(uint p, vec3 xb) {
	uint o = 20u + p * 12u;
	vec4 a = sm[o], b = sm[o + 1u];
	ivec3 d = ivec3(b.xyz);
	vec3 q = (xb - a.xyz) / a.w;
	if (any(lessThan(q, vec3(0.0))) || any(greaterThan(q, vec3(d - 1)))) return vec4(0.0, 0.0, 0.0, 1000.0);
	uint off = uint(b.w);
	ivec3 r = clamp(ivec3(floor(q + 0.5)), ivec3(0), d - 1);
	if (abs(sdf[off + uint((r.z * d.y + r.y) * d.x + r.x)].y - float(p)) > 0.5) return vec4(0.0, 0.0, 0.0, 1000.0);
	ivec3 c = min(ivec3(floor(q)), d - 2);
	vec3 f = q - vec3(c);
	float v000 = sdv(off, d, c), v100 = sdv(off, d, c + ivec3(1, 0, 0)), v010 = sdv(off, d, c + ivec3(0, 1, 0)), v110 = sdv(off, d, c + ivec3(1, 1, 0));
	float v001 = sdv(off, d, c + ivec3(0, 0, 1)), v101 = sdv(off, d, c + ivec3(1, 0, 1)), v011 = sdv(off, d, c + ivec3(0, 1, 1)), v111 = sdv(off, d, c + ivec3(1, 1, 1));
	float x00 = mix(v000, v100, f.x), x10 = mix(v010, v110, f.x), x01 = mix(v001, v101, f.x), x11 = mix(v011, v111, f.x);
	float y0 = mix(x00, x10, f.y), y1 = mix(x01, x11, f.y);
	vec3 g = vec3(mix(mix(v100 - v000, v110 - v010, f.y), mix(v101 - v001, v111 - v011, f.y), f.z), mix(x10 - x00, x11 - x01, f.z), y1 - y0) / a.w;
	return vec4(g, mix(y0, y1, f.z));
}
vec2 bodySd(vec3 x) {
	vec2 best = vec2(1000.0, 99.0);
	uint np = uint(sm[8].w);
	for (uint p = 0u; p < np; p++) {
		float s = partSd(p, (m4(23u + p * 12u) * vec4(x, 1.0)).xyz).w;
		if (s < best.x) best = vec2(s, float(p));
	}
	return best;
}
vec3 pushOut(vec3 x, uint p, float m) {
	uint o = 20u + p * 12u;
	vec3 xb = (m4(o + 3u) * vec4(x, 1.0)).xyz;
	vec4 s = partSd(p, xb);
	if (s.w >= m || dot(s.xyz, s.xyz) < 1e-8) return x;
	return (m4(o + 7u) * vec4(xb + normalize(s.xyz) * (m - s.w), 1.0)).xyz;
}
