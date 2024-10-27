import requests
import re
import openai
from openai import OpenAI
import discord
import io
from discord.ext import commands
import asyncio
from concurrent.futures import ThreadPoolExecutor

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', description="Tale Weaver", intents=intents)

# Dnd Assistant
default_assistant = "ASSISTANT_ID"

DISCORD_API_KEY = "DISCORD-API KEY"
OPENAI_API_KEY = "OPENAI_KEY"

HELP_MESSAGE = """ I am the Plot Smith, a master weaver of tales. ✨ You may summon me to conjure captivating stories, crafting characters, plots, or themes from the very fabric of imagination. 🌌 Share your inspiration, and I shall sculpt a narrative of grandeur. 📖 If you desire any alterations to the unfolding saga, simply share your wishes, and I will reshape the tale to fulfill your vision. 🔮 

Once our story reaches its conclusion, you can ask me to `imagine` and generate an image of the realm we’ve created 🎨, or you may request me to `speak` the tale aloud, and I will narrate it to you myself. 🎤 Let us embark on this epic journey together! 🚀🔥
"""

#Last Message AI sent
last_message_AI = "Two Cats"
image_prompt = "Generate an image for "

user_threads = {}

#Debug when Ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print("Assistant bot is ready!")
    print('------')


client = OpenAI(
    api_key=OPENAI_API_KEY,
)

def manage_thread(user_id, clear=False):
    if clear or user_id not in user_threads:
        thread = client.beta.threads.create()
        user_threads[user_id] = thread.id
        return thread.id
    return user_threads[user_id]



        
@bot.event
async def on_message(message):
    # Bot ignores messages to itself or messages that mention everyone
    if message.author == bot.user or message.mention_everyone:
        return

    # Check if the message is not from a guild (DM)
    if message.guild is None:
        asyncio.create_task(process_message(message))

async def process_message(message):
    async with message.channel.typing():
        global last_message_AI
        message_str = message.content
        message_str = clean_discord_message(message_str)
        #Get help from last message
        if(message_str in ["help", "HELP","/help","Help"]):
            await message.add_reaction('ℹ️')
            await message.channel.send(HELP_MESSAGE)
            return
        #Generate Image from last Message
        if(message_str in ["create", "imagine","imagine","Create"]):
            await message.add_reaction('🎨')
            await asyncio.create_task(generate_image(image_prompt + last_message_AI,message))
            return
        #Convert last message to Audio
        if(message_str in ["speak", "talk"]):
            await message.add_reaction('🎶')
            await asyncio.create_task(generate_audio(last_message_AI,message))
            return
        #Clean Thread
        if(message_str in ["reload", "clear", "/clear" ,"reset","/reset","CLEAR","RESET"]):
            manage_thread(message.author.id,True)
            await message.channel.send("🧼 You now have a clean thread 🧼")
            return
        
        thread_id = manage_thread(message.author.id)
        print(thread_id)
        result = await get_gpt_assistant(message_str,thread_id)  # Async call maintained
        #Store Last message
        last_message_AI = result;
        await send_messages(message, split_string(result, 1700))


async def get_gpt_assistant(user_input,my_thread):
    output_easy = ""
    try:
        # Attempt to send the user message to the thread
        client.beta.threads.messages.create(
            thread_id=my_thread,
            role="user",
            content=user_input
        )
        # Start the assistant and stream the response
        with client.beta.threads.runs.stream(
            thread_id=my_thread,
            assistant_id=default_assistant,
            #instructions="Please address the user as Jane Doe. The user has a premium account." #Instructions should be in the Assistant
        ) as stream:
            for text in stream.text_deltas:
                output_easy += text

        return output_easy
    except Exception as e:
        # If an error occurs, return the error message
        return f"✖️ An error occurred: {str(e)}"
   
#Generate An image and attach to thread
async def generate_image(what_to_make,message):
    response = client.images.generate(
      model="dall-e-3",
      prompt = what_to_make,
      size="1024x1024",
      quality="standard",
      n=1,
    )
    image_url = response.data[0].url
    await message.channel.send(image_url)

async def generate_audio(what_to_make, message):
    # Generate the audio response
    response = client.audio.speech.create(
        model="tts-1",
        voice="echo",
        input=what_to_make
    )
    audio_data = io.BytesIO()
    for chunk in response.iter_bytes():
        audio_data.write(chunk)
    audio_data.seek(0)
    fileName = ' '.join(what_to_make.split()[:3]) + ".mp3"
    await message.channel.send(file=discord.File(fp=audio_data, filename=fileName))

    
def clean_discord_message(input_string):
    # Create a regular expression pattern to match text between < and >
    bracket_pattern = re.compile(r'<[^>]+>')

    # Replace text between brackets with an empty string
    cleaned_content = bracket_pattern.sub('', input_string)

    return cleaned_content  

def split_string(string, max_length = 1700):
    messages = []
    for i in range(0, len(string), max_length):
        sub_message = string[i:i+max_length]
        messages.append(sub_message)
    return messages

async def send_messages(messageSystem,output):
    for index, string in enumerate(output):
        await messageSystem.channel.send(string)


bot.run(DISCORD_API_KEY)