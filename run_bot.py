import discord
import datetime
import time
import sys
import traceback
from credentials import DISCORD_BOT_TOKEN
from utils import get_transcripts_from_audio_data, answer_prompts, summarize_message, check_api_health, invoke_agent

# Configure more detailed logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("eva-bot")

# Check API health before starting
logger.info("Checking API health...")
max_retries = 5
retry_count = 0
api_ready = False

while retry_count < max_retries and not api_ready:
    if check_api_health():
        api_ready = True
        logger.info("API is healthy and ready!")
    else:
        retry_count += 1
        logger.warning(f"API not ready, retrying in 5 seconds... (Attempt {retry_count}/{max_retries})")
        time.sleep(5)

if not api_ready:
    logger.error("API is not available. Please make sure the API is running.")
    logger.error("You can start the API with: python -m semantic_engine_api.run")
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

@bot.command(description="Summarize recent messages")
async def summarize(ctx, messages: discord.Option(int, "Number of messages to summarize", min_value=2, max_value=100, default=10)):
    """Summarize the specified number of recent messages in the channel
    
    Args:
        ctx (discord.context): Discord context
        messages (int): Number of messages to summarize (default: 10)
    """
    # Send a processing message
    processing_msg = await ctx.respond(f"Summarizing the last {messages} messages, please wait...")
    
    try:
        # Fetch message history - slash commands don't appear in history, so no need to filter them out
        message_history = []
        message_count = 0
        
        async for message in ctx.channel.history(limit=100):  # Set higher limit to find enough non-bot messages
            # Skip bot messages (optional, remove if you want to include bot messages)
            if message.author.bot:
                continue
                
            # Add to history with author name
            message_history.append(f"{message.author.display_name}: {message.content}")
            message_count += 1
            
            # Stop once we have enough messages
            if message_count >= messages:
                break
        
        # Reverse to get chronological order
        message_history.reverse()
        
        # Skip if no messages found
        if not message_history:
            await processing_msg.edit(content="No valid messages found to summarize.")
            return
            
        # Join all messages into a single text with line breaks
        conversation_text = "\n".join(message_history)
        
        # Get the summary from the summarization service
        result = summarize_message(conversation_text)
        
        # Create a thread for the summary
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        thread_name = f"Summary {timestamp}"
        thread = await processing_msg.edit(content=f"**{result['title']}**", view=None)
        thread = await thread.create_thread(name=thread_name)
        
        # Split the summary into chunks of 1900 characters (leaving room for formatting)
        summary_chunks = [result['summary'][i:i+1900] for i in range(0, len(result['summary']), 1900)]
        
        # Send each chunk in the thread
        for chunk in summary_chunks:
            await thread.send(chunk)
            
    except Exception as e:
        import traceback
        print(f"Error in summarize command: {e}")
        print(traceback.format_exc())
        await processing_msg.edit(content=f"Sorry, I couldn't summarize those messages. Error: {str(e)}")

#login event
@bot.event
async def on_ready():
    """Prints message to console once we successfully load the bot
    """
    print('We have logged in as {0.user}'.format(bot) + ' ' + datetime.datetime.utcnow().strftime("%m/%d/%Y %H:%M:%S UTC"))
    
    # Sync commands with Discord
    print("Syncing commands with Discord...")
    try:
        synced = await bot.sync_commands()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

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
# A command to interact with the bot directly
@bot.event
async def on_message(message):
    # Don't respond to our own messages
    if message.author == bot.user:
        return
        
    # Check if eva is tagged in the message
    if bot.user.mentioned_in(message):
        logger.info(f"EVA tagged by {message.author.display_name}")
        
        # Get the reply reference
        if message.reference and message.reference.resolved:
            reference_message = message.reference.resolved
        else:
            reference_message = None
        
        # Get any additional explanation request 
        parts = message.content.split(' ', 1)
        mention_message = parts[1].strip() if len(parts) > 1 else ""
        
        # Send a processing message
        processing_msg = await message.reply("Generating reply, please wait...")
        
        try:
            # Get usernames
            mentioning_username = message.author.display_name

            messages = [
                {"role": "user", "content": mentioning_username + ": " + mention_message}
            ]
            
            # If there is a reference message, add it to the messages structure
            if reference_message:
                reference_username = reference_message.author.display_name
                messages.insert(0, {"role": "user", "content": reference_username + ": " + reference_message.content})
            
            # Call the agent service with the explanation inquiry
            logger.info(f"Calling agent API with request: {mention_message}")
            reply = await invoke_agent(
                messages, 
                thread_id=str(message.channel.id) + ":" + str(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            
            if not reply or reply.startswith("Error"):
                logger.error(f"Agent API returned error: {reply}")
                await processing_msg.edit(content=f"Sorry, I couldn't explain that message: {reply}")
                return
            
            logger.info("Received reply from agent API, sending reply")
            
            # Split the reply into chunks if needed (Discord has a 2000 character limit)
            reply_chunks = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
            
            # Send the reply chunks in the same channel
            for chunk in reply_chunks:
                await message.channel.send(chunk)
            
            logger.info(f"Successfully completed reply for {message.author.display_name}")
                
        except Exception as e:
            # Log the full exception with traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Error in !explain command: {str(e)}")
            logger.error(f"Traceback: {error_traceback}")
            
            # Give the user a detailed error message
            await processing_msg.edit(content=f"Sorry, I couldn't explain that message. An error occurred: {str(e)}")

# Run bot
if __name__ == "__main__":
    bot.run(DISCORD_BOT_TOKEN) 