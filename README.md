# bite

Short for "**Bi**kkie's **Te**xture and Material Format Tool"

Python library for parsing textures and materials for game modding


## Supported Formats

> NOTE: currently only supports a narrow spec of these formats

| Extension | Name                      |
| :-------- | :------------------------ |
| `.dds`    | Direct Draw Surface       |
| `.pvr`    | PowerVR Texture           |
| `.vms`    | Dreamcast VMU IconDataVMS |
| `.vtf`    | Valve Texture Format      |


## Planned Formats

| Extension | Name           |
| :-------- | :------------- |
| `.json`   | Rpak Material  |
| `.vmt`    | Valve Material |

> NOTE: `Matl` parses the [RSX](https://github.com/r-ex/rsx) `.json` format
> -- similar to the [RePak](https://github.com/r-ex/RePak) `.json` format

## Similar Tools

If you just want a tool for one specific format, try these:
 - `.dds`
   * [texconv](https://github.com/Microsoft/DirectXTex/wiki/Texconv)
 - `.pvr`
   * [pvr2image](https://github.com/VincentNLOBJ/pvr2image)
 - `.vtf`
   * [VTFEdit](https://valvedev.info/tools/vtfedit/)
   * [VTFLib](https://github.com/NeilJed/VTFLib)
 - `.vms`
   * [VMU TOOL PC](https://github.com/sizious/vmu-tool-pc)


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
>>> dds.parse()
>>> mip = dds.default_mip()
>>> raw_pixels = dds.mipmaps[mip]
>>> width, height = dds.mip_size(mip)
>>> # TODO: check `dds.header.format` so you can decode the pixels
>>> # --- `dds.header.format` is an `enum.Enum` subclass: `bite.dds.DXGI`
>>> # TODO: do something with the pixels
```
