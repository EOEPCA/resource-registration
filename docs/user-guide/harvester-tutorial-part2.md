# Harvester Developer Guide Part 2 - Worker implementation with Python

This chapter covers implementing new individual tasks for workflow orchestration and configuring the worker to manage their execution.

## Understanding the `TaskHandler`

The TaskHandler (located in `worker.common.task_handler.py`) is the base class for all custom task implementations. When creating a new task, you'll primarily focus on overriding its execute method.

### The `execute` Method

The `execute(self, job: ExternalJob, result: JobResultBuilder, config: dict) -> JobResult` method is where the actual work of your task is performed. This is the only method you typically need to override in your custom handler.

* Purpose: To receive job details, perform the task's business logic, and return a result indicating success or failure, along with any output variables.
* Parameters:
    * `job: ExternalJob`: An object providing access to the current job details. Key uses include:
        * `job.id`: The unique ID of the current job instance.
        * `job.element_name`: The name or ID of the task element from the BPMN workflow.
        * `job.get_variable("my_input_variable")`: To retrieve input variables passed from the workflow.
    * `result: JobResultBuilder`: An object used to construct the outcome of the task. You will use methods like:
        * `result.success()`: To indicate successful completion.
        * `result.failure()`: To indicate an error occurred.
        * `result.variable_json(name="output_variable_name", value=some_value)`: To set output variables (various types like variable_string, variable_int, variable_float, variable_boolean are available).
    * `config: dict`: A general configuration dictionary. While available, for handler-specific configurations, it is generally preferred to use the self.get_config() method (see below).
* Returns: A JobResult object, built using the result builder, which informs the workflow engine about the task's outcome (e.g., `result.success().variable_string(...)`).

### Supporting Features from the Base TaskHandler

The TaskHandler base class provides some helpful features:

* Configuration Handling (init and get_config):
    * The base TaskHandler's constructor (init) automatically loads configurations specific to your handler class from the main `config.yaml` file (under `worker.handlers.<YourHandlerClassName>`). It also handles subscription-related settings.
    * You can access these configurations within your execute method using `self.get_config(key: str, default=None)`. For example, `api_key = self.get_config("api_key")`.
* Standardized Error Reporting (task_failure):
    * The base class provides a helper method `task_failure(self, error, error_msg, result, retries=3, timeout="PT10M") -> JobResult`. You can use this in your execute method's except blocks to create a consistent failure JobResult.

So, when implementing a new task, your focus will be on the execute method, leveraging `job.get_variable()`, `self.get_config()`, and `result.success()`, `result.failure()`, or `self.task_failure()` for outputs.

## Implementing a New Task

Follow these steps to create and integrate a new task:

1. Create a Handler Class

    * Create a new Python file (e.g., `my_custom_tasks.py`) or add to an existing one within the `src/worker/` directory structure (e.g., `src/worker/custom/tasks.py`).
    * Define a new class that inherits from `worker.common.task_handler.TaskHandler`.

2. Implement the execute Method

```python
# src/worker/custom/tasks.py
from worker.common.task_handler import TaskHandler
from worker.common.utils.logging import log_with_context # For logging
from flowable.external_worker_client import ExternalJob, JobResultBuilder, JobResult


class MyCustomTaskHandler(TaskHandler):
    def execute(self, job: ExternalJob, result: JobResultBuilder, config: dict) -> JobResult:
        log_context = {"JOB": job.id, "BPMN_TASK": job.element_name}
        log_with_context("Starting My Custom Task...", log_context)

        try:
            # 1. Get input variables
            input_data = job.get_variable("my_input_data")
            api_url = self.get_config("service_url", "http://default.api.com")

            if not input_data:
                log_with_context("Missing 'my_input_data' variable.", log_context, "error")
                return result.failure().error_message("Input data is missing.")

            log_with_context(f"Processing data: {input_data} using API: {api_url}", log_context)

            # 2. Perform task logic
            processed_output = f"Processed: {input_data.upper()}"

            # 3. Return success with output variables
            log_with_context("Custom task completed successfully.", log_context)
            return result.success().variable_string(name="my_output_data", value=processed_output)

        except Exception as e:
            error_msg = f"Error in MyCustomTaskHandler: {str(e)}"
            log_with_context(error_msg, log_context, "error")
            # Use the task_failure helper for consistent error reporting
            return self.task_failure("CustomTaskExecutionError", error_msg, result)
```

