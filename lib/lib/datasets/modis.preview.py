import os
from osgeo import gdal

# todo: modis.preview wird von docgenerator nicht gefunden. Punkt im Namen müsste gegen anderes Zeichen ersetzt werden

modis_previews = {
    "mod09ga": {
        "sample": (
            "https://modis-samples.fra1.cdn.digitaloceanspaces.com/"
            "MOD09GA.061/MOD09GA.A2023177.h20v05.061.2023179044546.hdf"
        ),
        "description": "MODIS/Terra Surface Reflectance Daily L2G Global 1km and 500m SIN Grid",
        "bands": ["sur_refl_b01_1", "sur_refl_b04_1", "sur_refl_b03_1"],
        "cmap": None,
    },
    "myd09ga": {
        "sample": (
            "https://modis-samples.fra1.cdn.digitaloceanspaces.com/"
            "MYD09GA.061/MYD09GA.A2023168.h29v05.061.2023170035115.hdf"
        ),
        "description": "MODIS/Aqua Surface Reflectance Daily L2G Global 1km and 500m SIN Grid",
        "bands": ["sur_refl_b01_1", "sur_refl_b04_1", "sur_refl_b03_1"],
        "cmap": None,
    },
    "mod09gq": {
        "sample": (
            "https://modis-samples.fra1.cdn.digitaloceanspaces.com/"
            "MOD09GQ.061/MOD09GQ.A2023177.h20v05.061.2023179044546.hdf"
        ),
        "description": "MODIS/Terra Surface Reflectance Daily L2G Global 250m SIN Grid",
        "bands": ["sur_refl_b01_1", "sur_refl_b01_1", "sur_refl_b02_1"],
        "cmap": None,
    },
    "myd09gq": {
        "sample": (
            "https://modis-samples.fra1.cdn.digitaloceanspaces.com/"
            "MYD09GQ.061/MYD09GQ.A2023126.h29v06.061.2023128033751.hdf"
        ),
        "description": "MODIS/Aqua Surface Reflectance Daily L2G Global 250m SIN Grid",
        "bands": ["sur_refl_b01_1", "sur_refl_b01_1", "sur_refl_b02_1"],
        "cmap": None,
    },
    "mod10a1": {
        "sample": (
            "https://modis-samples.fra1.cdn.digitaloceanspaces.com/"
            "MOD10A1.061/MOD10A1.A2023113.h23v04.061.2023115044355.hdf"
        ),
        "description": "MODIS/Terra Snow Cover Daily L3 Global 500m SIN Grid",
        "bands": ["NDSI_Snow_Cover"],
        "cmap": [
            (0, (255, 255, 255), 100, (255, 255, 0)),
            (101, (56, 56, 56), 199, (56, 56, 56)),
            (200, (30, 144, 255), 250, (0, 0, 205)),
        ],
    },
    "myd10a1": {
        "sample": (
            "https://modis-samples.fra1.cdn.digitaloceanspaces.com/"
            "MYD10A1.061/MYD10A1.A2023175.h24v05.061.2023177034319.hdf"
        ),
        "description": "MODIS/Aqua Snow Cover Daily L3 Global 500m SIN Grid",
        "bands": ["NDSI_Snow_Cover"],
        "cmap": [
            (0, (255, 255, 255), 100, (255, 255, 0)),
            (101, (56, 56, 56), 199, (56, 56, 56)),
            (200, (30, 144, 255), 250, (0, 0, 205)),
        ],
    },
    "mod13a2": {
        "sample": (
            "https://modis-samples.fra1.cdn.digitaloceanspaces.com/"
            "MOD13A2.061/MOD13A2.A2023145.h20v05.061.2023164003951.hdf"
        ),
        "description": "MODIS/Terra Vegetation Indices 16-Day L3 Global 1km SIN Grid",
        "bands": ['"1 km 16 days MIR reflectance"', '"1 km 16 days NIR reflectance"', '"1 km 16 days red reflectance"'],
        "cmap": None,
    },
    "myd13a2": {
        "sample": (
            "https://modis-samples.fra1.cdn.digitaloceanspaces.com/"
            "MYD13A2.061/MYD13A2.A2023153.h29v12.061.2023170141456.hdf"
        ),
        "description": "MODIS/Aqua Vegetation Indices 16-Day L3 Global 1km SIN Grid",
        "bands": ['"1 km 16 days MIR reflectance"', '"1 km 16 days NIR reflectance"', '"1 km 16 days red reflectance"'],
        "cmap": None,
    },
    "mod13a3": {
        "sample": (
            "https://modis-samples.fra1.cdn.digitaloceanspaces.com/"
            "MOD13A3.061/MOD13A3.A2023121.h20v05.061.2023164011854.hdf"
        ),
        "description": "MODIS/Terra Vegetation Indices Monthly L3 Global 1km SIN Grid",
        "bands": ['"1 km monthly MIR reflectance"', '"1 km monthly NIR reflectance"', '"1 km monthly red reflectance"'],
        "cmap": None,
    },
    "myd13a3": {
        "sample": (
            "https://modis-samples.fra1.cdn.digitaloceanspaces.com/"
            "MYD13A3.061/MYD13A3.A2023032.h29v12.061.2023074111018.hdf"
        ),
        "description": "MODIS/Aqua Vegetation Indices Monthly L3 Global 1km SIN Grid",
        "bands": ['"1 km monthly MIR reflectance"', '"1 km monthly NIR reflectance"', '"1 km monthly red reflectance"'],
        "cmap": None,
    },
    "mod13q1": {
        "sample": (
            "https://modis-samples.fra1.cdn.digitaloceanspaces.com/"
            "MOD13Q1.061/MOD13Q1.A2023161.h20v05.061.2023177232655.hdf"
        ),
        "description": "MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid",
        "bands": ['"250m 16 days MIR reflectance"', '"250m 16 days NIR reflectance"', '"250m 16 days red reflectance"'],
        "cmap": None,
    },
    "myd13q1": {
        "sample": (
            "https://modis-samples.fra1.cdn.digitaloceanspaces.com/"
            "MYD13Q1.061/MYD13Q1.A2023137.h29v12.061.2023154011314.hdf"
        ),
        "description": "MODIS/Aqua Vegetation Indices 16-Day L3 Global 250m SIN Grid",
        "bands": ['"250m 16 days MIR reflectance"', '"250m 16 days NIR reflectance"', '"250m 16 days red reflectance"'],
        "cmap": None,
    },
}


