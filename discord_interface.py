import os
import datetime
import discord
from discord.ext import commands
from dotenv import load_dotenv
import whisper
import wave
import io
import time
import sys
import requests
from utils import (
    summarize_message, 
    get_related_topics, 
    fact_check_claim, 
    get_definition, 
    extract_atomic_ideas,
    check_api_health
)

load_dotenv()
discord_bot_token = os.getenv('DISCORD_BOT_TOKEN')
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

# Check API health before starting
print("Checking API health...")
max_retries = 5
retry_count = 0
api_ready = False

while retry_count < max_retries and not api_ready:
    if check_api_health():
        api_ready = True
        print("API is healthy and ready!")
    else:
        retry_count += 1
        print(f"API not ready, retrying in 5 seconds... (Attempt {retry_count}/{max_retries})")
        time.sleep(5)

if not api_ready:
    print("ERROR: API is not available. Please make sure the API is running.")
    print("You can start the API with: python -m api_module.run")
    sys.exit(1)

# Set up intents we actually need
intents = discord.Intents.default()

model = whisper.load_model("small")
client = commands.Bot(command_prefix='!', intents=intents)
connections = {}  # Cache for voice connections

class VoiceControlView(discord.ui.View):
    def __init__(self, ctx, vc):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.vc = vc
        
    @discord.ui.button(label="Start", style=discord.ButtonStyle.primary, emoji="🔴")
    async def start(self, button, interaction):
        await interaction.response.edit_message(content="Recording...")   
        self.vc.start_recording(
            discord.sinks.WaveSink(),
            once_done,
            self.ctx.channel
        )

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.primary, emoji="⬜")
    async def stop(self, button, interaction):
        if self.ctx.guild.id in connections:
            self.vc = connections[self.ctx.guild.id]
            self.vc.stop_recording()
            await interaction.response.edit_message(content="You can start recording!", view=VoiceControlView(self.ctx, self.vc))
        else:
            await self.ctx.respond("I am currently not recording here.")

async def once_done(sink: discord.sinks, channel: discord.TextChannel):
    msg = await channel.send("Processing audio...")
    
    # Filter out bots
    for user_id in list(sink.audio_data.keys()):
        user = await client.fetch_user(user_id)
        if user.bot:
            del sink.audio_data[user_id]

    recorded_users = [
        f"<@{user_id}>"
        for user_id, _ in sink.audio_data.items()
    ]

    if not recorded_users:
        await msg.edit(content="No valid audio recorded.")
        return

    # Process each user's audio
    for user_id, audio in sink.audio_data.items():
        filename = f"audio_{user_id}.wav"
        with open(filename, "wb") as f:
            f.write(audio.file.getvalue())
        
        # Transcribe with whisper
        text = model.transcribe(filename)["text"]
        os.remove(filename)
        
        await channel.send(f"<@{user_id}> said: {text}")
    
    await msg.edit(content=f"Finished processing audio for: {', '.join(recorded_users)}")

async def reply_to_user(ctx, reply):
    await ctx.send(reply)

#say hello
@client.slash_command(description="Join")
async def join(ctx: discord.context):
    """Command join that lets the bot join the voice channel

    Args:
        ctx (discord.context): Discord Context
    """
    # If the user calling the bot is not in voice channel
    if not ctx.author.voice:
        await ctx.respond("You aren't in a voice channel!")
        
    vc = await ctx.author.voice.channel.connect()  # Connect to the voice channel the author is in.
    connections.update({ctx.guild.id: vc})  # Updating the cache with the guild and channel.
    # Send recording view
    await ctx.respond("You Can Start recording!", view = VoiceControlView(ctx, vc))

@client.slash_command(description="Leave")
async def leave(ctx: discord.context):
    """Command leave that lets the bot leave the voice channel

    Args:
        ctx (discord.context): Discord context
    """
    if ctx.guild.id in connections:  # Check if the guild is in the cache.
        vc = connections[ctx.guild.id]
        await vc.disconnect()  # Disconnect from the voice channel.
        del connections[ctx.guild.id]  # Remove the guild from the cache.
        await ctx.delete()  # And delete.
    else:
        await ctx.respond("I am currently not Connected")  # Respond with this if we aren't recording.

#login event
@client.event
async def on_ready():
    """Prints message to console once we successfully load the bot
    """
    print('We have logged in as {0.user}'.format(client) + ' ' + datetime.datetime.utcnow().strftime("%m/%d/%Y %H:%M:%S UTC"))

@client.event
async def on_reaction_add(reaction, user):
    print(reaction.emoji)
    ctx = await client.get_context(reaction.message)
    async with ctx.typing():
        if reaction.emoji == "🔍":
            message = reaction.message
            await message.reply("Generating related topics to think about. Please wait...")
            response = await get_related_topics(message.content)
            lst_str = response.split('\n')
            lst = [s.strip() for s in lst_str if s.strip()][:10]
            
            tags = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
            formatted_lst = [f"{tags[i]} {s}" for i, s in enumerate(lst) if i < len(tags)]
            formatted_str = '\n'.join(formatted_lst)
            print(formatted_str)
            reply = await message.reply('\n' + formatted_str)
            for i in range(len(formatted_lst)):
                await reply.add_reaction(tags[i])
        elif reaction.emoji == "✅":
            message = reaction.message
            await message.reply("Searching fact checking websites to assess the claim. Please wait...")
            response = await fact_check_claim(message.content)
            reply = await message.reply(response)
        elif reaction.emoji == "🤖":
            message = reaction.message
            await reply_to_user(ctx, "I am summarizing the conversation in this channel. This may take some time, please be patient.")
            
            # Get channel history
            messages = []
            async for msg in message.channel.history(limit=100):
                messages.append(msg.content)
            messages_text = '\n'.join(messages[::-1])
            
            # Use the summarization service via API
            result = summarize_message(messages_text)
            response = f"**{result['title']}**\n\n{result['summary']}"
            reply = await message.reply(response)

