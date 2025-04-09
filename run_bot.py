import discord
import datetime
import time
import sys
from credentials import DISCORD_BOT_TOKEN
from utils import get_transcripts_from_audio_data, answer_prompts, summarize_message, check_api_health

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
    print("You can start the API with: python -m semantic_engine_api.run")
    sys.exit(1)

# Init bot
bot = discord.Bot(intents=discord.Intents.all())  # We need message content and reaction intents
connections = {}

class MyView(discord.ui.View): # Create a class called MyView that subclasses discord.ui.View
    """a class that subclasses discord.ui.View that will display buttons to control the bot
    """
    def __init__(self, ctx, vc):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.vc = vc
        
    # Button that starts recording
    @discord.ui.button(label="Start", style=discord.ButtonStyle.primary, emoji="🔴")
    async def start(self, button, interaction):
        await interaction.response.edit_message(content = "recording....")   
        self.vc.start_recording(
            discord.sinks.WaveSink(),  # The sink type to use.
            once_done,  # callback function after recording is finished.
            self.ctx.channel  # The channel to disconnect from.
        )

    # Button that stops recording
    @discord.ui.button(label="Stop", style=discord.ButtonStyle.primary, emoji="⬜")
    async def stop(self, button, interaction):
        if self.ctx.guild.id in connections:  # Check if the guild is in the cache.
            self.vc = connections[self.ctx.guild.id]
            self.vc.stop_recording()  # Stop recording, and call the callback (once_done).
            await interaction.response.edit_message(content = "You Can Start recording!",  view=MyView(self.ctx,self.vc))
        else:
            await self.ctx.respond("I am currently not recording here.")  # Respond with this if we aren't recording.

async def once_done(sink: discord.sinks, channel: discord.TextChannel):
    """Callback function after recording is finished. Process audio input and pass it to chatGPT, then send response in chat.

    Args:
        sink (discord.sinks): Audio Sink
        channel (discord.TextChannel): Channel to send reponse in
    """
    print("[DEBUG] Starting once_done callback")
    msg = await channel.send("Creating response...")
    
    # Filter bots out
    for user_id in list(sink.audio_data.keys()):
        user = await bot.fetch_user(user_id)
        if user.bot:
            del sink.audio_data[user_id]

    recorded_users = [  # A list of recorded users
        f"<@{user_id}>"
        for user_id, _ in sink.audio_data.items()
    ]

    print(f"[DEBUG] Recorded users: {recorded_users}")

    # Prepare files for transcription
    input_audio_data = {
        f"<@{user_id}>": audio.file
        for user_id, audio in sink.audio_data.items()
    }

    print("[DEBUG] Calling get_transcripts_from_audio_data")
    transcripts = await get_transcripts_from_audio_data(input_audio_data)
    print(f"[DEBUG] Received transcripts: {transcripts}")
    
    await msg.edit(f"finished recording prompts for: {', '.join(recorded_users)}.")  # Send a message to notify that recording finished.
    
    # Send prompt responses
    print("[DEBUG] Calling answer_prompts")
    await answer_prompts(transcripts, channel) # Sends answers for users prompts
    print("[DEBUG] Finished processing audio")

@bot.command(description="Sends the bot's latency.") # this decorator makes a slash command
async def ping(ctx): # a slash command will be created with the name "ping"
    await ctx.respond(f"Pong! Latency is {bot.latency}")

@bot.command(description="Join")
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

@bot.command(description="Leave")
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
@bot.event
async def on_ready():
    """Prints message to console once we successfully load the bot
    """
    print('We have logged in as {0.user}'.format(bot) + ' ' + datetime.datetime.utcnow().strftime("%m/%d/%Y %H:%M:%S UTC"))

@bot.event
async def on_reaction_add(reaction, user):
    """Handle reaction adds to messages"""
    # Ignore bot's own reactions
    if user == bot.user:
        return
        
    # If the reaction is the robot emoji
    if str(reaction.emoji) == "🤖":
        message = reaction.message
        # Send a processing message
        processing_msg = await message.channel.send("Summarizing message, please wait...")
        
        try:
            # Get the summary from the summarization service via API
            result = summarize_message(message.content)
            
            # Send the title first
            await message.reply(f"**{result['title']}**")
            
            # Split the summary into chunks of 1900 characters (leaving room for formatting)
            summary_chunks = [result['summary'][i:i+1900] for i in range(0, len(result['summary']), 1900)]
            
            # Send each chunk as a separate message
            for i, chunk in enumerate(summary_chunks):
                if i == 0:
                    # First chunk as a reply to the original message
                    await message.reply(chunk)
                else:
                    # Subsequent chunks as regular messages
                    await message.channel.send(chunk)
                    
        except Exception as e:
            await message.reply(f"Sorry, I couldn't summarize that message. Error: {str(e)}")
        finally:
            # Delete the processing message
            await processing_msg.delete()

# Run bot
if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN) 