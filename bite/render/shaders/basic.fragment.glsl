// https://learnopengl.com/Advanced-Lighting/HDR
#version 450 core
layout (location = 0) out vec4 outColour;

in vec2 position;

uniform sampler2D texture0;

void main()
{
    vec2 uv = (position + 1) / 2;
    vec3 hdrColour = texture(texture0, uv).rgb;
    // exposure tone mapping
    // TODO: get exposure from a uniform
    const float exposure = 1.0;
    vec3 ldrColour = 1 - exp(-hdrColour * exposure);
    // gamma correction
    const float gamma = 2.2;
    ldrColour = pow(ldrColour, vec3(1 / gamma));
    outColour = vec4(ldrColour, 1);
}