@client.slash_command(description="summarize-channel")
async def summarize(ctx):
    await reply_to_user(ctx, "I am summarizing the conversation in this channel. This may take some time, please be patient.")
    
    try:
        n = int(ctx.message.content.replace('!summarize', '').strip())
    except ValueError:
        n = 10  # Default to 10 messages if no number specified
    
    messages = []
    async for msg in ctx.channel.history(limit=n):
        messages.append(msg.content)
    messages_text = '\n'.join(messages[::-1])
    
    # Use the summarization service via API
    result = summarize_message(messages_text)
    response = f"**{result['title']}**\n\n{result['summary']}"
    await reply_to_user(ctx, response)

@client.slash_command(description="related-channel")
async def related(ctx):
    await reply_to_user(ctx, "Generating related topics to think about. Please wait...")
    try:
        n = int(ctx.message.content.replace('!related', '').strip())
    except ValueError:
        n = 100  # Default to 100 messages if no number specified
    
    messages = []
    async for msg in ctx.channel.history(limit=n):
        messages.append(msg.content)
    message_str = '\n'.join(messages[::-1])
    response = await get_related_topics(message_str)
    await reply_to_user(ctx, response)

@client.slash_command(description="define")
async def define(ctx):
    await ctx.respond("Searching for definition. Please wait...")
    
    # Check if the command has context from a reply
    if ctx.message and ctx.message.reference and ctx.message.reference.resolved:
        parent_message = ctx.message.reference.resolved
        term = ctx.message.content.replace('!define', '').strip()
        
        await ctx.send(f"Defining term {term}, in context: {parent_message.content}")
        response = await get_definition(term, parent_message.content)
        await reply_to_user(ctx, response)
    else:
        # Direct command without reply context
        term = ctx.message.content.replace('!define', '').strip() if ctx.message else ""
        if not term:
            # Try to get from interaction options if available
            try:
                term = ctx.options.term
            except:
                term = ""
        
        if term:
            response = await get_definition(term)
            await reply_to_user(ctx, response)
        else:
            await ctx.respond("Please provide a term to define. You can also reply to a message for context.")

@client.slash_command(description="extract")
async def extract(ctx):
    """Extract key ideas from a message
    
    Can be used directly or as a reply to another message
    """
    await ctx.respond("Extracting key ideas. Please wait...")
    
    # Check if used as a reply
    if ctx.message and ctx.message.reference and ctx.message.reference.resolved:
        # Message to extract from
        source_message = ctx.message.reference.resolved.content
    else:
        # Take content from the command itself
        source_message = ctx.message.content.replace('!extract', '').strip() if ctx.message else ""
        if not source_message:
            # Try to get from interaction options
            try:
                source_message = ctx.options.text
            except:
                source_message = ""
    
    if not source_message:
        await ctx.respond("Please provide text to extract ideas from, or use this command as a reply to a message.")
        return
    
    # Call the extraction API
    ideas = await extract_atomic_ideas(source_message)
    
    if not ideas:
        await ctx.respond("No key ideas were extracted. Try with a longer or more detailed text.")
        return
    
    # Format and send the response
    response = "**Key Ideas Extracted:**\n\n"
    for i, idea in enumerate(ideas[:10]):  # Limit to top 10 ideas
        response += f"{i+1}. {idea['text']} (Score: {idea['score']})\n"
    
    await reply_to_user(ctx, response)

@client.slash_command(description="exit")
async def exit(ctx):
    await ctx.respond("Shutting down...")
    sys.exit(0)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('!'):
        await client.process_commands(message)
    elif client.user.mentioned_in(message):
        ctx = await client.get_context(message)
        
        async with ctx.typing():
            # Use the custom extraction API for general chat responses
            try:
                url = f"http://localhost:5000/api/custom_extraction"
                prompt = """Respond to the user's message in a helpful, informative, and conversational way. 
                If the user is asking a question, provide an answer. If they're making a comment, respond appropriately."""
                
                payload = {
                    "text": message.content,
                    "prompt": prompt,
                    "parse_score": False,
                    "temperature": 0.7
                }
                
                response = requests.post(url, json=payload, timeout=60)
                
                if response.status_code == 200:
                    result = response.json()
                    await reply_to_user(ctx, result['result'])
                else:
                    await reply_to_user(ctx, "I'm sorry, I couldn't process your message right now.")
            except Exception as e:
                print(f"[ERROR] Exception in chat response: {str(e)}")
                await reply_to_user(ctx, "I'm sorry, I encountered an error while processing your message.")

if __name__ == "__main__":
    client.run(discord_bot_token)
