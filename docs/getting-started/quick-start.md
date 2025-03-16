# Quick Start

To try out the Resource Registration building block you can install it locally or deploy the full Kubernetes setup as described in the [EOEPCA Deployment Guide](https://deployment-guide.docs.eoepca.org/current/building-blocks/resource-registration/).

## Registration API

To setup a local copy of the Registration API follow the instructions provided [here](https://github.com/EOEPCA/registration-api?tab=readme-ov-file#getting-started). This component is build upon the [pygeoapi](https://pygeoapi.io/) project to offer the [OGC API - Processes](https://ogcapi.ogc.org/processes/) to the user. An introduction to the OGC API Processes can be found in the Registration API [User Guide](../user-guide/registration-api-usage.md).

## Harvester

You can setup a local copy of the Harvester component using Docker and Docker Compose:

1. Run the Flowable workflow engine on your machine as described in the [Flowable Docker documentation](https://github.com/flowable/flowable-engine/tree/main/docker).
3. Clone the [Harvester GitHub repository](https://github.com/EOEPCA/registration-harvester.git).
4. Deploy the BPMN workflow definitions contained in the `workflows` directory on your local Flowable instance. 
5. The  `docker-compose.yml` in the project root directory defines the worker processes for the workflows. Adapt the workflow-specific configuration files to your enviroment and start everything with `docker compose up`.

!!! info "USGS M2M user account"
    The Landsat workflow searches the [Landsat STAC API](https://landsatlook.usgs.gov/stac-server) and downloads the data from the [USGS Machine-to-Machine (M2M) API](https://m2m.cr.usgs.gov/). To access this system, a M2M user accout is required which can be created [here](https://ers.cr.usgs.gov/register). The credentials must be passed as the environment variables `M2M_USER` and `M2M_PASSWORD` to the worker processes.

!!! info "CDSE user account"
    The Sentinel workflow searches and downloads the data from the [CDSE OData API](https://datahub.creodias.eu/odata/v1). To access this API, a CDSE user accout is required which can be created [here](https://identity.dataspace.copernicus.eu/auth/realms/CDSE/login-actions/registration?client_id=cdse-public&tab_id=0kmNL363Fs4). The credentials must be passed as the environment variables `CDSE_USER` and `CDSE_PASSWORD` to the worker processes.
