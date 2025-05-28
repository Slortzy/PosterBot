import discord
from discord import app_commands
import asyncio
import os
from dotenv import load_dotenv
from keep_alive import keep_alive

# Load environment variables
load_dotenv()

# Discord bot configuration
intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Global variables
ticket_messages = {}  # To store ticket messages
ANNOUNCEMENT_CHANNEL_NAME = "admin-announcements"

async def create_private_announcement_channel(guild: discord.Guild) -> discord.TextChannel:
    # Look for existing announcement channel
    channel = discord.utils.get(guild.text_channels, name=ANNOUNCEMENT_CHANNEL_NAME)
    
    # If channel doesn't exist, create it
    if not channel:
        # Set permissions for the channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Create the channel
        channel = await guild.create_text_channel(
            name=ANNOUNCEMENT_CHANNEL_NAME,
            overwrites=overwrites,
            topic="Canal d'annonces officiel - Seuls les administrateurs peuvent écrire ici"
        )
        
        # Send initial message
        await channel.send("🔒 Ce canal est réservé aux annonces officielles. Seuls les administrateurs peuvent y écrire.")
    
    return channel

async def get_or_create_tickets_category(guild: discord.Guild) -> discord.CategoryChannel:
    # Look for existing category
    category = discord.utils.get(guild.categories, name="Tickets")
    
    # If category doesn't exist, create it
    if not category:
        category = await guild.create_category(name="Tickets")
        
        # Set category permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        await category.edit(overwrites=overwrites)
    
    return category

@client.event
async def on_ready():
    print(f'Logged in as {client.user} (ID: {client.user.id})')
    print('------')
    
    # Display servers where the bot is present
    print("Connected to servers:")
    for guild in client.guilds:
        print(f"- {guild.name} (ID: {guild.id})")
        # Create announcement channel for each guild
        await create_private_announcement_channel(guild)

    # Register the commands
    try:
        await tree.sync()
        print("Commands synced successfully!")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@tree.command(name="announce", description="Envoyer une annonce dans le canal d'annonces")
@app_commands.describe(
    title="Titre de l'annonce",
    content="Contenu de l'annonce"
)
async def send_announcement(interaction: discord.Interaction, title: str, content: str):
    # Check if user has admin permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Vous devez être administrateur pour utiliser cette commande.", ephemeral=True)
        return

    try:
        # Get the announcement channel
        channel = discord.utils.get(interaction.guild.text_channels, name=ANNOUNCEMENT_CHANNEL_NAME)
        if not channel:
            channel = await create_private_announcement_channel(interaction.guild)

        # Create and send the embed
        embed = discord.Embed(
            title=title,
            description=content,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Annonce par {interaction.user.name}")
        
        await channel.send(embed=embed)
        await interaction.response.send_message("✅ Annonce envoyée avec succès!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Erreur lors de l'envoi de l'annonce: {str(e)}", ephemeral=True)

@tree.command(name="ticket", description="Créer un nouveau ticket")
@app_commands.describe(
    title="Titre du ticket",
    description="Description du ticket"
)
async def create_ticket(interaction: discord.Interaction, title: str, description: str):
    try:
        # Create embed for the ticket
        embed = discord.Embed(
            title=f"🎫 {title}",
            description=description,
            color=discord.Color.green()
        )
        embed.add_field(
            name="Instructions",
            value="Réagissez avec 🎫 pour créer un ticket",
            inline=False
        )
        embed.set_footer(text="ArkeonProject - Système de tickets")
        
        # Send message and add reaction
        message = await interaction.channel.send(embed=embed)
        await message.add_reaction("🎫")
        
        # Store message for reaction handling
        ticket_messages[message.id] = {"title": title, "description": description}
        
        await interaction.response.send_message("✅ Ticket créé avec succès!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Erreur lors de la création du ticket: {str(e)}", ephemeral=True)

@client.event
async def on_reaction_add(reaction, user):
    # Ignore bot reactions
    if user.bot:
        return

    message = reaction.message
    
    # Handle ticket creation
    if message.id in ticket_messages and str(reaction.emoji) == "🎫":
        try:
            # Remove user's reaction
            await reaction.remove(user)
            
            # Get ticket data
            ticket_data = ticket_messages[message.id]
            
            # Create new channel for ticket
            guild = message.guild
            
            # Get or create Tickets category
            category = await get_or_create_tickets_category(guild)
            
            # Create channel name
            channel_name = f"ticket-{user.name.lower()}"
            
            # Check if ticket already exists
            existing_ticket = discord.utils.get(category.channels, name=channel_name)
            if existing_ticket:
                await user.send("Vous avez déjà un ticket ouvert!")
                return
            
            # Permissions for new channel
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            # Create channel in Tickets category
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites
            )
            
            # Create embed for new channel
            embed = discord.Embed(
                title=f"Ticket: {ticket_data['title']}",
                description=f"Ticket créé par {user.mention}\n\n{ticket_data['description']}",
                color=discord.Color.green()
            )
            embed.set_footer(text="Réagissez avec 🔒 pour fermer le ticket")
            
            # Send embed and add close reaction
            ticket_message = await ticket_channel.send(embed=embed)
            await ticket_message.add_reaction("🔒")
            
            # Notify user
            await user.send(f"Votre ticket a été créé dans {ticket_channel.mention}")
            
        except Exception as e:
            print(f"Erreur lors de la création du ticket: {str(e)}")
            try:
                await user.send(f"Erreur lors de la création du ticket: {str(e)}")
            except:
                pass
    
    # Handle ticket closing
    elif str(reaction.emoji) == "🔒" and isinstance(message.channel, discord.TextChannel) and message.channel.name.startswith("ticket-"):
        if user == message.guild.owner or any(role.permissions.administrator for role in user.roles):
            await message.channel.send("Le ticket va être fermé dans 5 secondes...")
            await asyncio.sleep(5)
            try:
                await message.channel.delete()
            except Exception as e:
                print(f"Erreur lors de la suppression du canal: {str(e)}")

if __name__ == '__main__':
    print("Starting bot...")
    # Get token from environment variables
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Error: No token found in environment variables!")
        print("Please make sure to set DISCORD_TOKEN in your .env file or environment variables.")
        exit(1)
    
    # Start the keep alive web server
    keep_alive()
    # Start the bot
    client.run(token)
