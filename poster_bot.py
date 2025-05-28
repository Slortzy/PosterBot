import discord
from discord import app_commands
import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import threading
from typing import Optional
import os
from dotenv import load_dotenv
from keep_alive import keep_alive

# Charger les variables d'environnement
load_dotenv()

# Configuration du bot Discord
intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Variables globales
selected_channel: Optional[discord.TextChannel] = None
channels_list = []
ticket_messages = {}  # Pour stocker les messages de tickets

class DiscordBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Discord Bot Control Panel")
        self.root.geometry("600x700")
        
        # Frame principale
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Frame pour la sélection du canal
        channel_frame = ttk.Frame(main_frame)
        channel_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(channel_frame, text="Select Channel:").grid(row=0, column=0, sticky=tk.W, padx=(0,5))
        self.channel_var = tk.StringVar()
        self.channel_combo = ttk.Combobox(channel_frame, textvariable=self.channel_var)
        self.channel_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0,5))
        self.channel_combo.bind('<<ComboboxSelected>>', self.on_channel_select)
        
        # Bouton de rafraîchissement
        ttk.Button(channel_frame, text="🔄 Refresh", command=self.refresh_channels).grid(row=0, column=2, sticky=tk.E)
        
        # Section Message
        message_frame = ttk.LabelFrame(main_frame, text="Send Message", padding="10")
        message_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(message_frame, text="Title:").grid(row=0, column=0, sticky=tk.W)
        self.title_entry = ttk.Entry(message_frame, width=50)
        self.title_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(message_frame, text="Content:").grid(row=1, column=0, sticky=tk.W)
        self.content_text = tk.Text(message_frame, width=50, height=10)
        self.content_text.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(message_frame, text="Send Message", command=self.send_message).grid(row=2, column=1, sticky=tk.E, pady=10)
        
        # Section Ticket
        ticket_frame = ttk.LabelFrame(main_frame, text="Create Ticket", padding="10")
        ticket_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(ticket_frame, text="Ticket Title:").grid(row=0, column=0, sticky=tk.W)
        self.ticket_title_entry = ttk.Entry(ticket_frame, width=50)
        self.ticket_title_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(ticket_frame, text="Description:").grid(row=1, column=0, sticky=tk.W)
        self.ticket_desc_text = tk.Text(ticket_frame, width=50, height=5)
        self.ticket_desc_text.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(ticket_frame, text="Create Ticket", command=self.create_ticket).grid(row=2, column=1, sticky=tk.E, pady=10)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Bot starting...")
        ttk.Label(main_frame, textvariable=self.status_var).grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        self.update_channels_list()
    
    def refresh_channels(self):
        self.status_var.set("Refreshing channels list...")
        asyncio.run_coroutine_threadsafe(update_channels_list(), client.loop)
        self.root.after(1000, lambda: self.status_var.set("Channels list refreshed!"))
    
    def update_channels_list(self):
        global channels_list
        self.channel_combo['values'] = [ch.name for ch in channels_list]
        if not self.channel_combo['values']:
            self.status_var.set("No channels found. Try refreshing the list.")
        else:
            self.status_var.set(f"Found {len(channels_list)} channels")
    
    def on_channel_select(self, event):
        global selected_channel, channels_list
        channel_name = self.channel_var.get()
        selected_channel = next((ch for ch in channels_list if ch.name == channel_name), None)
        if selected_channel:
            self.status_var.set(f"Selected channel: {selected_channel.name}")
    
    def send_message(self):
        if not selected_channel:
            messagebox.showerror("Error", "Please select a channel first!")
            return
            
        title = self.title_entry.get().strip()
        content = self.content_text.get("1.0", tk.END).strip()
        
        if not title or not content:
            messagebox.showerror("Error", "Please fill in both title and content!")
            return
            
        asyncio.run_coroutine_threadsafe(
            self.send_discord_message(title, content),
            client.loop
        )
    
    async def send_discord_message(self, title: str, content: str):
        try:
            embed = discord.Embed(title=title, description=content, color=discord.Color.blue())
            await selected_channel.send(embed=embed)
            self.root.after(0, lambda: self.status_var.set("Message sent successfully!"))
            self.root.after(0, self.clear_message_fields)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to send message: {str(e)}"))
    
    def clear_message_fields(self):
        self.title_entry.delete(0, tk.END)
        self.content_text.delete("1.0", tk.END)
    
    def create_ticket(self):
        if not selected_channel:
            messagebox.showerror("Error", "Please select a channel first!")
            return
            
        title = self.ticket_title_entry.get().strip()
        description = self.ticket_desc_text.get("1.0", tk.END).strip()
        
        if not title or not description:
            messagebox.showerror("Error", "Please fill in both ticket title and description!")
            return
            
        asyncio.run_coroutine_threadsafe(
            self.create_discord_ticket(title, description),
            client.loop
        )
    
    async def create_discord_ticket(self, title: str, description: str):
        try:
            # Création de l'embed pour le ticket
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
            
            # Envoi du message et ajout de la réaction
            message = await selected_channel.send(embed=embed)
            await message.add_reaction("🎫")
            
            # Stocker le message pour la gestion des réactions
            global ticket_messages
            ticket_messages[message.id] = {"title": title, "description": description}
            
            # Mise à jour du statut
            self.root.after(0, lambda: self.status_var.set("Ticket created successfully!"))
            self.root.after(0, self.clear_ticket_fields)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to create ticket: {str(e)}"))
    
    def clear_ticket_fields(self):
        self.ticket_title_entry.delete(0, tk.END)
        self.ticket_desc_text.delete("1.0", tk.END)

