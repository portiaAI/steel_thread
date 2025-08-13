# SteelThread: Agent Evaluation Framework

**SteelThread** is a flexible evaluation framework built around Portia, designed to support robust **evals** and **stream based** testing of agentic workflows. It enables configurable datasets, custom metric definitions including both deterministic and LLM-based judging, and stubbed tool behaviors for reproducible and interpretable scoring. But its strongest suite is that **you can add successful agent runs from the dashboard directly into your datasets rather than have to build those ground truth from scratch**. This means Eval sets that are up to date and easy to maintain at all times.

We offer two distinct types of monitoring through **SteelThread**:
- **Streams** are dynamic datasets sampled automatically from your latest plans and plan runs, allowing you to measure performance in production.
- **Evals** are static datasets designed to be run multiple times to allow you to analyze how changes to your agents affect performance.

For access to the full documentation please visit [our docs](https://docs.portialabs.ai/evals-steel-thread).
SteelThread relies on access to agent activity in Portia cloud (queries, plans, plan runs). You will need a `PORTIA_API_KEY` to get started. Get one for free from your Portia dashboard's "Manage API keys" tab.

---

## **Install using your framework of choice**

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

## **Create a dataset**
If you're new to Portia you may not have agent runs in the cloud just yet. so let's start by creating those. Run the query "Read the user feedback notes in local file {path}, and call out recurring themes in their feedback. Use lots of ⚠️ emojis when highlighting areas of concern." where `path` is a local file you can put a couple of lines of fictitious user feedback in. Here's the script to save you same time:

```python
from portia import Portia

path = "./uxr/calorify.txt" # TODO: change to your desired path
query =f"Read the user feedback notes in local file {path}, \
            and call out recurring themes in their feedback. \
                Use lots of ⚠️ emojis when highlighting areas of concern."

Portia().run(query=query)
```
---

## **Basic Usage with Streams**

Below is example code to process a stream. Before running it make sure you set up your stream from the Portia dashboard's Observability tab so you can then pass it to the `process_stream` method below. This method will use the built-in set of Stream evaluators to give you data out of the box.

```python
from portia import Config
from steelthread.steelthread import SteelThread, StreamConfig
from dotenv import load_dotenv


load_dotenv(override=True)

config = Config.from_default()

# Setup SteelThread instance and process stream
st = SteelThread()
st.process_stream(
    StreamConfig(
        # The stream name is the name of the stream we created in the dashboard.
        stream_name="your-stream-name-here",
        config=config,
    )
)
```

---

## Features

### Custom Metrics
Define your own evaluators by subclassing `Evaluator`:

```python
from steelthread.evals import Evaluator, EvalMetric

class EmojiEvaluator(Evaluator):
    def eval_test_case(self, test_case,plan, plan_run, metadata):
        out = plan_run.outputs.final_output.get_value() or ""
        count = out.count("🌞")
        return EvalMetric.from_test_case(
            test_case=test_case,
            name="emoji_score",
            score=min(count / 2, 1.0),
            description="Emoji usage"
        )
```

### Tool Stubbing

Stub tool responses deterministically for fast and reproducible testing:

```python
from portia import Portia, Config, DefaultToolRegistry
from steelthread.portia.tools import ToolStubRegistry, ToolStubContext


config = Config.from_default()

# Define stub behavior
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

# Run evals with stubs 
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

### `Metric Reporting`

**SteelThread** is designed around plugable metrics backends. By default metrics are logged and sent to Portia Cloud for visualization but you can add additional backends via the config options.

---

## 🧪 End-to-end example with Evals

Let's see how everything fits together. Create an Eval dataset in the dashboard from the plan run we made in the **Create a dataset** section. Navigate to the "Evaluations" tab of the dashboard, create a new eval set from existing data and select the relevant plan run. Record the name you bestowed upon your Eval dataset as you will to pass it to the evaluators in the code below, which you are now ready to run. This code:
* Uses a custom evaluator to count ⚠️ emojis in the output.
* Stubs the `file_reader_tool` with static text.
* Run the evals for the dataset you create to compute the emoji count metric over it.

Feel to mess around with the output from the tool stub and re-run these Evals a few times to see the progression in scoring.

```python
from portia import Portia, Config, DefaultToolRegistry
from steelthread.steelthread import SteelThread, EvalConfig
from steelthread.evals import Evaluator, EvalMetric
from steelthread.portia.tools import ToolStubRegistry, ToolStubContext


# Custom evaluator
class EmojiEvaluator(Evaluator):
    def eval_test_case(self, test_case,plan, plan_run, metadata):
        out = plan_run.outputs.final_output.get_value() or ""
        count = out.count("⚠️")
        return EvalMetric.from_test_case(
            test_case=test_case,
            name="emoji_score",
            score=min(count / 2, 1.0),
            description="Emoji usage",
            explanation=f"Found {count} ⚠️ emojis in the output.",
            actual_value=str(count),
            expectation="2"
        )

# Define stub behavior
def file_reader_stub_response(
    ctx: ToolStubContext,
) -> str:
    """Stub response for file reader tool to return static file content."""
    filename = ctx.kwargs.get("filename", "").lower()

    return f"Feedback from file: {filename} suggests \
        ⚠️ 'One does not simply Calorify' \
        and ⚠️ 'Calorify is not a diet' \
        and ⚠️ 'Calorify is not a weight loss program' \
        and ⚠️ 'Calorify is not a fitness program' \
        and ⚠️ 'Calorify is not a health program' \
        and ⚠️ 'Calorify is not a nutrition program' \
        and ⚠️ 'Calorify is not a meal delivery service' \
        and ⚠️ 'Calorify is not a meal kit service' "


config = Config.from_default()

# Run evals with stubs 
portia = Portia(
    config,
    tools=ToolStubRegistry(
        DefaultToolRegistry(config),
        stubs={
            "file_reader_tool": file_reader_stub_response,
        },
    ),
)

SteelThread().run_evals(
    portia,
    EvalConfig(
        eval_dataset_name="your-dataset-name-here", #TODO: replace with your dataset name
        config=config,
        iterations=5,
        evaluators=[EmojiEvaluator(config)]
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
