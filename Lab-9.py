import asyncio
import os
import time

import requests
import streamlit as st
from agents import Agent, ModelSettings, Runner, function_tool
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions

os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]
MODEL = "gpt-5-mini"


def get_current_weather(location):
    url = f'https://wttr.in/{location}?format=j1'
    response = requests.get(url, timeout=10)
    if response.status_code != 200:
        raise Exception(f'wttr.in error: status {response.status_code}')
    try:
        data = response.json()
    except ValueError:
        raise Exception(f'Could not find a location named {location}')

    current = data['current_condition'][0]
    today = data['weather'][0]

    return {
        'location': location,
        'temperature_F': float(current['temp_F']),
        'feels_like_F': float(current['FeelsLikeF']),
        'description': current['weatherDesc'][0]['value'],
        'humidity_percent': int(current['humidity']),
        'wind_speed_mph': float(current['windspeedMiles']),
        'chance_of_rain_percent': int(today['hourly'][4]['chanceofrain']),
        'max_temp_F': float(today['maxtempF']),
        'min_temp_F': float(today['mintempF'])
    }


@function_tool
def get_weather(location: str = "Syracuse, NY") -> dict:
    """Get the current weather and today's forecast for a place: temperature
    and feels-like in Fahrenheit, conditions, humidity, wind speed in mph,
    chance of rain, and today's high and low. Accepts a city name such as
    'Syracuse, NY' or 'Lima, Peru', a zip code, an airport code or a
    landmark. If the place can't be found, it returns an error."""
    return get_current_weather(location)


weather_agent = Agent(
    name="Weather agent",
    instructions=(
        "You report the weather. Always call get_weather for the place the "
        "user names, then summarize the facts in a few plain sentences: "
        "temperature, how it feels, wind, chance of rain, and the day's high "
        "and low. Do not give advice about clothes or activities; other "
        "teammates do that. If the place can't be found, say so gently and "
        "say what you'd need instead."
    ),
    tools=[get_weather],
    model=MODEL,
)

stylist_agent = Agent(
    name="Stylist agent",
    instructions=(
        "You suggest what to wear based on the weather summary you are given. "
        "Be practical and warm, like a friend who happens to have good taste. "
        "Give a short outfit (top, bottom, shoes, one extra layer if needed) "
        "and a one-line reason. Never invent weather facts you were not given."
    ),
    model=MODEL,
)

activity_agent = Agent(
    name="Activity agent",
    instructions=(
        "You suggest two or three things to do today based on the weather "
        "summary you are given. Mix one outdoor idea and one indoor backup. "
        "Keep it friendly and realistic, and never invent weather facts."
    ),
    model=MODEL,
)

manager_agent = Agent(
    name="Manager",
    instructions=(
        "You coordinate a small team to help someone plan their day. First "
        "call weather_report for the place. Then pass the weather summary "
        "(in your own words) to outfit_advice and activity_ideas. Combine "
        "everything into one short, kind, easy-to-read answer: a line on the "
        "weather, what to wear, what to do. If the place isn't real or the "
        "weather could not be found, don't guess: say so gently and invite "
        "the person to try another city. Speak to the person like a "
        "thoughtful friend, not a report."
    ),
    tools=[
        weather_agent.as_tool(
            tool_name="weather_report",
            tool_description="Looks up the current weather for a place and "
                             "returns a short factual summary. No advice.",
        ),
        stylist_agent.as_tool(
            tool_name="outfit_advice",
            tool_description="Given a weather summary, suggests what to wear.",
        ),
        activity_agent.as_tool(
            tool_name="activity_ideas",
            tool_description="Given a weather summary, suggests things to do "
                             "today, with an indoor backup.",
        ),
    ],
    model=MODEL,
)

single_agent = Agent(
    name="Single agent",
    instructions=(
        "You help people plan their day. Always call get_weather for the "
        "place the user names, then give a short, warm answer: the weather "
        "in a sentence, what to wear, and two or three things to do (include "
        "an indoor backup). If the place can't be found, say so gently and "
        "ask for another city. Don't invent weather facts."
    ),
    tools=[get_weather],
    model=MODEL,
)

packing_agent = Agent(
    name="Packing agent",
    handoff_description="Builds a packing list for a trip to another city.",
    instructions=prompt_with_handoff_instructions(
        "You have taken over from the triage agent and answer the user "
        "yourself. Always call get_weather for the destination first, then "
        "write a friendly packing list."
    ),
    tools=[get_weather],
    model_settings=ModelSettings(tool_choice="required"),
    model=MODEL,
)

outfit_team = manager_agent.clone(
    name="Outfit team", handoff_description="What to wear and do today."
)

triage_agent = Agent(
    name="Triage agent",
    instructions="Hand off trips to the Packing agent and "
                 "today's outfits to the Outfit team.",
    handoffs=[packing_agent, outfit_team],
    model=MODEL,
)


@st.cache_resource
def get_event_loop():
    return asyncio.new_event_loop()


def run(agent, prompt):
    start = time.perf_counter()
    result = get_event_loop().run_until_complete(Runner.run(agent, prompt))
    return result, time.perf_counter() - start


st.title("What to Wear: the crew")

mode = st.radio(
    "Who should answer?",
    ["Team (manager + specialists)", "Single agent", "Triage (bonus)"],
    horizontal=True,
)
location = st.text_input("Enter a city (or leave blank for Syracuse, NY):")

if st.button("Get advice"):
    place = location if location else "Syracuse, NY"
    if mode.startswith("Team"):
        agent, prompt = manager_agent, f"What should I wear and do today in {place}?"
    elif mode.startswith("Single"):
        agent, prompt = single_agent, f"What should I wear and do today in {place}?"
    else:
        agent, prompt = triage_agent, place

    with st.spinner("Checking in with the crew... this can take 20 to 40 seconds."):
        result, seconds = run(agent, prompt)

    with st.chat_message("assistant"):
        st.write(result.final_output)

    usage = result.context_wrapper.usage
    with st.expander("Behind the scenes"):
        st.write(
            f"Model requests: {usage.requests} · Tokens: {usage.total_tokens:,} · "
            f"Time: {seconds:.1f}s · Answered by: {result.last_agent.name}"
        )
        for item in result.new_items:
            if item.type == "tool_call_item":
                st.write(f"{item.agent.name} called {item.raw_item.name}: "
                         f"{item.raw_item.arguments}")
            elif item.type == "tool_call_output_item":
                st.write(f"result: {str(item.output)[:300]}")
            elif item.type == "handoff_output_item":
                st.write(f"handoff: {item.source_agent.name} -> {item.target_agent.name}")
