# Harvester Tutorial: Part 1

## Workflow design with BPMN

### Flowable Design
   
- Login to Flowable Design
- First we must create a new app. Click the red "Create" button and fill the form as shown below and click "Create"

![Create App](../img/harvester-tutorial/flowable-design-create-app.png)

- Next we will create our first BPMN model. Click the red "Create" button and fill the form as shown below. Important is that we choose *Process* as Model Type here.

![Create BPMN Model](../img/harvester-tutorial/flowable-design-create-process.png)

- No we are in the BPMN editor and can start drawing our workflow model. If not shown, make sure that the Properties panel is visible on the right side. Your workspace should now look like as shown below:

![BPMN Editor](../img/harvester-tutorial/flowable-design-bpmn-editor.png)

- As you see, there is already a BPMN Start Event present. 

![Create External Worker Task](../img/harvester-tutorial/flowable-design-create-external-worker-task.png)

 
- Save to file
- We will utilize the Flowable REST API to deploy the workflow.