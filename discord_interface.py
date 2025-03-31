import os
import datetime
import discord
from discord.ext import commands
from dotenv import load_dotenv
import whisper
import wave
import io

from summarisation_service import get_summarization_service

load_dotenv()
discord_bot_token = os.getenv('DISCORD_BOT_TOKEN')
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")

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

# Initialize services
summarization_service = get_summarization_service()

# Placeholder functions for other services
async def get_related_topics(message: str) -> str:
    # TODO: Implement related topics service
    return "Related topics service not yet implemented"

async def fact_check_claim(claim: str) -> str:
    # TODO: Implement fact checking service
    return "Fact checking service not yet implemented"

async def get_definition(term: str, context: str = None) -> str:
    # TODO: Implement definition service
    return "Definition service not yet implemented"

async def get_chat_response(message: str) -> str:
    # TODO: Implement chat service
    return "Chat service not yet implemented"

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
    await ctx.respond("You Can Start recording!", view = MyView(ctx, vc))

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
            lst_str = response[1:-1].split(',')
            lst = [s.strip()[1:-1] for s in lst_str][:10]
            
            tags = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
            lst = [f"{tags[i]} {s}" for i, s in enumerate(lst)]
            lst = '\n'.join(lst)
            print(lst)
            reply = await message.reply('\n' + lst)
            for i in range(len(lst)):
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
            
            # Use the summarization service
            result = await summarization_service.generate_summary(messages_text)
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
    
    # Use the summarization service
    result = await summarization_service.generate_summary(messages_text)
    response = f"**{result['title']}**\n\n{result['summary']}"
    await reply_to_user(ctx, response)

summarize.help = "Summarizes the given text into a shorter, more concise version."

@client.command(description="related-channel")
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

related.help = "Searches the web for related topics based on the given query."

@client.command(description="define")
async def define(ctx):
    await ctx.message.reply("Searching online dictionaries. Please wait...")

    # Check if the command is a reply to a message in a thread
    if isinstance(ctx.message.reference.resolved, discord.Message):
        parent_message = ctx.message.reference.resolved
        term = ctx.message.content.replace('!define', '').strip()

        await ctx.send(f"Defining term {term}, in content: {parent_message.content}")
        response = await get_definition(term, parent_message.content)
        await reply_to_user(ctx, response)
    else:
        term = ctx.message.content.replace('!define', '').strip()
        response = await get_definition(term)
        await reply_to_user(ctx, response)
        await ctx.send("If you wish to provide context, use this command in a thread reply for the message you wish to use as context.")

define.help = "Returns the definition to a term."

@client.command(description="exit")
async def exit(ctx):
    exit()

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('!'):
        await client.process_commands(message)
    elif client.user.mentioned_in(message):
        ctx = await client.get_context(message)
        
        async with ctx.typing():
            response = await get_chat_response(message.content)
        
        await reply_to_user(ctx, response)

client.run(discord_bot_token)
