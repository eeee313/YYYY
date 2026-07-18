import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
from datetime import datetime
import random

# Configuration
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
OWNER_ID = 1173953184113360910

# LITECOIN CONFIGURATION
LITECOIN_ADDRESS = "LX9UuyZGTx8eiCCCk2hzRGTgZCMHph8UDi"

# Channel IDs
VOUCHES_CHANNEL_ID = 1527833204935889120
ORDER_HISTORY_CHANNEL_ID = 1527833245868363856

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Pricing configuration
PRICING = {
    "gamepass": 1.00,  # per 1K
    "preloaded": 2.00,  # per 1K
    "giftcard": 2.50,   # per 1K
    "account": 0.00     # Will be set per account type
}

# Account pricing
ACCOUNT_PRICES = {
    "headless": 50.00,
    "korblox": 75.00,
    "brainrot": 100.00,
    "limited": 150.00,
    "aged": 30.00
}

# Supported cryptocurrencies (Litecoin only for now)
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
    """Class to represent an order"""
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
        self.order_type = order_type  # "robux" or "account"

class OrderManager:
    """Manages all orders"""
    def __init__(self):
        self.orders = {}
        self.load_orders()
    
    def load_orders(self):
        """Load orders from file"""
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
        """Save orders to file"""
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
        """Create a new order"""
        order = Order(user_id, amount, delivery_method, payment_method, price, order_type)
        self.orders[order.order_id] = order
        self.save_orders()
        return order
    
    def get_order(self, order_id):
        """Get an order by ID"""
        return self.orders.get(order_id)
    
    def update_order_status(self, order_id, status):
        """Update order status"""
        if order_id in self.orders:
            self.orders[order_id].status = status
            self.save_orders()
            return True
        return False
    
    def update_payment_details(self, order_id, address, amount):
        """Update payment details for an order"""
        if order_id in self.orders:
            self.orders[order_id].payment_address = address
            self.orders[order_id].payment_amount = amount
            self.save_orders()
            return True
        return False

# Initialize order manager
order_manager = OrderManager()

# ========== AUTO-MESSAGING SYSTEM ==========
@tasks.loop(minutes=20)
async def auto_post_messages():
    """Post random messages every 20 minutes"""
    try:
        # Get channels
        vouches_channel = bot.get_channel(VOUCHES_CHANNEL_ID)
        order_history_channel = bot.get_channel(ORDER_HISTORY_CHANNEL_ID)
        
        if not vouches_channel or not order_history_channel:
            print("Could not find channels for auto-posting")
            return
        
        # Post random vouch
        if vouches_channel:
            vouch = random.choice(VOUCH_MESSAGES)
            customer = random.choice(CUSTOMER_NAMES)
            await vouches_channel.send(f"**{customer}** said:\n{vouch}")
            print(f"Posted vouch: {customer} - {vouch[:30]}...")
        
        # Post random ticket
        if order_history_channel:
            ticket = random.choice(TICKET_MESSAGES)
            customer = random.choice(CUSTOMER_NAMES)
            await order_history_channel.send(f"📋 **New Order from {customer}**\n{ticket}")
            print(f"Posted ticket: {customer} - {ticket[:30]}...")
            
    except Exception as e:
        print(f"Error in auto-posting: {e}")

@auto_post_messages.before_loop
async def before_auto_post():
    """Wait for bot to be ready before starting"""
    await bot.wait_until_ready()

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
    
    @discord.ui.button(label="💎 Sell Items", style=discord.ButtonStyle.gold, custom_id="sell_items")
    async def sell_items_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "sell")
    
    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        """Create a ticket channel"""
        guild = interaction.guild
        
        # Check if user already has a ticket
        for channel in guild.channels:
            if channel.name == f"ticket-{interaction.user.name.lower()}":
                await interaction.response.send_message("You already have an open ticket!", ephemeral=True)
                return
        
        # Create category if it doesn't exist
        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")
        
        # Create overwrites
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        # Add owner to all tickets
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
            # Notify owner
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
            
            # Store amount in view
            self.amount = amount
            
            # Show delivery methods
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
        """Calculate price based on amount"""
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
        # Notify owner
        owner = bot.get_user(OWNER_ID)
        if owner:
            await owner.send(f"🎮 {interaction.user.name} chose In-Game delivery for {self.amount:,} Robux! Check {interaction.channel.mention}")
    
    async def process_delivery(self, interaction: discord.Interaction, method: str):
        """Process delivery method selection"""
        # Calculate final price based on delivery method
        final_price = self.price
        if method == "preloaded_account":
            final_price = self.price * 2
        elif method == "giftcard":
            final_price = self.price * 2.5
        
        # Show payment methods
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
        # Show crypto options (only Litecoin for now)
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
        # Generate payment invoice
        ltc_amount = self.price / 75  # Assuming $75 per LTC (approximate rate)
        ltc_amount = round(ltc_amount, 8)
        
        # Create order
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
        view.add_item(discord.ui.Button(label="📋 Copy Address", style=discord.ButtonStyle.secondary, custom_id="copy_address", disabled=True))
        view.add_item(discord.ui.Button(label="✅ Confirm Payment", style=discord.ButtonStyle.success, custom_id="confirm_payment"))
        
        await interaction.response.send_message(embed=embed, view=view)
        
        # Notify owner
        owner = bot.get_user(OWNER_ID)
        if owner:
            await owner.send(f"🆕 New Robux Order!\nOrder ID: `{order.order_id}`\nUser: {interaction.user.name}\nAmount: {self.amount:,} Robux\nPrice: ${self.price:.2f}\nCheck {interaction.channel.mention}")

