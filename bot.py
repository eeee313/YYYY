import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import asyncio
from datetime import datetime
import random

# Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = 1173953184113360910  # Owner ID for notifications

# LITECOIN CONFIGURATION
LITECOIN_ADDRESS = "LX9UuyZGTx8eiCCCk2hzRGTgZCMHph8UDi"

# Channel IDs
VOUCHES_CHANNEL_ID = 1527833204935889120
ORDER_HISTORY_CHANNEL_ID = 1527833245868363856
TICKET_CATEGORY_ID = 1527856283498184876  # Ticket category

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Pricing configuration
PRICING = {
    "gamepass": 1.00,
    "preloaded": 2.00,
    "giftcard": 2.50,
    "account": 0.00
}

# Account pricing
ACCOUNT_PRICES = {
    "korblox": 19.99,
    "headless": 29.99,
    "valkyrie": 39.99,
    "korblox_headless": 49.99,
    "korblox_headless_valkyrie": 59.99
}

# Supported cryptocurrencies
SUPPORTED_CRYPTO = ["litecoin"]

# Valid delivery methods
DELIVERY_METHODS = ["gamepass", "preloaded_account", "giftcard", "in_game"]

# Valid order statuses
ORDER_STATUSES = {
    "pending": "⏳ Waiting for payment...",
    "processing": "⚙️ Processing...",
    "completed": "✅ Completed",
    "cancelled": "❌ Cancelled"
}

# Random messages for auto-posting
TICKET_MESSAGES = [
    "Just bought 25k Robux! Fast service! 🚀",
    "Another happy customer! Got my Robux in 5 mins!",
    "Best Robux seller ever! Buying more soon!",
    "50k Robux received! Perfect transaction!",
    "Great service, will recommend to friends!",
    "Just got my 100k Robux! Amazing!",
    "Fast and reliable! 10/10!",
    "Best prices around! Just bought 75k!",
    "Already bought 3 times from here! Never disappointed!",
    "100k Robux within 10 minutes! Insane service!",
    "Just ordered 30k Robux! Can't wait!",
    "My go-to Robux seller! Great deals!",
    "Got my Robux super fast! Highly recommend!",
    "Cheapest prices and fastest delivery!",
    "Finally found a reliable seller! Just got 40k Robux!"
]

VOUCH_MESSAGES = [
    "⭐ ⭐ ⭐ ⭐ ⭐ Amazing service! Got my Robux instantly!",
    "⭐ ⭐ ⭐ ⭐ ⭐ Best seller on Discord! 100% legit!",
    "⭐ ⭐ ⭐ ⭐ ⭐ Fast, cheap, reliable! What more could you want?",
    "⭐ ⭐ ⭐ ⭐ ⭐ Legit seller! Already bought 3 times!",
    "⭐ ⭐ ⭐ ⭐ ⭐ Very professional! Will buy again!",
    "⭐ ⭐ ⭐ ⭐ ⭐ Great prices and fast delivery!",
    "⭐ ⭐ ⭐ ⭐ ⭐ 10/10 experience! Highly recommend!",
    "⭐ ⭐ ⭐ ⭐ ⭐ Trusted seller! Got my 50k Robux quick!",
    "⭐ ⭐ ⭐ ⭐ ⭐ Already convinced my friends to buy here!",
    "⭐ ⭐ ⭐ ⭐ ⭐ Best Robux seller on Discord! Period!",
    "⭐ ⭐ ⭐ ⭐ ⭐ Very trustworthy! Great communication!",
    "⭐ ⭐ ⭐ ⭐ ⭐ Fastest delivery I've ever seen!",
    "⭐ ⭐ ⭐ ⭐ ⭐ Cheap prices and legit! Can't beat it!",
    "⭐ ⭐ ⭐ ⭐ ⭐ Been buying for months! Always perfect!",
    "⭐ ⭐ ⭐ ⭐ ⭐ Absolute legend! Got my Robux in minutes!"
]

CUSTOMER_NAMES = [
    "Dark_Blaze", "CyberNinja", "Shadow_Knight", "Ice_Crystal",
    "Storm_Fury", "Neon_Dragon", "Mystic_Wolf", "Thunder_Bolt",
    "Ghost_Walker", "Flame_Phoenix", "Dream_Weaver", "Star_Glow",
    "Wolf_Pack", "Dark_Soul", "Light_Bringer", "Night_Hawk",
    "Silent_Shadow", "Crimson_King", "Golden_Eagle", "Moon_Light"
]

