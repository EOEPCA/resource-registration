# Harvester Developer Guide Part 2 - Worker implementation with Python

This chapter covers implementing the tasks for the workflow we created in the [first part](harvester-tutorial-part1.md) of this tutorial. The workflow definition file and code samples can be found in the [Registration Harvester repository](https://github.com/EOEPCA/registration-harvester). 

## Understanding the `TaskHandler`

The TaskHandler (located in `worker.common.task_handler.py`) is the base class for all custom task implementations. When creating a new task, you'll primarily focus on overriding its execute method.

### The `execute` Method

The `execute(self, task: ExternalTask, config: dict) -> TaskResult` method is where the actual work of your task is performed. This is the only method you typically need to override in your custom handler.

* Purpose: To receive task details, perform the task's business logic, and return a result indicating success or failure, along with any output variables.
* Parameters:
    * `task: ExternalTask`: An object providing access to the current task details. Key uses include:
        * `task.get_task_id()`: The unique ID of the current task instance.
        * `task.get_topic_name()`: The name or ID of the task element from the BPMN workflow.
        * `task.get_variable("my_input_variable")`: To retrieve input variables passed from the workflow.
    * `config: dict`: A general configuration dictionary. While available, for handler-specific configurations, it is generally preferred to use the self.get_config() method (see below).
* Returns: A TaskResult object which informs the workflow engine about the task's outcome e.g.
  * success: `task.complete(global_variables={"variable_name": value})`
  * failure: `task.failure(error_message="...", error_details="...", max_retries=3, retry_timeout=60000)`

### Supporting Features from the Base TaskHandler

The TaskHandler base class provides some helpful features:

* Configuration Handling (init and get_config):
    * The base TaskHandler's constructor (init) automatically loads configurations specific to your handler class from the main `config.yaml` file (under `handlers.<YourHandlerClassName>`). It also handles subscription-related settings.
    * You can access these configurations within your execute method using `self.get_config(key: str, default=None)`. For example, `api_key = self.get_config("api_key")`.

So, when implementing a new task, your focus will be on the execute method, leveraging `task.get_variable()`, `self.get_config()`, and `task.complete` or `task.failure()` for outputs.

## Implementing the tasks for our example workflow

In general, for each workflow step modelled as external worker task, you have to do the following: 

1. Create a Handler Class

    * Create a new Python file (e.g., `my_custom_tasks.py`) or add to an existing one within the `src/worker/` directory structure (e.g., `src/worker/custom/tasks.py`).
    * Define a new class that inherits from `worker.common.task_handler.TaskHandler`.

2. Implement the execute Method

### Task implementation

For our tutorial example we have two tasks to implement, the "Discovery STAC Items" and the "Process STAC Item" task. For simplicity we will implement both handler classes in the same Python module as shown below. The full Python file is located [here](https://github.com/EOEPCA/registration-harvester/blob/main/src/worker/tutorial/tasks.py).


```python
class TutorialDiscoverItemsTaskHandler(TaskHandler):
    def execute(self, task: ExternalTask, config: dict) -> TaskResult:
        log_context = {
            "WORKER_ID": task.get_worker_id(),
            "TASK_ID": task.get_task_id(),
            "TOPIC_NAME": task.get_topic_name(),
        }
        log_with_context("Starting DiscoverItems task ...", log_context)

        try:
            # no input data needed for this task

            # get STAC API url from configuration
            api_url = self.get_config("service_url", "https://stac.dataspace.copernicus.eu/v1/")

            # 2. Perform task logic
            log_with_context(f"Searching STAC items using API: {api_url}", log_context)
            # stac search
            catalog = Client.open(api_url, headers=[])
            search = catalog.search(max_items=100, collections="sentinel-2-l2a", datetime="2025-07-02")
            items = list(search.items_as_dicts())

            # 3. Return success with output variables
            log_with_context("DiscoverItems task completed successfully.", log_context)
            return task.complete(global_variables={"items": items})

        except Exception as e:
            return task.failure(
                error_message="Error in TutorialDiscoverItemsTaskHandler",
                error_details=str(e),
                max_retries=0,
                retry_timeout=0,
            )

class TutorialProcessItemTaskHandler(TaskHandler):
    def execute(self, task: ExternalTask, config: dict) -> TaskResult:
        log_context = {
            "WORKER_ID": task.get_worker_id(),
            "TASK_ID": task.get_task_id(),
            "TOPIC_NAME": task.get_topic_name(),
        }
        log_with_context("Starting ProcessItem task ...", log_context)

        try:
            # 1. Get input variables
            item = task.get_variable("item")

            if not item:
                return task.failure(
                    error_message="Missing input variable",
                    error_details="The variable 'item' is missing",
                    max_retries=0,
                    retry_timeout=0,
                )

            # 2. Perform task logic: just logging the item
            log_with_context(f"Processing item {item}", log_context)

            # 3. Return success, no output variable produced by this task
            log_with_context("ProcessItem task completed successfully.", log_context)
            return task.complete()

        except Exception as e:
            return task.failure(
                error_message="Error in TutorialProcessItemTaskHandler",
                error_details=str(e),
                max_retries=0,
                retry_timeout=0,
            )
```

### Best practices

* **Logging:** Use `log_with_context` for all logging. Include `task.get_task_id()` and `task.get_topic_name()` in your `log_context` for better traceability.
* **Input Variables:** Retrieve any necessary input variables passed from the workflow using `task.get_variable("variable_name")`.
* **Configuration:** Access handler-specific configurations (defined in `config.yaml`) using `self.get_config("config_key", "default_value")`.
* **Business Logic:** Implement the core functionality of your task.
* **Error Handling:** Wrap your logic in a `try...except` block. If an error occurs, log it and return a failure result, preferably using `task.failure()`.
* **Return Result:** Use `task.complete(global_variables={})` and pass the output data in the `global_variables` dictionary back to the workflow.

## Configuring the Worker

After implementing your TaskHandler, you need to configure the worker to use it. This is done in the main configuration file (typically `etc/config.yaml`, or the path specified by the `CONFIG_FILE_PATH` environment variable).
The `SubscriptionManager` component automatically discovers and subscribes your handlers to specific topics based on this configuration.

### General structure of configuration file

* `topics`: This section maps topic names (which your BPMN tasks will publish to) to your handler classes.
    * Each key is a topic name (e.g., `my_custom_task_topic`).
    * For each topic, you must specify:
        * `module`: The fully qualified Python module path to your handler class (e.g., `worker.custom.tasks`).
        * `handler`: The class name of your handler (e.g., `MyCustomTaskHandler`).
  * `handlers`: This section provides specific configurations for individual TaskHandler implementations.
    * Each key is the class name of a handler (e.g., `MyCustomTaskHandler`).
    * Inside each handler's configuration, you can define key-value pairs. These values are accessible within that handler using `self.get_config("your_key")`.

### Configuration for example workflow

This sections provides the part of the configuration to bind our worker implementation to the tasks we defined in the BMPN model. The full configuration file can be found [here](https://github.com/EOEPCA/registration-harvester/blob/main/config-tutorial.yaml).

```yaml
# Bind the workflow steps defined in BPMN to a worker implementation by Job topic name
topics:
    tutorial_discover_items:                        # Job topic name defined in the BPMN for this task
        module: "worker.tutorial.tasks"             # Path to the .py file containing the handler implementation, dot-separated
        handler: "TutorialDiscoverItemsTaskHandler" # Name of the handler class
        lock_duration: 300000                       # Example: 5 minute lock duration for this task
        retries: 3                                  # If the task fails, the BPMN engine will retry 3 times
    tutorial_process_item:
        module: "worker.tutorial.tasks"               
        handler: "TutorialProcessItemTaskHandler"     
        lock_duration: 300000                         
        retries: 3                          

# Provide configuration specific to each handler, if needed
handlers:  
    TutorialDiscoverItemsTaskHandler:
        service_url: "https://my.api.service.com/v1/process"
        default_timeout_seconds: 60
```

### How it Works

1. The SubscriptionManager starts up.
2. It reads the `topics` section from the `config.yaml`.
3. For each topic entry, it dynamically imports the specified module and retrieves the handler class.
4. It instantiates your handler class. The `handlers` dictionary from the config is passed to the TaskHandler's constructor. The TaskHandler.__init__ method then filters out the configuration relevant to its specific class name.
5. The manager subscribes this handler instance to the specified topic, ready to process incoming jobs.

## Workflow Integration

Tasks implemented as TaskHandlers are invoked by an external system, the BPMN engine Operaton. In your BPMN model, you would define an "External Worker task". The "Job topic" you configure for this external task in the BPMN model must match one of the topic names defined in your `topics` configuration (e.g., `my_custom_task_topic`).

When the workflow reaches such an external task, the engine publishes a job to the topic specified in the BPMN model. The worker, listening on that topic, picks up the job and delegates it to the configured TaskHandler for execution.