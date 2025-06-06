# **Bi**kkie's **Te**xture and Material Format Tool

Python library for parsing textures and materials for game modding


## Supported Formats

> NOTE: currently only supports a narrow spec of these formats

| Extension | Name |
| :--- | :--- |
| `.dds` | Direct Draw Surface |
| `.pvr` | PowerVR Texture |
| `.vtf` | Valve Texture Format |


## Planned Formats

| Extension | Name |
| :--- | :--- |
| `.vmt` | Valve Material |

> TODO: Also some form of `.rpak` material (`.json` / `.msw` / `.uber`)


## Similar Tools

If you just want a tool for one specific format, try these:
 - `.dds`
   * [texconv](https://github.com/Microsoft/DirectXTex/wiki/Texconv)
 - `.pvr`
   * [pvr2image](https://github.com/VincentNLOBJ/pvr2image)
 - `.vtf`
   * [VTFEdit](https://valvedev.info/tools/vtfedit/)
   * [VTFLib](https://github.com/NeilJed/VTFLib)


## Installation

To use the latest **unstable** version, clone with `git`:
```
$ git clone git@github.com:snake-biscuits/bite.git
```

You can also clone with `pip`:

```
$ pip install git+https://github.com/snake-biscuits/bite.git
```

> NOTE: not ready for PyPI yet

> TODO: explain installing extras

<!--
Or, use the latest stable release (??? 2025 | 0.1.0 | Python 3.8-13):
```
$ pip install bite
```
-->


## Usage

```python
>>> import bite
>>> dds = bite.DDS.from_file("path/to/file.dds")
>>> if dds.is_cubemap:
...     raw_pixels = dds.mipmaps[bite.MipIndex(0, 0, None)]
... else:
...     raw_pixels = dds.mipmaps[bite.MipIndex(0, 0, bite.Face(0))]
... 
>>> width, height = dds.size
>>> # TODO: check `dds.format` so you can decode the pixels
>>> # --- `dds.format` is an `enum.Enum` subclass: `bite.dds.DXGI`
>>> # TODO: do something with the pixels
```