class Order:
    def __init__(self, user_id, amount, delivery_method, payment_method, price, order_type="robux"):
        self.user_id = user_id
        self.amount = amount
        self.delivery_method = delivery_method
        self.payment_method = payment_method
        self.price = price
        self.status = "pending"
        self.created_at = datetime.now()
        self.order_id = f"ORDER-{datetime.now().strftime('%Y%m%d%H%M%S')}-{user_id}"
        self.payment_address = None
        self.payment_amount = None
        self.order_type = order_type

class OrderManager:
    def __init__(self):
        self.orders = {}
        self.load_orders()
    
    def load_orders(self):
        try:
            if os.path.exists('orders.json'):
                with open('orders.json', 'r') as f:
                    data = json.load(f)
                    for key, value in data.items():
                        order = Order(value['user_id'], value['amount'], 
                                    value['delivery_method'], value['payment_method'], 
                                    value['price'], value.get('order_type', 'robux'))
                        order.status = value['status']
                        order.order_id = value['order_id']
                        order.created_at = datetime.fromisoformat(value['created_at'])
                        order.payment_address = value.get('payment_address')
                        order.payment_amount = value.get('payment_amount')
                        self.orders[key] = order
        except FileNotFoundError:
            pass
    
    def save_orders(self):
        data = {}
        for key, order in self.orders.items():
            data[key] = {
                'user_id': order.user_id,
                'amount': order.amount,
                'delivery_method': order.delivery_method,
                'payment_method': order.payment_method,
                'price': order.price,
                'status': order.status,
                'order_id': order.order_id,
                'created_at': order.created_at.isoformat(),
                'payment_address': order.payment_address,
                'payment_amount': order.payment_amount,
                'order_type': order.order_type
            }
        with open('orders.json', 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_order(self, user_id, amount, delivery_method, payment_method, price, order_type="robux"):
        order = Order(user_id, amount, delivery_method, payment_method, price, order_type)
        self.orders[order.order_id] = order
        self.save_orders()
        return order
    
    def get_order(self, order_id):
        return self.orders.get(order_id)
    
    def update_order_status(self, order_id, status):
        if order_id in self.orders:
            self.orders[order_id].status = status
            self.save_orders()
            return True
        return False
    
    def update_payment_details(self, order_id, address, amount):
        if order_id in self.orders:
            self.orders[order_id].payment_address = address
            self.orders[order_id].payment_amount = amount
            self.save_orders()
            return True
        return False

order_manager = OrderManager()

# ========== AUTO-MESSAGING SYSTEM ==========
@tasks.loop(minutes=20)
async def auto_post_messages():
    try:
        vouches_channel = bot.get_channel(VOUCHES_CHANNEL_ID)
        order_history_channel = bot.get_channel(ORDER_HISTORY_CHANNEL_ID)
        
        if not vouches_channel or not order_history_channel:
            print("Could not find channels for auto-posting")
            return
        
        if vouches_channel:
            vouch = random.choice(VOUCH_MESSAGES)
            customer = random.choice(CUSTOMER_NAMES)
            await vouches_channel.send(f"**{customer}** said:\n{vouch}")
            print(f"Posted vouch: {customer} - {vouch[:30]}...")
        
        if order_history_channel:
            ticket = random.choice(TICKET_MESSAGES)
            customer = random.choice(CUSTOMER_NAMES)
            await order_history_channel.send(f"📋 **New Order from {customer}**\n{ticket}")
            print(f"Posted ticket: {customer} - {ticket[:30]}...")
            
    except Exception as e:
        print(f"Error in auto-posting: {e}")

@auto_post_messages.before_loop
async def before_auto_post():
    await bot.wait_until_ready()

# ========== SLASH COMMANDS ==========
@bot.tree.command(name="sendorder", description="Send a random order message to order history channel (Admin only)")
@app_commands.default_permissions(administrator=True)
async def slash_sendorder(interaction: discord.Interaction):
    """Send a random order message to order history channel"""
    try:
        order_history_channel = bot.get_channel(ORDER_HISTORY_CHANNEL_ID)
        if not order_history_channel:
            await interaction.response.send_message("❌ Order history channel not found!", ephemeral=True)
            return
        
        ticket = random.choice(TICKET_MESSAGES)
        customer = random.choice(CUSTOMER_NAMES)
        await order_history_channel.send(f"📋 **New Order from {customer}**\n{ticket}")
        await interaction.response.send_message(f"✅ Order message sent to {order_history_channel.mention}!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

@bot.tree.command(name="sendvouch", description="Send a random vouch message to vouches channel (Admin only)")
@app_commands.default_permissions(administrator=True)
async def slash_sendvouch(interaction: discord.Interaction):
    """Send a random vouch message to vouches channel"""
    try:
        vouches_channel = bot.get_channel(VOUCHES_CHANNEL_ID)
        if not vouches_channel:
            await interaction.response.send_message("❌ Vouches channel not found!", ephemeral=True)
            return
        
        vouch = random.choice(VOUCH_MESSAGES)
        customer = random.choice(CUSTOMER_NAMES)
        await vouches_channel.send(f"**{customer}** said:\n{vouch}")
        await interaction.response.send_message(f"✅ Vouch message sent to {vouches_channel.mention}!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

# ========== SETUP COMMANDS ==========
@bot.command(name='setup_robux')
@commands.has_permissions(administrator=True)
async def setup_robux(ctx):
    """Setup Buy Robux panel - Matches screenshot 2"""
    embed = discord.Embed(
        title="# Buy Robux™ - Robux",
        description="",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="## Information",
        value="• This bot is a Discord bot designed to streamline the process of purchasing and distributing Robux, the virtual currency used in Roblox. We insist to read all the articles below \"important\" category.",
        inline=False
    )
    embed.add_field(
        name="## Fully Automated Payments:",
        value="• Experience seamless transactions with our fully automated payment system.",
        inline=False
    )
    embed.add_field(
        name="## Transaction Security:",
        value="• Our bot guarantees a safe and secure payment process every time.",
        inline=False
    )
    embed.add_field(
        name="## Delivery Method:",
        value="• Robux is delivered via Gamepass, Pre-loaded Account or Roblox Giftcard.",
        inline=False
    )
    embed.add_field(
        name="## Account Safety:",
        value="• You will not get banned for purchasing Robux, our goods are supplied by legitimate individuals.",
        inline=False
    )
    embed.add_field(
        name="---",
        value="",
        inline=False
    )
    embed.add_field(
        name="## Payment Methods",
        value="• **Cryptocurrency** (Bitcoin / Litecoin / Ethereum / Solana / Tether USDT)\n• **Card** (Credit / Debit / ApplePay / GooglePay / And More...)\n• **PayPal** (PayPal Balance / PayPal Card / And More...)\n• **Giftcards** (Steam / Binance / PaySafe / Rewarble)",
        inline=False
    )
    embed.add_field(
        name="---",
        value="",
        inline=False
    )
    embed.add_field(
        name="## Products",
        value="• **Robux Rates:**\n  • **Gamepass**: Standard Price\n  • **Pre-loaded Account**: 2× Price\n  • **Roblox Giftcard**: 2.5× Price",
        inline=False
    )
    embed.add_field(
        name="## Example:",
        value="• 10,000 Robux → $10.00 (Gamepass)\n• 10,000 Robux → $20.00 (Pre-loaded Account)\n• 10,000 Robux → $25.00 (Roblox Giftcard)",
        inline=False
    )
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="🛒 BUY ROBUX", style=discord.ButtonStyle.green, custom_id="buy_robux"))
    await ctx.send(embed=embed, view=view)
    await ctx.send("✅ Buy Robux panel setup complete!")

@bot.command(name='setup_accounts')
@commands.has_permissions(administrator=True)
async def setup_accounts(ctx):
    """Setup Buy Accounts panel - Matches screenshot 3"""
    embed = discord.Embed(
        title="# Buy Robux™ - Roblox Accounts",
        description="",
        color=discord.Color.purple()
    )
    embed.add_field(
        name="## Information",
        value="• This bot is a Discord bot designed to streamline the process of purchasing and distributing Roblox Products, the virtual gaming platform. We insist to read all the articles below \"important\" category.",
        inline=False
    )
    embed.add_field(
        name="## Fully Automated Payments:",
        value="• Experience seamless transactions with our fully automated payment system.",
        inline=False
    )
    embed.add_field(
        name="## Transaction Security:",
        value="• Our bot guarantees a safe and secure payment process every time.",
        inline=False
    )
    embed.add_field(
        name="## Delivery Method:",
        value="• Roblox Accounts are delivered via Login Credentials with Original creation E-Mail.",
        inline=False
    )
    embed.add_field(
        name="## Account Safety:",
        value="• You will not get banned for purchasing Roblox Account.",
        inline=False
    )
    embed.add_field(
        name="---",
        value="",
        inline=False
    )
    embed.add_field(
        name="## Payment Methods",
        value="• **Cryptocurrency** (Bitcoin / Litecoin / Ethereum / Solana / Tether USDT)\n• **Card** (Credit / Debit / ApplePay / GooglePay / And More...)\n• **PayPal** (PayPal Balance / PayPal Card / And More...)\n• **Giftcards** (Steam / Binance / PaySafe / Rewarble)",
        inline=False
    )
    embed.add_field(
        name="---",
        value="",
        inline=False
    )
    embed.add_field(
        name="## Products",
        value="• **Korblox Account** | $19.99\n• **Headless Account** | $29.99\n• **Violet Valkyrie Account** | $39.99\n• **Korblox + Headless Account** | $49.99\n• **Korblox + Headless + Valkyrie Account** | $59.99",
        inline=False
    )
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="👤 BUY ACCOUNT", style=discord.ButtonStyle.blurple, custom_id="buy_account"))
    await ctx.send(embed=embed, view=view)
    await ctx.send("✅ Buy Account panel setup complete!")

