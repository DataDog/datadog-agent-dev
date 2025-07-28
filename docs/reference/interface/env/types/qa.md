# QA environment interface

-----

Environment types implementing the [`QAEnvironmentInterface`][dda.env.qa.interface.QAEnvironmentInterface] interface may be managed by the [`env qa`](../../../cli/commands.md#dda-env-qa) command group.

::: dda.env.qa.interface.QAEnvironmentConfig
    options:
      show_labels: true
      unwrap_annotated: true

::: dda.env.qa.interface.QAEnvironmentInterface
    options:
      show_labels: true
      show_if_no_docstring: false
