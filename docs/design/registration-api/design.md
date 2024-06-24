# Design

[pygeoapi](https://pygeoapi.io) is a Python server implementation of the OGC API suite of standards. The project emerged as part of the next generation [OGC API](https://ogcapi.ogc.org) efforts in 2018 and provides the capability for organizations to deploy a RESTful OGC API endpoint using OpenAPI, GeoJSON, and HTML. pygeoapi is [open source](https://opensource.org) and released under an MIT license.

Features
--------

* out of the box modern OGC API server
* certified OGC Compliant and Reference Implementation
    * OGC API - Features
    * OGC API - Environmental Data Retrieval
* additionally implements
    * OGC API - Coverages
    * OGC API - Maps
    * OGC API - Tiles
    * OGC API - Processes
    * OGC API - Records
    * SpatioTemporal Asset Library
* out of the box data provider plugins for rasterio, GDAL/OGR, Elasticsearch, PostgreSQL/PostGIS
* easy to use OpenAPI / Swagger documentation for developers
* supports JSON, GeoJSON, HTML and CSV output
* supports data filtering by spatial, temporal or attribute queries
* easy to install: install a full implementation via `pip` or `git`
* simple YAML configuration
* easy to deploy: via UbuntuGIS or the official Docker image
* flexible: built on a robust plugin framework to build custom data connections, formats and processes
* supports any Python web framework (included are Flask [default], Starlette)
* supports asynchronous processing and job management (OGC API - Processes)