@bot.command(name='setup_sell')
@commands.has_permissions(administrator=True)
async def setup_sell(ctx):
    """Setup Sell Items panel - Matches screenshot 1"""
    embed = discord.Embed(
        title="Buy Robux™ - Sell Your Items",
        description="",
        color=discord.Color.gold()
    )
    embed.add_field(
        name="Information:",
        value="We cash out Roblox Limiteds. Robux. IN-Game Items. Clothing/Developer Active Roblox Group, and more! (Make Ticket & Ask)",
        inline=False
    )
    embed.add_field(
        name="Payment methods:",
        value="• **PayPal** | PayPal Transfer\n• **Cryptocurrency** | All Coins\n• **Other Methods** | Bank Transfer / Giftcards / Robux",
        inline=False
    )
    embed.add_field(
        name="Looking For:",
        value="• **Roblox Limiteds** | High Value Only\n• **Robux** | High Bulk Only\n• **IN-Game Items** | High Tier Only → Adopt Me / MM2 / Da Hood ETC...\n• **Clothing/Developer Roblox Groups** | Active Groups Only",
        inline=False
    )
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="💎 Sell Your Items", style=discord.ButtonStyle.secondary, custom_id="sell_items"))
    await ctx.send(embed=embed, view=view)
    await ctx.send("✅ Sell Items panel setup complete!")

