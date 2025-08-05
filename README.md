# 🧵 SteelThread: Agent Evaluation Framework

**SteelThread** is a flexible evaluation framework built around Portia, designed to support robust **evals** and **stream based** testing of agentic workflows. It enables configurable datasets, custom metric definitions, LLM-based judging, and stubbed tool behaviors for reproducible and interpretable scoring.

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

When running monitoring through **SteelThread** we offer two distinct types:

- **Evals** are static datasets designed to be run multiple times to allow you to analyze how changes to your agents affect performance.
- **Streams** are dynamic streams that automatically include your latest plans and plan runs, allowing you to measure performance in production.

Both types of monitoring can be configured via the [cloud dashboard.](https://app.portialabs.ai/dashboard/monitoring). Once you've created a dataset record the name of it.

---

### 3. **Basic Usage**

Run a full suite of evals and streams using the name of the dataset from step 2. This will use the built in set of evaluators to give you data out of the box.

```python
from portia import Config, LogLevel, Portia
from steelthread.steelthread import SteelThread, StreamConfig, EvalConfig

# Setup
config = Config.from_default(default_log_level=LogLevel.CRITICAL)
st = SteelThread()

# Process stream
st.process_stream(
    StreamConfig(stream_name="stream_v1", config=config, additional_tags={"feeling": "neutral"})
)

# Run evals
portia = Portia(config)
st.run_evals(
    portia,
    EvalConfig(
        eval_dataset_name="evals_v1",
        config=config,
        iterations=4,
    ),
)
```

---

## 🛠️ Features

### 🧪 Custom Metrics
Define your own evaluators by subclassing `Evaluator`:

```python
from steelthread.evals.evaluator import Evaluator
from steelthread.metrics.metric import Metric

class EmojiEvaluator(Evaluator):
    def eval_test_case(self,  
        test_case: EvalTestCase,
        final_plan: Plan,
        final_plan_run: PlanRun,
        additional_data: PlanRunMetadata, 
    ):
        output = final_plan_run.outputs.final_output.get_value() or ""
        count = output.count("😊")
        score = min(count / 2, 1.0)
        return Metric(score=score, name="emoji_score", description="Checks for emoji use")
```

---

### 🧩 Tool Stubbing

Stub tool responses deterministically for fast and reproducible testing:

```python
from steelthread.portia.tools import ToolStubRegistry, ToolStubContext

def weather_stub_response(
    ctx: ToolStubContext,
) -> str:
    """Stub for weather tool to return deterministic weather."""
    city = ctx.kwargs.get("city", "").lower()
    if city == "sydney":
        return "33.28"
    if city == "london":
        return "2.00"

    return f"Unknown city: {city}"


# Run evals with stubs + custom evaluators.
portia = Portia(
    config,
    tools=ToolStubRegistry(
        DefaultToolRegistry(config),
        stubs={
            "weather_tool": weather_stub_response,
        },
    ),
)
```

### 📊 `Metric Reporting`

**SteelThread** is designed around plugable metrics backends. By default metrics are logged and sent to Portia Cloud for visualization but you can add additional backends via the config options.


---

## 🧪 Example: End-to-End Test Script

See how everything fits together:

```python
from steelthread.steelthread import SteelThread, EvalConfig
from steelthread.portia.tools import ToolStubRegistry
from steelthread.metrics.metric import Metric
from steelthread.evals.evaluator import Evaluator
from portia import Config, Portia, DefaultToolRegistry, ToolRunContext

# Custom tool stub
def weather_stub_response(
    ctx: ToolStubContext,
) -> str:
    """Stub for weather tool to return deterministic weather."""
    city = ctx.kwargs.get("city", "").lower()
    if city == "sydney":
        return "33.28"
    if city == "london":
        return "2.00"

    return f"Unknown city: {city}"


# Custom evaluator
class EmojiEvaluator(Evaluator):
    def eval_test_case(self, test_case,plan, plan_run, metadata):
        out = plan_run.outputs.final_output.get_value() or ""
        count = out.count("🌞")
        return Metric(score=min(count / 2, 1.0), name="emoji_score", description="Emoji usage")

# Setup
config = Config.from_default()
st = SteelThread()
portia = Portia(
    config,
    tools=ToolStubRegistry(DefaultToolRegistry(config), {"weather_tool": weather_stub_response})
)

st.run_evals(
    portia,
    EvalConfig(
        eval_dataset_name="evals_v1",
        config=config,
        iterations=4,
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
