# 🧵 SteelThread: Agent Evaluation Framework

**SteelThread** is a flexible evaluation framework built around Portia, designed to support robust **online** and **offline** testing of agentic workflows. It enables configurable datasets, custom metric definitions, LLM-based judging, and stubbed tool behaviors for reproducible and interpretable scoring.

---

## 🚀 Getting Started

### 1. **Install using your framework of choice**

#### `pip`
```bash
pip install steel-thread
```
#### `poetry`
```bash
poetry add steel-thread
```
#### `uv`
```bash
uv add steel-thread
```

---

### 2. **Create your datasets**

**SteelThread** is designed around deep integration with Portia. It uses data from Portia Cloud to generate test cases and evals. 

When running evals through **SteelThread** we offer two distinct types:

- **Offline evals** are static datasets designed to be run multiple times to allow you to analyze how changes to your agents affect performance.
- **Online evals** are dynamic datasets that automatically include your latest plans and plan runs, allowing you to measure performance in production.

Both types of evals can be configured via the [cloud dashboard.](https://app.portialabs.ai/dashboard/evals). Once you've created a dataset record the name of it.

---

### 3. **Basic Usage**

Run a full suite of online and offline evaluations using the name of the dataset from step 2. This will use the built in set of evaluators to give you data out of the box.

```python
from portia import Config, LogLevel, Portia
from steelthread.steelthread import SteelThread, OnlineEvalConfig, OfflineEvalConfig

# Setup
config = Config.from_default(default_log_level=LogLevel.CRITICAL)
runner = SteelThread()

# Online evals
runner.run_online(
    OnlineEvalConfig(data_set_name="online_evals", config=config)
)

# Offline evals
portia = Portia(config)
runner.run_offline(
    portia,
    OfflineEvalConfig(data_set_name="offline_evals_v1", config=config, iterations=4)
)
```

---

## 🛠️ Features

### 🧪 Custom Metrics
Define your own evaluators by subclassing `OfflineEvaluator`:

```python
from steelthread.offline_evaluators.evaluator import OfflineEvaluator
from steelthread.metrics.metric import Metric

class EmojiEvaluator(OfflineEvaluator):
    def eval_test_case(self, test_case, final_plan_run, additional_data):
        output = final_plan_run.outputs.final_output.get_value() or ""
        count = output.count("😊")
        score = min(count / 2, 1.0)
        return Metric(score=score, name="emoji_score", description="Checks for emoji use")
```

---

### 🧩 Tool Stubbing

Stub tool responses deterministically for fast and reproducible testing:

```python
from steelthread.portia.tools import ToolStubRegistry

portia = Portia(
    config,
    tools=ToolStubRegistry(
        DefaultToolRegistry(config),
        stubs={
            "weather_tool": lambda i, ctx, args, kwargs: "20.0"  # Always returns 20.0
        }
    )
)
```

### 📊 `Metric Reporting`

**SteelThread** is designed around plugable metrics backends. By default metrics are logged and sent to Portia Cloud for visualization but you can add additional backends via the config options.

---

## 📁 Project Structure

```
steelthread/
├── metrics/                 # Metric schema & backend logging
│   └── metric.py
├── offline_evaluators/     # Offline test runners and evaluators
│   ├── eval_runner.py
│   ├── evaluator.py
│   └── test_case.py
├── online_evaluators/      # Online test runners
│   └── eval_runner.py
├── portia/                 # Tool stubbing and integration with Portia
│   └── tools.py
├── shared/                 # Shared storage and model definitions
│   └── readonly_storage.py
└── steelthread.py          # Main runner entry point
```

---

## 🧪 Example: End-to-End Test Script

See how everything fits together:

```python
from steelthread.steelthread import SteelThread, OfflineEvalConfig
from steelthread.portia.tools import ToolStubRegistry
from steelthread.metrics.metric import Metric
from steelthread.offline_evaluators.default_evaluator import DefaultOfflineEvaluator
from steelthread.offline_evaluators.evaluator import OfflineEvaluator
from portia import Config, Portia, DefaultToolRegistry, ToolRunContext

# Custom tool stub
def weather_stub_response(i, ctx, args, kwargs):
    return "33.28" if kwargs.get("city") == "sydney" else "2.00"

# Custom evaluator
class EmojiEvaluator(OfflineEvaluator):
    def eval_test_case(self, test_case, plan_run, metadata):
        out = plan_run.outputs.final_output.get_value() or ""
        count = out.count("🌞")
        return Metric(score=min(count / 2, 1.0), name="emoji_score", description="Emoji usage")

# Setup
config = Config.from_default()
runner = SteelThread()
portia = Portia(
    config,
    tools=ToolStubRegistry(DefaultToolRegistry(config), {"weather_tool": weather_stub_response})
)

runner.run_offline(
    portia,
    OfflineEvalConfig(
        data_set_name="offline_evals_v1",
        config=config,
        iterations=1,
        evaluators=[DefaultOfflineEvaluator(config), EmojiEvaluator(config)],
    ),
)
```

---

## 🧪 Testing

Write tests for your metrics, plans, or evaluator logic using `pytest`:

```bash
uv run pytest tests/
```

---