# ========== TICKET SYSTEM ==========
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🛒 Buy Robux", style=discord.ButtonStyle.green, custom_id="buy_robux")
    async def buy_robux_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "robux")
    
    @discord.ui.button(label="👤 Buy Account", style=discord.ButtonStyle.blurple, custom_id="buy_account")
    async def buy_account_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "account")
    
    @discord.ui.button(label="💎 Sell Items", style=discord.ButtonStyle.secondary, custom_id="sell_items")
    async def sell_items_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "sell")
    
    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        guild = interaction.guild
        
        # Check if user already has a ticket
        for channel in guild.channels:
            if channel.name == f"ticket-{interaction.user.name.lower()}":
                await interaction.response.send_message("You already have an open ticket!", ephemeral=True)
                return
        
        # Get the ticket category by ID
        category = guild.get_channel(TICKET_CATEGORY_ID)
        if not category:
            # Fallback: create or find "Tickets" category
            category = discord.utils.get(guild.categories, name="Tickets")
            if not category:
                category = await guild.create_category("Tickets")
        
        # Create overwrites
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        owner = guild.get_member(OWNER_ID)
        if owner:
            overwrites[owner] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        # Create the ticket channel
        channel_name = f"ticket-{interaction.user.name.lower()}"
        channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        
        # Send welcome message based on ticket type
        embed = discord.Embed(
            title=f"🎫 Ticket Created",
            description=f"Welcome {interaction.user.mention}!",
            color=discord.Color.green()
        )
        
        if ticket_type == "robux":
            embed.add_field(name="Type", value="🛒 Robux Purchase", inline=False)
            await channel.send(embed=embed, view=RobuxOrderView())
        elif ticket_type == "account":
            embed.add_field(name="Type", value="👤 Account Purchase", inline=False)
            await channel.send(embed=embed, view=AccountOrderView())
        elif ticket_type == "sell":
            embed.add_field(name="Type", value="💎 Selling Items", inline=False)
            embed.add_field(name="Note", value=f"Please wait for <@{OWNER_ID}> to assist you!", inline=False)
            await channel.send(embed=embed)
            owner = bot.get_user(OWNER_ID)
            if owner:
                await owner.send(f"💎 {interaction.user.name} wants to sell items! Check {channel.mention}")
        
        await interaction.response.send_message(f"✅ Ticket created! Check {channel.mention}", ephemeral=True)

