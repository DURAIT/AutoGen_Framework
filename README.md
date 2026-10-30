# 🌦️ Weather News Agent

A single-file Streamlit dashboard powered by an [AutoGen](https://microsoft.github.io/autogen/) agent. Enter a city and the agent searches the web with the free, keyless [DuckDuckGo](https://pypi.org/project/ddgs/) search package, then replies with the weather in **exactly 3 short lines**.

---

## ✨ Features

- **AutoGen agent** that decides when to call a search tool on its own
- **Keyless web search** via `ddgs` (DuckDuckGo), with no search API key needed
- **Natural-language answers**: `reflect_on_tool_use=True` makes the agent write a reply from the search results instead of returning raw output
- **Exactly 3 short lines** per city: current conditions, today's outlook, and news or alerts
- **Streamlit dashboard** with a dark glass UI, a search bar, quick-pick city buttons, a hero temperature card and colour-coded alerts
- **Clean shutdown**: the model client is closed after every request

---

## 🧰 Tech Stack

| Component | Purpose |
|-----------|---------|
| `autogen-agentchat` | Agent framework (`AssistantAgent`) |
| `autogen-ext[openai]` | OpenAI model client for AutoGen |
| `ddgs` | Free DuckDuckGo search, no API key |
| `streamlit` | Web frontend |
| `python-dotenv` | Loads the API key from a `.env` file |

---

## 📋 Prerequisites

- **Python 3.10 or newer**
- **pip** (comes with Python)
- An **OpenAI API key** (https://platform.openai.com/api-keys)
- An internet connection

Check your Python version:

```bash
python --version
```

---

## 📁 Project Structure

```
weather-news/
├── weather_news.py   # the entire app (agent + tool + Streamlit UI)
├── .env              # your API key (you create this)
└── README.md
```

---

## 🚀 Setup

### 1. Create a project folder

```bash
mkdir weather-news
cd weather-news
```

Place `weather_news.py` and this `README.md` inside the folder.

### 2. Create and activate a virtual environment

**Windows (PowerShell):**

```powershell
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

Your terminal prompt should now start with `(venv)`.

### 3. Install the dependencies

```bash
pip install -U autogen-agentchat "autogen-ext[openai]" ddgs python-dotenv streamlit
```

### 4. Add your API key

Create a file named `.env` in the same folder as `weather_news.py`:

```env
OPENAI_API_KEY=your-openai-api-key-here
```

> 🔒 Never commit `.env` to Git. If you use version control, add `.env` to your `.gitignore`.

### 5. Run the app

```bash
streamlit run weather_news.py
```

Streamlit starts a local server and opens the dashboard in your browser, usually at **http://localhost:8501**.

---

## 🖥️ Using the Dashboard

1. Type a city in the search bar, for example `Chennai, Tamil Nadu, India`.
2. Press **Enter** or click **Search**. You can also click one of the quick-pick city buttons.
3. Wait a few seconds while the agent searches the web and writes the answer.
4. Read the result in three cards:

| Line | Card | Content |
|------|------|---------|
| 1 | **Current Overview** | Current conditions and temperature |
| 2 | **Today's Outlook** | Today's forecast |
| 3 | **News & Alerts** | Notable weather news or alerts (green if none, red if there is an alert) |

An **AI Weather Summary** card at the bottom repeats the same 3 lines together.

To stop the app, press `Ctrl + C` in the terminal.

---

## ⚙️ How It Works

```
User enters city
      │
      ▼
Streamlit  ──►  AutoGen AssistantAgent  ──►  search_weather_news()  ──►  DuckDuckGo
                       │                                                     │
                       │◄──────────────── search results ◄───────────────────┘
                       ▼
        reflect_on_tool_use=True → model writes a 3-line answer
                       │
                       ▼
        to_three_lines() guarantees exactly 3 lines  ──►  dashboard cards
                       │
                       ▼
              model_client.close()
```

### The search tool

In AutoGen, a tool is a plain Python function. The agent reads the function's **name, type hints and docstring** to decide when to call it:

```python
def search_weather_news(query: str) -> str:
    """Search the web with DuckDuckGo for current weather conditions and weather news.
    ...
    """
```

It is registered on the agent with:

```python
AssistantAgent(
    name="weather_news_agent",
    model_client=model_client,
    tools=[search_weather_news],
    reflect_on_tool_use=True,
    system_message=SYSTEM_MESSAGE,
)
```

### Key design points

- **`reflect_on_tool_use=True`** makes the agent turn search results into a readable answer instead of dumping raw output.
- **The system message** asks for exactly 3 short lines.
- **`to_three_lines()`** trims, splits or pads the reply, so the UI always shows exactly 3 lines.
- **`finally: await model_client.close()`** always releases the HTTP client, even if a request fails.
- **`load_dotenv()`** reads `OPENAI_API_KEY` from `.env` at startup.

---

## 🔧 Customisation

**Change the model** in `get_weather_news()`:

```python
model_client = OpenAIChatCompletionClient(model="gpt-4o-mini", api_key=api_key)
```

**Change the quick-pick cities** near the bottom of the file:

```python
QUICK_CITIES = ["Chennai", "Mumbai", "Delhi", "Bengaluru", "London", "New York"]
```

**Change the answer format** by editing `SYSTEM_MESSAGE`, for example to ask for a different focus on each line.

**Change the search depth** by editing `max_results` in `search_weather_news()`:

```python
results = DDGS().text(query, max_results=5)
```

**Restyle the dashboard** by editing the CSS block inside the `st.markdown("""<style>...</style>""")` call.

---

## 📌 Notes

- Weather details come from web search snippets summarised by the model, so treat them as a quick snapshot and not an official forecast.
- Each search makes one or more OpenAI API calls, which may incur small usage costs on your OpenAI account.

---

## 📄 License

Use and modify freely for learning and personal projects.
