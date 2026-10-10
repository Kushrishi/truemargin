# Contributing

Use Python 3.12 and the [development setup](docs/reproduction.md). Run Ruff,
Black, Mypy and pytest before submitting a code change. Tests use synthetic
fixtures and retained public outputs; they do not require clinical images.

Describe the problem, affected behavior and validation in the pull request.
For numerical changes, identify coordinate order, units, precision and any
changed assumptions. Compare with an independent reference where practical.

Completed studies pin source, inputs and protocol bytes. Keep those records
unchanged; a new estimator or study design needs its own prospective definition.
Do not update expected scientific results merely to make a test pass. Store
large images, registration fields and temporary outputs outside Git.

Use the [research guide](research/README.md) to distinguish current guidance from
historical records. Public explanations should define study identifiers and
separate measured results from proposed capabilities. The current repository
license metadata is research-restricted; this guide does not grant additional
reuse rights.