def create_preview(infile: str, outdir: str, outres: int) -> str:
    """
    Creates an 8-Bit RGB COG preview of the MODIS hdf infile

    Args:
        infile (str): Path to input HDF
        outdir (str): Output directory
        outres (int): Resolution in meters

    Returns:
        preview (str): Path to preview COG
    """
    basename = os.path.splitext(os.path.basename(infile))[0]
    preview = os.path.join(outdir, f"{basename}_preview.tif")
    product_id = basename.split(".")[0].lower()
    # identify product based on MODIS naming convention
    product = modis_previews[product_id]
    # collect RGB band hrefs
    band_hrefs = []
    mds = gdal.Open(infile)
    sds = mds.GetSubDatasets()
    for b in product["bands"]:
        for sd, _ in sds:
            if b == sd.split(":")[-1]:
                band_hrefs.append(sd)
    mds = None
    # extract bands incl. statistics into RGB in-memory stack
    bands = []
    vmins = []
    vmaxs = []
    for band_href in band_hrefs:
        band = gdal.Open(band_href)
        vmin, vmax, _, _ = band.GetRasterBand(1).GetStatistics(True, True)
        vmins.append(vmin)
        vmaxs.append(vmax)
        bands.append(band)
    scale_params = [min(vmins), max(vmaxs), 0, 255]
    vrt = os.path.join("/vsimem", f"{basename}_preview.vrt")
    vrt_options = gdal.BuildVRTOptions(separate=True, hideNodata=True, resolution="user", xRes=outres, yRes=outres)
    gdal.BuildVRT(vrt, bands, options=vrt_options)
    # reset scale value, add colormap if appropriate
    rgb_stack = gdal.Open(vrt)
    for i in range(rgb_stack.RasterCount):
        rgb_stack.GetRasterBand(i + 1).SetScale(1.0)
    if product["cmap"]:
        b1 = rgb_stack.GetRasterBand(1)
        colors = gdal.ColorTable()
        for ramp in product["cmap"]:
            colors.CreateColorRamp(*ramp)
        b1.SetRasterColorTable(colors)
        b1.SetRasterColorInterpretation(gdal.GCI_PaletteIndex)
    rgb_stack = None
    # scale into 8-Bit COG
    translate_options = gdal.TranslateOptions(format="COG", outputType=gdal.GDT_Byte, scaleParams=[scale_params])
    gdal.Translate(preview, vrt, options=translate_options)
    gdal.Unlink(vrt)
    for band in bands:
        band = None
    return preview


# hdfs = [modis_previews[product]['sample'] for product in modis_previews]
# for hdf in hdfs:
#    create_preview(hdf, r'D:\_temp', 2000)
#    print(f'{os.path.split(hdf)[1]} done')
# print('done')