# ========== ACCOUNT ORDER VIEWS ==========
class AccountOrderView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Headless Account", style=discord.ButtonStyle.secondary, custom_id="headless")
    async def headless(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_account(interaction, "headless", "$50.00")
    
    @discord.ui.button(label="Korblox Account", style=discord.ButtonStyle.secondary, custom_id="korblox")
    async def korblox(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_account(interaction, "korblox", "$75.00")
    
    @discord.ui.button(label="Brainrot Account", style=discord.ButtonStyle.secondary, custom_id="brainrot")
    async def brainrot(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_account(interaction, "brainrot", "$100.00")
    
    @discord.ui.button(label="Limited Account", style=discord.ButtonStyle.secondary, custom_id="limited")
    async def limited(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_account(interaction, "limited", "$150.00")
    
    @discord.ui.button(label="Aged Account", style=discord.ButtonStyle.secondary, custom_id="aged")
    async def aged(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_account(interaction, "aged", "$30.00")
    
    async def process_account(self, interaction: discord.Interaction, account_type: str, price_str: str):
        """Process account purchase"""
        price = float(price_str.replace('$', ''))
        
        embed = discord.Embed(
            title="👤 Account Purchase",
            description=f"You selected: **{account_type.title()} Account**\nPrice: **{price_str}**",
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
        # Generate payment invoice
        ltc_amount = self.price / 75  # Assuming $75 per LTC
        ltc_amount = round(ltc_amount, 8)
        
        # Create order
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
        embed.add_field(name="👤 Account Type", value=self.account_type.title(), inline=False)
        embed.add_field(name="💰 Price", value=f"${self.price:.2f}", inline=False)
        embed.add_field(name="📤 Send To", value=f"```{LITECOIN_ADDRESS}```", inline=False)
        embed.add_field(name="💵 Amount", value=f"```{ltc_amount} LTC```", inline=False)
        embed.add_field(name="⏳ Status", value="⏳ Waiting for payment...", inline=False)
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="✅ Confirm Payment", style=discord.ButtonStyle.success, custom_id="confirm_payment"))
        
        await interaction.response.send_message(embed=embed, view=view)
        
        # Notify owner
        owner = bot.get_user(OWNER_ID)
        if owner:
            await owner.send(f"🆕 New Account Order!\nOrder ID: `{order.order_id}`\nUser: {interaction.user.name}\nAccount Type: {self.account_type.title()}\nPrice: ${self.price:.2f}\nCheck {interaction.channel.mention}")

# ========== COMMANDS ==========
@bot.command(name='setup')
@commands.has_permissions(administrator=True)
async def setup(ctx):
    """Setup the ticket system in the current channel"""
    embed = discord.Embed(
        title="🛒 Buy Robux™",
        description="Welcome to Buy Robux™!\n\nClick the buttons below to get started:",
        color=discord.Color.green()
    )
    embed.add_field(
        name="📋 Information",
        value="• Fully automated payments\n• Secure transactions\n• Multiple delivery methods\n• Account safety guaranteed",
        inline=False
    )
    embed.add_field(
        name="💳 Payment Methods",
        value="• Cryptocurrency (Litecoin)\n• More coming soon!",
        inline=False
    )
    
    await ctx.send(embed=embed, view=TicketView())
    await ctx.send("✅ Setup complete! The ticket system is now active.")

@bot.command(name='order')
@commands.has_permissions(administrator=True)
async def view_order(ctx, order_id: str):
    """View order details (Admin only)"""
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
        embed.add_field(name="Account Type", value=order.amount.title(), inline=True)
    
    embed.add_field(name="Price", value=f"${order.price:.2f}", inline=True)
    embed.add_field(name="Status", value=ORDER_STATUSES.get(order.status, order.status), inline=True)
    
    if order.payment_address:
        embed.add_field(name="Payment Address", value=f"```{order.payment_address}```", inline=False)
    if order.payment_amount:
        embed.add_field(name="Payment Amount", value=f"{order.payment_amount} LTC", inline=True)
    
    embed.add_field(name="Created At", value=order.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="✅ Complete Order", style=discord.ButtonStyle.success, custom_id="complete_order"))
    view.add_item(discord.ui.Button(label="❌ Cancel Order", style=discord.ButtonStyle.danger, custom_id="cancel_order"))
    
    await ctx.send(embed=embed, view=view)

@bot.command(name='orders')
@commands.has_permissions(administrator=True)
async def list_orders(ctx):
    """List all pending orders (Admin only)"""
    pending_orders = [o for o in order_manager.orders.values() if o.status == "pending"]
    
    if not pending_orders:
        await ctx.send("✅ No pending orders!")
        return
    
    embed = discord.Embed(
        title=f"📋 Pending Orders ({len(pending_orders)})",
        color=discord.Color.blue()
    )
    
    for order in pending_orders[:10]:  # Show first 10
        embed.add_field(
            name=order.order_id,
            value=f"User: <@{order.user_id}>\nType: {order.order_type.title()}\nPrice: ${order.price:.2f}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    """Called when bot is ready"""
    print(f'✅ Bot is ready! Logged in as {bot.user}')
    print(f'📊 Connected to {len(bot.guilds)} guilds')
    
    # Start auto-posting
    auto_post_messages.start()
    print('🔄 Auto-posting started (every 20 minutes)')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")

# ========== SLASH COMMANDS ==========
@bot.tree.command(name="ping", description="Check bot latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

@bot.tree.command(name="setup", description="Setup the ticket system (Admin only)")
@discord.app_commands.default_permissions(administrator=True)
async def slash_setup(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🛒 Buy Robux™",
        description="Welcome to Buy Robux™!\n\nClick the buttons below to get started:",
        color=discord.Color.green()
    )
    embed.add_field(
        name="📋 Information",
        value="• Fully automated payments\n• Secure transactions\n• Multiple delivery methods\n• Account safety guaranteed",
        inline=False
    )
    embed.add_field(
        name="💳 Payment Methods",
        value="• Cryptocurrency (Litecoin)\n• More coming soon!",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, view=TicketView())

# ========== EVENT HANDLERS ==========
@bot.event
async def on_interaction(interaction: discord.Interaction):
    """Handle button interactions"""
    if interaction.type != discord.InteractionType.component:
        return
    
    custom_id = interaction.data.get('custom_id', '')
    
    # Handle confirm payment
    if custom_id == 'confirm_payment':
        await interaction.response.send_message("⏳ Payment confirmation received! Please wait for the owner to verify your payment.", ephemeral=True)
        
        # Notify owner
        owner = bot.get_user(OWNER_ID)
        if owner:
            await owner.send(f"💳 {interaction.user.name} confirmed payment in {interaction.channel.mention}")
    
    # Handle complete order (admin only)
    elif custom_id == 'complete_order':
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Only the owner can complete orders!", ephemeral=True)
            return
        
        # Extract order ID from message
        if interaction.message and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            if embed.title and embed.title.startswith("📋 Order Details -"):
                order_id = embed.title.replace("📋 Order Details - ", "")
                order_manager.update_order_status(order_id, "completed")
                await interaction.response.send_message("✅ Order marked as completed!")
                
                # Notify user
                order = order_manager.get_order(order_id)
                if order:
                    user = bot.get_user(order.user_id)
                    if user:
                        await user.send(f"✅ Your order `{order_id}` has been completed! Enjoy your purchase!")
    
    # Handle cancel order (admin only)
    elif custom_id == 'cancel_order':
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ Only the owner can cancel orders!", ephemeral=True)
            return
        
        # Extract order ID from message
        if interaction.message and interaction.message.embeds:
            embed = interaction.message.embeds[0]
            if embed.title and embed.title.startswith("📋 Order Details -"):
                order_id = embed.title.replace("📋 Order Details - ", "")
                order_manager.update_order_status(order_id, "cancelled")
                await interaction.response.send_message("❌ Order cancelled!")
                
                # Notify user
                order = order_manager.get_order(order_id)
                if order:
                    user = bot.get_user(order.user_id)
                    if user:
                        await user.send(f"❌ Your order `{order_id}` has been cancelled. Please contact support if you have questions.")

# ========== RUN BOT ==========
if __name__ == "__main__":
    bot.run(BOT_TOKEN)