# ========== ROBUX ORDER VIEWS ==========
class RobuxOrderView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Enter Amount", style=discord.ButtonStyle.primary, custom_id="enter_amount")
    async def enter_amount(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Please enter the amount of Robux you want to buy (min 1000):", ephemeral=True)
        
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        
        try:
            msg = await bot.wait_for('message', timeout=60.0, check=check)
            amount = int(msg.content.replace(',', '').replace('k', '000').replace('K', '000'))
            
            if amount < 1000:
                await interaction.followup.send("❌ Minimum order is 1,000 Robux!", ephemeral=True)
                return
            
            self.amount = amount
            
            embed = discord.Embed(
                title="📦 Select Delivery Method",
                description=f"Amount: **{amount:,} Robux**\nPrice: **${self.calculate_price(amount):.2f}**",
                color=discord.Color.blue()
            )
            await interaction.channel.send(embed=embed, view=DeliveryMethodView(amount, self.calculate_price(amount)))
            
        except ValueError:
            await interaction.followup.send("❌ Invalid amount! Please enter a number.", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Timeout! Please start again.", ephemeral=True)
    
    def calculate_price(self, amount):
        if 1000 <= amount <= 24000:
            return (amount / 1000) * 1.00
        elif 25000 <= amount <= 49000:
            return (amount / 1000) * 0.90
        elif 50000 <= amount <= 99000:
            return (amount / 1000) * 0.80
        elif 100000 <= amount <= 249000:
            return (amount / 1000) * 0.70
        elif 250000 <= amount <= 499000:
            return (amount / 1000) * 0.60
        else:
            return (amount / 1000) * 0.50

class DeliveryMethodView(discord.ui.View):
    def __init__(self, amount, price):
        super().__init__(timeout=None)
        self.amount = amount
        self.price = price
    
    @discord.ui.button(label="Gamepass", style=discord.ButtonStyle.secondary, custom_id="gamepass")
    async def gamepass(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_delivery(interaction, "gamepass")
    
    @discord.ui.button(label="Pre-loaded Account", style=discord.ButtonStyle.secondary, custom_id="preloaded")
    async def preloaded(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_delivery(interaction, "preloaded_account")
    
    @discord.ui.button(label="Roblox Giftcard", style=discord.ButtonStyle.secondary, custom_id="giftcard")
    async def giftcard(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_delivery(interaction, "giftcard")
    
    @discord.ui.button(label="🎮 In-Game", style=discord.ButtonStyle.danger, custom_id="ingame")
    async def ingame(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"Got it! In-game was chosen, please wait for the owner - <@{OWNER_ID}>", ephemeral=False)
        owner = bot.get_user(OWNER_ID)
        if owner:
            await owner.send(f"🎮 {interaction.user.name} chose In-Game delivery for {self.amount:,} Robux! Check {interaction.channel.mention}")
    
    async def process_delivery(self, interaction: discord.Interaction, method: str):
        final_price = self.price
        if method == "preloaded_account":
            final_price = self.price * 2
        elif method == "giftcard":
            final_price = self.price * 2.5
        
        embed = discord.Embed(
            title="💳 Select Payment Method",
            description=f"Delivery: **{method.replace('_', ' ').title()}**\nAmount: **{self.amount:,} Robux**\nTotal Price: **${final_price:.2f}**",
            color=discord.Color.gold()
        )
        embed.add_field(name="Note", value="Only Cryptocurrency is accepted!", inline=False)
        
        await interaction.response.send_message(embed=embed, view=PaymentMethodView(self.amount, method, final_price))

class PaymentMethodView(discord.ui.View):
    def __init__(self, amount, delivery_method, price):
        super().__init__(timeout=None)
        self.amount = amount
        self.delivery_method = delivery_method
        self.price = price
    
    @discord.ui.button(label="Cryptocurrency", style=discord.ButtonStyle.green, custom_id="crypto")
    async def crypto(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🪙 Select Cryptocurrency",
            description="Choose your preferred cryptocurrency:",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed, view=CryptoSelectionView(self.amount, self.delivery_method, self.price))

class CryptoSelectionView(discord.ui.View):
    def __init__(self, amount, delivery_method, price):
        super().__init__(timeout=None)
        self.amount = amount
        self.delivery_method = delivery_method
        self.price = price
    
    @discord.ui.button(label="Litecoin", style=discord.ButtonStyle.blurple, custom_id="litecoin")
    async def litecoin(self, interaction: discord.Interaction, button: discord.ui.Button):
        ltc_amount = self.price / 75
        ltc_amount = round(ltc_amount, 8)
        
        order = order_manager.create_order(
            interaction.user.id,
            self.amount,
            self.delivery_method,
            "litecoin",
            self.price,
            "robux"
        )
        order_manager.update_payment_details(order.order_id, LITECOIN_ADDRESS, ltc_amount)
        
        embed = discord.Embed(
            title="💳 Litecoin Payment Invoice",
            description=f"**Order ID:** `{order.order_id}`",
            color=discord.Color.gold()
        )
        embed.add_field(name="📦 Order Details", value=f"Amount: {self.amount:,} Robux\nDelivery: {self.delivery_method.replace('_', ' ').title()}\nTotal: ${self.price:.2f}", inline=False)
        embed.add_field(name="📤 Send To", value=f"```{LITECOIN_ADDRESS}```", inline=False)
        embed.add_field(name="💰 Amount", value=f"```{ltc_amount} LTC```", inline=False)
        embed.add_field(name="💵 USD Value", value=f"**${self.price:.2f}**", inline=False)
        embed.add_field(name="⏳ Status", value="⏳ Waiting for payment...", inline=False)
        embed.add_field(name="⚠️ Note", value="Please send the exact amount. Your order will be processed once payment is confirmed.", inline=False)
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="✅ Confirm Payment", style=discord.ButtonStyle.success, custom_id="confirm_payment"))
        
        await interaction.response.send_message(embed=embed, view=view)
        
        owner = bot.get_user(OWNER_ID)
        if owner:
            await owner.send(f"🆕 New Robux Order!\nOrder ID: `{order.order_id}`\nUser: {interaction.user.name}\nAmount: {self.amount:,} Robux\nPrice: ${self.price:.2f}\nCheck {interaction.channel.mention}")

# ========== ACCOUNT ORDER VIEWS ==========
class AccountOrderView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Korblox Account ($19.99)", style=discord.ButtonStyle.secondary, custom_id="korblox")
    async def korblox(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_account(interaction, "Korblox Account", 19.99)
    
    @discord.ui.button(label="Headless Account ($29.99)", style=discord.ButtonStyle.secondary, custom_id="headless")
    async def headless(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_account(interaction, "Headless Account", 29.99)
    
    @discord.ui.button(label="Violet Valkyrie ($39.99)", style=discord.ButtonStyle.secondary, custom_id="valkyrie")
    async def valkyrie(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_account(interaction, "Violet Valkyrie Account", 39.99)
    
    @discord.ui.button(label="Korblox + Headless ($49.99)", style=discord.ButtonStyle.secondary, custom_id="korblox_headless")
    async def korblox_headless(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_account(interaction, "Korblox + Headless Account", 49.99)
    
    @discord.ui.button(label="Korblox + Headless + Valkyrie ($59.99)", style=discord.ButtonStyle.secondary, custom_id="korblox_headless_valkyrie")
    async def korblox_headless_valkyrie(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_account(interaction, "Korblox + Headless + Valkyrie Account", 59.99)
    
    async def process_account(self, interaction: discord.Interaction, account_type: str, price: float):
        embed = discord.Embed(
            title="👤 Account Purchase",
            description=f"You selected: **{account_type}**\nPrice: **${price:.2f}**",
            color=discord.Color.purple()
        )
        embed.add_field(name="Payment", value="Litecoin only", inline=False)
        await interaction.response.send_message(embed=embed, view=AccountPaymentView(account_type, price))

class AccountPaymentView(discord.ui.View):
    def __init__(self, account_type, price):
        super().__init__(timeout=None)
        self.account_type = account_type
        self.price = price
    
    @discord.ui.button(label="Pay with Litecoin", style=discord.ButtonStyle.green, custom_id="pay_account")
    async def pay_account(self, interaction: discord.Interaction, button: discord.ui.Button):
        ltc_amount = self.price / 75
        ltc_amount = round(ltc_amount, 8)
        
        order = order_manager.create_order(
            interaction.user.id,
            self.account_type,
            "account_delivery",
            "litecoin",
            self.price,
            "account"
        )
        order_manager.update_payment_details(order.order_id, LITECOIN_ADDRESS, ltc_amount)
        
        embed = discord.Embed(
            title="💳 Account Payment Invoice",
            description=f"**Order ID:** `{order.order_id}`",
            color=discord.Color.gold()
        )
        embed.add_field(name="👤 Account Type", value=self.account_type, inline=False)
        embed.add_field(name="💰 Price", value=f"${self.price:.2f}", inline=False)
        embed.add_field(name="📤 Send To", value=f"```{LITECOIN_ADDRESS}```", inline=False)
        embed.add_field(name="💵 Amount", value=f"```{ltc_amount} LTC```", inline=False)
        embed.add_field(name="⏳ Status", value="⏳ Waiting for payment...", inline=False)
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="✅ Confirm Payment", style=discord.ButtonStyle.success, custom_id="confirm_payment"))
        
        await interaction.response.send_message(embed=embed, view=view)
        
        owner = bot.get_user(OWNER_ID)
        if owner:
            await owner.send(f"🆕 New Account Order!\nOrder ID: `{order.order_id}`\nUser: {interaction.user.name}\nAccount Type: {self.account_type}\nPrice: ${self.price:.2f}\nCheck {interaction.channel.mention}")

# ========== ADMIN COMMANDS ==========
@bot.command(name='orders')
@commands.has_permissions(administrator=True)
async def list_orders(ctx):
    pending_orders = [o for o in order_manager.orders.values() if o.status == "pending"]
    
    if not pending_orders:
        await ctx.send("✅ No pending orders!")
        return
    
    embed = discord.Embed(
        title=f"📋 Pending Orders ({len(pending_orders)})",
        color=discord.Color.blue()
    )
    
    for order in pending_orders[:10]:
        embed.add_field(
            name=order.order_id,
            value=f"User: <@{order.user_id}>\nType: {order.order_type.title()}\nPrice: ${order.price:.2f}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='order')
@commands.has_permissions(administrator=True)
async def view_order(ctx, order_id: str):
    order = order_manager.get_order(order_id)
    if not order:
        await ctx.send("❌ Order not found!")
        return
    
    embed = discord.Embed(
        title=f"📋 Order Details - {order_id}",
        color=discord.Color.blue()
    )
    embed.add_field(name="User", value=f"<@{order.user_id}>", inline=True)
    embed.add_field(name="Type", value=order.order_type.title(), inline=True)
    
    if order.order_type == "robux":
        embed.add_field(name="Amount", value=f"{order.amount:,} Robux", inline=True)
        embed.add_field(name="Delivery Method", value=order.delivery_method.replace('_', ' ').title(), inline=True)
    else:
        embed.add_field(name="Account Type", value=order.amount, inline=True)
    
    embed.add_field(name="Price", value=f"${
