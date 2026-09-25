import streamlit as st
from openai import OpenAI
import requests
import json

st.title("What to Wear Bot")

if 'openai_client' not in st.session_state:
    st.session_state.openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


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


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get the current weather and today's forecast for a location, to give clothing and activity advice.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name, zip code, airport code, or landmark. Defaults to Syracuse, NY if not specified."
                    }
                },
                "required": ["location"]
            }
        }
    }
]

city_input = st.text_input("Enter a city (or leave blank for Syracuse, NY):")

get_advice = st.button("Get Advice")

if get_advice:

    client = st.session_state.openai_client

    location_text = city_input if city_input else "Syracuse, NY"

    user_message = f"What should I wear today in {location_text}, and what outdoor activities would be good given the weather?"

    messages = [
        {"role": "user", "content": user_message}
    ]

    first_response = client.chat.completions.create(
        model="gpt-4.1",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    response_message = first_response.choices[0].message
    tool_calls = response_message.tool_calls

    if tool_calls:
        messages.append(response_message)

        for tool_call in tool_calls:
            function_args = json.loads(tool_call.function.arguments)
            location = function_args.get("location", "Syracuse, NY")

            weather_data = get_current_weather(location)

            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": "get_current_weather",
                "content": json.dumps(weather_data)
            })

        second_response = client.chat.completions.create(
            model="gpt-4.1",
            messages=messages
        )

        final_answer = second_response.choices[0].message.content
        st.write(final_answer)
    else:
        st.write(response_message.content)