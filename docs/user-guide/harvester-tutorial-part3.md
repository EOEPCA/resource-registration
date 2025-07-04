# Harvester Developer Guide Part 3 - Deployment and workflow execution

This chapter covers the steps necessary to run the workflow we implemented in this tutorial. 

## Deployment of BPMN engine (Flowable) and worker

First, the BPMN engine Flowable and the worker must be deployed. Flowable is responsible for orchestrating and managing the workflow tasks where the worker executes the actual work which needs to be done in each task. A simple Docker Compose setup is part of the Registration Harvester can be found [here](https://github.com/EOEPCA/registration-harvester/blob/main/docker-compose.yml). A more sophisticated deployment for Kubernetes using Helm charts is also available, see [Flowable Helm chart](https://github.com/flowable/helm) and [Registration Harvester Helm](https://github.com/EOEPCA/helm-charts-dev/tree/develop/charts/registration-harvester) chart.

During the remaing part of this section it is assmued, that the Docker Compose deployment was done on localhost using the compose file mentioned above.

## Deployment of example workflow BPMN

```
curl -X POST \
  --user "eoepca:eoepca" \
  -F upload=@harvester-tutorial.bpmn \
  http://localhost:8082/flowable-rest/service/repository/deployments
```

## Execution of example workflow

To execute the workflow we must create a process instance of our BPMN process which is referenced by the process definition key. This key is derived from the process id which is defined in the BPMN file itself. In our case the key is `simpleHarvestingWorkflow`.

```
curl -X POST \ 
  --header "Content-Type: application/json" \
  --user "eoepca:eoepca" \
  --data '{"processDefinitionKey":"simpleHarvestingWorkflow"}' \
  http://localhost:8082/flowable-rest/service/runtime/process-instances
```

To check if there is a running instance run:

```
curl -X GET --user "eoepca:eoepca" http://localhost:8082/flowable-rest/service/runtime/process-instances
```

If everythin went successful, our workflow should already be running and logging the STAC items which has been returned from the STAC search in the "Disovery STAC Items" workflow task. To the logs of the worker just execute `docker compose logs`.