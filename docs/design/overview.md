# Architecture

Subcomponent architecture and interfaces.

## Harvester Data Sources / Workflows

As described in the overall building block architecture, the concept of the Harvester Data Source is represented by a Harvester workflow implementation. The inital set of Harvester Data Sources / Workflows is provided here. With DLR terrabyte as an operational platform for the Registration building block, this selection is primarily driven by the data requirements of the terrabyte users.

### Sentinel-1 SLC/GRD, Sentinel-2 L1C/L2A

| | |
| ---------| ---- |
| Provider | CDSE |
| API | OData https://datahub.creodias.eu/odata/v1 |
| Search Parameters | `PublicationDate`, `Online`, `Name` with `$expand=Attributes` option |
| Download | S3 (urls are retrieved from search results) |

### Landsat

| | |
| ---------| ---- |
| Provider | USGS |
| API      | STAC https://landsatlook.usgs.gov/stac-server |
| Search Parameters | `created` timestamp with [STAC API Query extension](https://github.com/stac-api-extensions/query) |
| Download | Utilization of [USGS M2M](https://m2m.cr.usgs.gov/) service to retrieve download URLs |

### MODIS

| | |
| ---------| ---- |
| Provider | NASA |
| API | CMR Search https://cmr.earthdata.nasa.gov/search/granules |
| Search Parameters | `production_date`, `updated_since` |
| Download | NASA DAAC |


### Other

The Resource Registration BB is extensible for other datasets and providers, that need to be integrated for harvesting. In general, Harvester Data Sources / Workflows will support the following metadata sources for harvesting:
- OGC API Records
- STAC
- OpenSearch
- OData?

Downloading will be supported from the following sources:
- S3 object storage
- HTTP
- Filesystem
- Swift object storage
