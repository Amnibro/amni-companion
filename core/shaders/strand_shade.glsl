float hI0(float x) { float v = 0.0, x2i = 1.0, fi = 1.0, i4 = 1.0; for (int i = 0; i < 10; i++) { if (i > 1) fi *= float(i); v += x2i / (i4 * fi * fi); x2i *= x * x; i4 *= 4.0; } return v; }
float hLogI0(float x) { return x > 12.0 ? x + 0.5 * (-log(6.2831853) + log(1.0 / x) + 1.0 / (8.0 * x)) : log(hI0(x)); }
float hMp(float cti, float cto, float sti, float sto, float v) {
	float a = cti * cto / v, b = sti * sto / v;
	if (v <= 0.1) return exp(hLogI0(a) - b - 1.0 / v + 0.6931 + log(1.0 / (2.0 * v)));
	return exp(-b) * hI0(a) / ((exp(1.0 / v) - exp(-1.0 / v)) * v);
}
float hLogi(float x, float s) { float e = exp(-abs(x) / s); return e / (s * (1.0 + e) * (1.0 + e)); }
float hNp(float phi, float p, float s, float go, float gt) {
	float d = phi - (2.0 * p * gt - 2.0 * go + p * 3.14159265);
	d = d - 6.2831853 * floor((d + 3.14159265) / 6.2831853);
	float c = 1.0 / (1.0 + exp(-3.14159265 / s)) - 1.0 / (1.0 + exp(3.14159265 / s));
	return hLogi(d, s) / c;
}
float hFr(float ci, float eta) {
	ci = clamp(ci, 0.0, 1.0);
	float st = sqrt(max(0.0, 1.0 - ci * ci)) / eta, ct = sqrt(max(0.0, 1.0 - st * st));
	float rpa = (eta * ci - ct) / (eta * ci + ct), rpe = (ci - eta * ct) / (ci + eta * ct);
	return st >= 1.0 ? 1.0 : 0.5 * (rpa * rpa + rpe * rpe);
}
vec3 hSigma(vec2 m) { return m.x * vec3(0.419, 0.697, 1.37) + m.y * vec3(0.187, 0.4, 1.05); }
vec3 chiang(vec3 T, vec3 L, vec3 V, vec3 sig, float h, float bm, float bn, float al, out vec3 af, out vec3 ab) {
	float sto = clamp(dot(V, T), -0.9999, 0.9999), cto = sqrt(1.0 - sto * sto), sti = clamp(dot(L, T), -0.9999, 0.9999), cti = sqrt(1.0 - sti * sti);
	vec3 n0 = abs(T.y) < 0.9 ? vec3(0.0, 1.0, 0.0) : vec3(1.0, 0.0, 0.0), X = normalize(n0 - T * dot(n0, T)), Y = cross(T, X);
	float phi = atan(dot(L, Y), dot(L, X)) - atan(dot(V, Y), dot(V, X));
	float eta = 1.55, stt = sto / eta, ctt = sqrt(max(0.0, 1.0 - stt * stt));
	float etp = sqrt(max(eta * eta - sto * sto, 1e-4)) / cto, sgt = clamp(h / etp, -1.0, 1.0), cgt = sqrt(1.0 - sgt * sgt), gt = asin(sgt), go = asin(h);
	vec3 tr = exp(-sig * (2.0 * cgt / ctt));
	float f = hFr(cto * sqrt(1.0 - h * h), eta);
	vec3 A0 = vec3(f), A1 = (1.0 - f) * (1.0 - f) * tr, A2 = A1 * f * tr, A3 = A2 * f * tr / (vec3(1.0) - f * tr);
	af = A1;
	ab = A0 + A2 + A3;
	float v0 = (0.726 * bm + 0.812 * bm * bm + 3.7 * pow(bm, 20.0));
	v0 *= v0;
	float s = 0.626657 * (0.265 * bn + 1.194 * bn * bn + 5.372 * pow(bn, 22.0));
	float s0 = sin(al), c0 = sqrt(1.0 - s0 * s0), s1 = 2.0 * c0 * s0, c1 = c0 * c0 - s0 * s0, s2 = 2.0 * c1 * s1, c2 = c1 * c1 - s1 * s1;
	vec3 r = hMp(cti, abs(cto * c1 + sto * s1), sti, sto * c1 - cto * s1, v0) * A0 * hNp(phi, 0.0, s, go, gt);
	r += hMp(cti, abs(cto * c0 - sto * s0), sti, sto * c0 + cto * s0, 0.25 * v0) * A1 * hNp(phi, 1.0, s, go, gt);
	r += hMp(cti, abs(cto * c2 - sto * s2), sti, sto * c2 + cto * s2, 4.0 * v0) * A2 * hNp(phi, 2.0, s, go, gt);
	r += hMp(cti, cto, sti, sto, 4.0 * v0) * A3 * 0.1591549;
	return r;
}
