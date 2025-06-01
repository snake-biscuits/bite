#version 450 core
layout (location = 0) in vec2 vertexPosition;

out vec2 position;

void main()
{
    position = vertexPosition;
    gl_Position = vec4(vertexPosition, 0.0, 1.0);
}
