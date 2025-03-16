# Design

The harvester is implemented as workflows in the Flowable BPMN platform. Flowable Platform is a flexible framework for workflow and process automation. Its core is a native Business Process Modelling Notation (BPMN) 2.0 process engine that runs inside the Java Virtual Machine. Workflows need to be defined with the BPMN specification that supports parallel workflow steps, branching, error handling, etc. A workflow step can be set to type “external” to allow an individual worker to fetch tasks for a specific workflow step. This worker connects to the REST API, fetches tasks, and returns the status (e.g., completed, failed, error). Failed workflow steps can be automatically retried from the Flowable process engine. Errors can be modelled in the BPMN diagram, e.g., asking an operator how to proceed as a manual user task.

The Flowable platform has the ability to separate the workflow engine from the workflow step execution, where the central workflow engine takes care of the workflow step orchestration. The workflow steps are implemented as Flowable Python Worker, allowing a seamless usage of various EO related upstream packages provided by Python's geospatial community.

On top of the workflow engine, a stack of tools for operations and monitoring are available. The following tools are used for the harvester:

- Flowable Engine as the core component responsible for executing BPMN workflows
- REST API provides remote access to running processes or to start processes
- Flowable Design as a web application that allows users and developers to design and configure a workflow
- Flowable External Client Python as a Python library to communicate with the Flowable REST API, which can be launched anywhere with access to the Flowable REST API.

Each workflow can be triggered by the Registration API and can utilize the Resource Discovery API for the registration of the harvested resources.

## Harvester Data Sources / Workflows

As described in the building block [architecture](overview.md), the concept of the Harvester Data Source is represented by a workflow. It provides an integration with a specific data source or provider and enables customised support for resource harvesting and interpretation. It is designed to be pluggable into the Harvester for a given deployment, making the Resource Registration BB easily extensible for other datasets, that need to be made available for discovery and access.

### Initial Workflows

The initial version of the Harvester includes a set of workflows for harvesting and registration of Sentinel data from the Copernicus Dataspace Ecosystem (CDSE), Landsat data from USGS and MODIS data from NASA LPDAAC. The following table lists the providers and APIs that will be supported by these workflows.

|                   | Sentinel | Landsat | MODIS       |
| ------------------| -------- | ------- | ----------- | 
| Provider          | CDSE     | USGS    | NASA        |
| API               | OData¹   | STAC²   | CMR Search³ |
| Search Parameters | `PublicationDate`, `Online`, `Name` with `$expand=Attributes` option | `created` timestamp with [STAC API Query extension](https://github.com/stac-api-extensions/query) | `production_date`, `updated_since` |
| Download          | S3 (urls are retrieved from search results) | Utilization of [USGS M2M](https://m2m.cr.usgs.gov/) service to retrieve download URLs | NASA DAAC |

¹ https://datahub.creodias.eu/odata/v1

² https://landsatlook.usgs.gov/stac-server

³ https://cmr.earthdata.nasa.gov/search/granules