* **Logging:** Use `log_with_context` for all logging. Include `job.id` and `job.element_name` in your `log_context` for better traceability.
* **Input Variables:** Retrieve any necessary input variables passed from the workflow using `job.get_variable("variable_name")`.
* **Configuration:** Access handler-specific configurations (defined in `config.yaml`) using `self.get_config("config_key", "default_value")`.
* **Business Logic:** Implement the core functionality of your task.
* **Error Handling:** Wrap your logic in a `try...except` block. If an error occurs, log it and return a failure result, preferably using `self.task_failure()`.

* **Return Result:**
    * On success: Use `result.success()` and chain `result.variable_json(name="var_name", value=var_value)` or `result.variable_string(...)` etc., to pass data back to the workflow.
    * On failure: Use `result.failure().error_message("Error Message").error_details("Detailed error info")` or `self.task_failure(...)`.

## Configuring the Worker

After implementing your TaskHandler, you need to configure the worker to use it. This is done in the main configuration file (typically `etc/config.yaml`, or the path specified by the `CONFIG_FILE_PATH` environment variable).
The `SubscriptionManager` component automatically discovers and subscribes your handlers to specific topics based on this configuration.

### Key Configuration Sections under `worker`

* `topics`: This section maps topic names (which your BPMN tasks will publish to) to your handler classes.
    * Each key is a topic name (e.g., `my_custom_task_topic`).
    * For each topic, you must specify:
        * `module`: The fully qualified Python module path to your handler class (e.g., `worker.custom.tasks`).
        * `handler`: The class name of your handler (e.g., `MyCustomTaskHandler`).
        * You can also override default subscription settings here, such as `lock_duration`, `number_of_retries`, etc. These settings will be merged with the `subscription_config` in your TaskHandler.
* `handlers`: This section provides specific configurations for individual TaskHandler implementations.
    * Each key is the class name of a handler (e.g., `MyCustomTaskHandler`).
    * Inside each handler's configuration, you can define key-value pairs. These values are accessible within that handler using `self.get_config("your_key")`.

### Example `config.yaml` Snippet

```yaml
worker:
  topics:
    # Topic for the custom task implemented above
    my_custom_task_topic:
      module: "worker.custom.tasks"  # Path to the .py file, dot-separated
      handler: "MyCustomTaskHandler"   # Class name
      lock_duration: "PT5M"          # Example: 5 minute lock duration for this task
      number_of_retries: 3

  handlers:
    # Configuration specific to MyCustomTaskHandler
    MyCustomTaskHandler:
      service_url: "https://my.api.service.com/v1/process"
      default_timeout_seconds: 60
```

### How it Works

1. The SubscriptionManager starts up.
2. It reads the `worker.topics` section from the `config.yaml`.
3. For each topic entry, it dynamically imports the specified module and retrieves the handler class.
4. It instantiates your handler class. The `worker.handlers` dictionary from the config is passed to the TaskHandler's constructor. The TaskHandler.__init__ method then filters out the configuration relevant to its specific class name.
5. The manager subscribes this handler instance to the specified topic, ready to process incoming jobs.

## Workflow Integration

Tasks implemented as TaskHandlers are invoked by an external system, the BPMN engine Flowable. In your BPMN model, you would define an "External Task". The "topic" you configure for this external task in the BPMN model must match one of the topic names defined in your `worker.topics` configuration (e.g., `my_custom_task_topic`).

When the workflow reaches such an external task, the engine publishes a job to the topic specified in the BPMN model. The worker, listening on that topic, picks up the job and delegates it to the configured TaskHandler for execution.