async def get_or_create_tickets_category(guild: discord.Guild) -> discord.CategoryChannel:
    # Chercher la catégorie existante
    category = discord.utils.get(guild.categories, name="Tickets")
    
    # Si la catégorie n'existe pas, la créer
    if not category:
        category = await guild.create_category(name="Tickets")
        
        # Définir les permissions de la catégorie
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
    
    # Afficher les serveurs où le bot est présent
    print("Connected to servers:")
    for guild in client.guilds:
        print(f"- {guild.name} (ID: {guild.id})")
    
    # Mettre à jour la liste des canaux
    await update_channels_list()

@client.event
async def on_reaction_add(reaction, user):
    # Ignorer les réactions du bot
    if user.bot:
        return

    message = reaction.message
    
    # Gestion de la création des tickets
    if message.id in ticket_messages and str(reaction.emoji) == "🎫":
        try:
            # Supprimer la réaction de l'utilisateur
            await reaction.remove(user)
            
            # Récupérer les données du ticket
            ticket_data = ticket_messages[message.id]
            
            # Créer un nouveau canal pour le ticket
            guild = message.guild
            
            # Obtenir ou créer la catégorie Tickets
            category = await get_or_create_tickets_category(guild)
            
            # Créer le nom du canal
            channel_name = f"ticket-{user.name.lower()}"
            
            # Vérifier si un ticket existe déjà pour cet utilisateur
            existing_ticket = discord.utils.get(category.channels, name=channel_name)
            if existing_ticket:
                await user.send("Vous avez déjà un ticket ouvert!")
                return
            
            # Permissions pour le nouveau canal
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            
            # Créer le canal dans la catégorie Tickets
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites
            )
            
            # Créer l'embed pour le nouveau canal
            embed = discord.Embed(
                title=f"Ticket: {ticket_data['title']}",
                description=f"Ticket créé par {user.mention}\n\n{ticket_data['description']}",
                color=discord.Color.green()
            )
            embed.set_footer(text="Pour fermer le ticket, réagissez avec 🔒")
            
            # Envoyer l'embed et ajouter la réaction pour fermer
            ticket_message = await ticket_channel.send(embed=embed)
            await ticket_message.add_reaction("🔒")
            
            # Notifier l'utilisateur
            await user.send(f"Votre ticket a été créé dans {ticket_channel.mention}")
            
        except Exception as e:
            print(f"Erreur lors de la création du ticket: {str(e)}")
            try:
                await user.send(f"Erreur lors de la création du ticket: {str(e)}")
            except:
                pass
    
    # Gestion de la fermeture des tickets
    elif str(reaction.emoji) == "🔒" and isinstance(message.channel, discord.TextChannel) and message.channel.name.startswith("ticket-"):
        if user == message.guild.owner or any(role.permissions.administrator for role in user.roles):
            await message.channel.send("Le ticket va être fermé dans 5 secondes...")
            await asyncio.sleep(5)
            try:
                await message.channel.delete()
            except Exception as e:
                print(f"Erreur lors de la suppression du canal: {str(e)}")

async def update_channels_list():
    global channels_list
    channels_list.clear()  # Vider la liste existante
    for guild in client.guilds:
        channels_list.extend(guild.text_channels)
    
    # Mettre à jour l'interface si elle existe
    if hasattr(client, 'gui_instance'):
        client.gui_instance.root.after(0, client.gui_instance.update_channels_list)

def run_bot():
    # Récupérer le token depuis les variables d'environnement
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Error: No token found in environment variables!")
        print("Please make sure to set DISCORD_TOKEN in your .env file or environment variables.")
        exit(1)
    
    client.run(token)

def run_gui():
    root = tk.Tk()
    app = DiscordBotGUI(root)
    client.gui_instance = app  # Stocker l'instance de GUI pour les mises à jour
    root.mainloop()

if __name__ == '__main__':
    print("Starting bot...")
    # Démarrer le serveur web keep alive
    keep_alive()
    # Démarrer le bot dans un thread séparé
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # Démarrer l'interface graphique dans le thread principal
    run_gui() 