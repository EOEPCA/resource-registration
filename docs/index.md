# Introduction

In supporting the Reuse capability as one of the FAIR principles, the Resource Registration Building Block provides support for ingesting resources into the platform to that they can be discovered, accessed and used collaboratively.  These resources include, but are not limited to data (e.g., datasets, data cube, virtual data cube), workflows, Jupyter Notebooks, services, web applications, and documentation.

## About the Resource Registration Building Block

The _Resource Registration Building Block_ functions as follows:

* **Data management**: aligns with the same set of resource types as the _Resource Discovery Building Block_:
* **Cloud native storage**: references assets in object storage
* **Publish-Subscribe**: provides Publish and Subscribe workflow in alignment with event driven architecture principles and OGC efforts
* **Aggregation**: harvests metadata from existing sources including OGC API - Records, STAC and OGC OpenSearch, and provides extensibility for specific data sources
* **Transactions**: provides an API capable of create, update, replace and delete workflow for resources
* **Resource citation**: provides DOI registration against a given resource

## Capabilities

The relevant use cases for the Resource Registration Building Block focus on the management of resources from the local platform.

It comprises the following key components, each addressing specific aspects of EO resource management:

- **Registation API**: provides core resource management resources on the local platform
- **Harvester**: provides ingest and aggregation functionality of resources on the local remote platforms
- **API Gateway**: protects all APIs and connects to the Identity Management building block for authentication and authorization
