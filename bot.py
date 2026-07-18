import os
import re
import discord
from discord.ext import commands
from discord import app_commands
import json
import asyncio
from datetime import datetime

# ========== Configuration ==========
BOT_TOKEN = os.getenv('BOT_TOKEN')
OWNER_ID = 1173953184113360910  # Owner ID for notifications

# LITECOIN CONFIGURATION
LITECOIN_ADDRESS = "LX9UuyZGTx8eiCCCk2hzRGTgZCMHph8UDi"

# NOTE: this is a static rate. LTC/USD moves constantly, so before going live
# either wire this up to a live price API (CoinGecko, Kraken, etc.) or update
# it manually on a schedule. Charging customers off a stale rate is how you
# under/over-charge them.
LTC_USD_RATE = 75.00

# Channel IDs
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

SUPPORTED_CRYPTO = ["litecoin"]
DELIVERY_METHODS = ["gamepass", "preloaded_account", "giftcard", "in_game"]

ORDER_STATUSES = {
    "pending": "⏳ Waiting for payment...",
    "processing": "⚙️ Processing...",
    "completed": "✅ Completed",
    "cancelled": "❌ Cancelled"
}


def safe_channel_name(name: str) -> str:
    """Mirror Discord's own channel-name sanitization so our duplicate-ticket
    check actually matches what Discord will create. Discord lowercases,
    replaces whitespace with hyphens, and strips characters outside
    [a-z0-9-_]."""
    name = name.lower().strip()
    name = re.sub(r'\s+', '-', name)
    name = re.sub(r'[^a-z0-9\-_]', '', name)
    return name or "ticket"


def calculate_robux_price(amount: int) -> float:
    """Base (Gamepass) price for a given Robux amount. Delivery-method
    multipliers (preloaded 2x, giftcard 2.5x) are applied on top of this."""
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


def parse_robux_amount(raw: str):
    """Parse '25000', '25,000', or '50k' into an int. Returns None if invalid."""
    raw = raw.strip().lower().replace(',', '')
    try:
        if raw.endswith('k'):
            return int(float(raw[:-1]) * 1000)
        return int(raw)
    except ValueError:
        return None


class Order:
    def __init__(self, user_id, amount, delivery_method, payment_method, price, order_type="robux"):
        self.user_id = user_id
        self.amount = amount  # int (Robux qty) for order_type == "robux", str (account name) for "account"
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


# ========== TICKET SYSTEM ==========
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🛒 Buy Robux", style=discord.ButtonStyle.green, custom_id="buy_robux")
    async def buy_robux_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"[buy_robux] clicked by {interaction.user} ({interaction.user.id})")
        await self.create_ticket(interaction, "robux")

    @discord.ui.button(label="👤 Buy Account", style=discord.ButtonStyle.blurple, custom_id="buy_account")
    async def buy_account_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        print(f"[buy_account] clicked by {interaction.user} ({interaction.user.id})")
        await self.create_ticket(interaction, "account")

    @discord.ui.button(label="💎 Sell Items", style=discord.ButtonStyle.secondary, custom_id="sell_items")
    async def sell_items_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "sell")

    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str):
        guild = interaction.guild
        expected_name = f"ticket-{safe_channel_name(interaction.user.name)}"

        # Acknowledge immediately — creating a channel + overwrites can easily
        # take longer than Discord's 3-second interaction ack window, which is
        # what causes "The application didn't respond in time".
        await interaction.response.defer(ephemeral=True)

        try:
            # Check if user already has an open ticket (matches Discord's own sanitization)
            for channel in guild.channels:
                if channel.name == expected_name:
                    await interaction.followup.send("You already have an open ticket!", ephemeral=True)
                    return

            category = guild.get_channel(TICKET_CATEGORY_ID)
            if not category:
                category = discord.utils.get(guild.categories, name="Tickets")
                if not category:
                    category = await guild.create_category("Tickets")

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            owner = guild.get_member(OWNER_ID)
            if owner:
                overwrites[owner] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            # Store the opener's ID in the channel topic so the Close button can
            # tell who's allowed to close it without a separate lookup table.
            channel = await guild.create_text_channel(
                expected_name, category=category, overwrites=overwrites, topic=str(interaction.user.id)
            )
            print(f"[create_ticket] channel created: {channel.name} ({channel.id})")
        except discord.Forbidden:
            print("[create_ticket] FORBIDDEN — bot is missing Manage Channels (or category permission) in this server.")
            await interaction.followup.send(
                "❌ I don't have permission to create ticket channels here. Ask an admin to grant me **Manage Channels**.",
                ephemeral=True
            )
            return
        except Exception:
            import traceback
            traceback.print_exc()
            await interaction.followup.send("❌ Something went wrong creating your ticket. Staff have been notified.", ephemeral=True)
            return

        type_labels = {
            "robux": "Robux Purchase",
            "account": "Account Purchase",
            "sell": "Selling Items"
        }
        panel_titles = {
            "robux": "Buy Robux™ - Robux",
            "account": "Buy Robux™ - Roblox Accounts",
            "sell": "Buy Robux™ - Sell Your Items"
        }

        embed = discord.Embed(
            title=panel_titles[ticket_type],
            description=(
                f"Welcome {interaction.user.mention}!\n\n"
                f"You've opened a ticket for **{type_labels[ticket_type]}**.\n"
                f"A staff member has been notified and your order is starting now."
            ),
            color=discord.Color.green()
        )
        await channel.send(embed=embed, view=TicketCloseView())

        if ticket_type == "robux":
            await start_robux_flow(channel, interaction.user)
        elif ticket_type == "account":
            account_embed = discord.Embed(
                title="Select an account",
                description="Choose the account you'd like to purchase below.",
                color=discord.Color.purple()
            )
            await channel.send(embed=account_embed, view=AccountOrderView())
        elif ticket_type == "sell":
            sell_embed = discord.Embed(
                title="Selling items",
                description=f"Please wait for <@{OWNER_ID}> to assist you!",
                color=discord.Color.gold()
            )
            await channel.send(embed=sell_embed)
            owner_user = bot.get_user(OWNER_ID)
            if owner_user:
                await owner_user.send(f"💎 {interaction.user.name} wants to sell items! Check {channel.mention}")

        await interaction.followup.send(f"✅ Ticket created! Check {channel.mention}", ephemeral=True)

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        import traceback
        print(f"[TicketView] unhandled error in item {item}:")
        traceback.print_exception(type(error), error, error.__traceback__)
        try:
            if interaction.response.is_done():
                await interaction.followup.send("❌ Something went wrong. Staff have been notified.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Something went wrong. Staff have been notified.", ephemeral=True)
        except discord.HTTPException:
            pass


# ========== TICKET CLOSE ==========
class ConfirmCloseView(discord.ui.View):
    def __init__(self, channel: discord.TextChannel):
        super().__init__(timeout=60)
        self.channel = channel

    @discord.ui.button(label="Confirm close", style=discord.ButtonStyle.danger, custom_id="confirm_close")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Closing ticket...", ephemeral=True)
        await asyncio.sleep(2)
        try:
            await self.channel.delete()
        except discord.HTTPException:
            pass

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, custom_id="cancel_close")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Close cancelled.", view=None)


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        opener_id = int(channel.topic) if channel.topic and channel.topic.isdigit() else None
        is_opener = opener_id is not None and interaction.user.id == opener_id
        is_staff = interaction.user.guild_permissions.administrator

        if not (is_opener or is_staff):
            await interaction.response.send_message("Only the ticket opener or staff can close this ticket.", ephemeral=True)
            return

        await interaction.response.send_message(
            "Are you sure you want to close this ticket?",
            view=ConfirmCloseView(channel),
            ephemeral=True
        )


# ========== CONFIRM PAYMENT (shared handler) ==========
class ConfirmPaymentView(discord.ui.View):
    """Lets the buyer mark an order as 'awaiting review' and pings the owner
    to actually verify the on-chain payment before fulfilling it."""

    def __init__(self, order_id: str):
        super().__init__(timeout=None)
        self.order_id = order_id

    @discord.ui.button(label="✅ Confirm Payment", style=discord.ButtonStyle.success, custom_id="confirm_payment")
    async def confirm_payment(self, interaction: discord.Interaction, button: discord.ui.Button):
        order = order_manager.get_order(self.order_id)
        if not order:
            await interaction.response.send_message("❌ Order not found!", ephemeral=True)
            return

        if order.status != "pending":
            await interaction.response.send_message(
                f"This order is already marked **{order.status}**.", ephemeral=True
            )
            return

        order_manager.update_order_status(self.order_id, "processing")
        button.disabled = True
        button.label = "⏳ Awaiting Verification"
        await interaction.response.edit_message(view=self)

        owner = bot.get_user(OWNER_ID)
        if owner:
            await owner.send(
                f"🔔 {interaction.user.name} says they've paid for order `{self.order_id}`.\n"
                f"Please verify the LTC transaction before marking it completed with `!order {self.order_id}`."
            )
        await interaction.followup.send(
            "Thanks — the owner has been notified and will verify the payment shortly.",
            ephemeral=True
        )


# ========== ROBUX ORDER FLOW ==========
async def start_robux_flow(channel: discord.TextChannel, user: discord.User):
    """Auto-prompts for the Robux amount right after ticket creation (no
    button needed — matches the reference flow) and pins the prompt."""
    prompt_embed = discord.Embed(
        title="How much Robux would you like to buy?",
        description=(
            "Please specify the amount of Robux you would like to purchase.\n"
            "Example: `25000` or `50k`\n"
            "The minimum order amount is **1,000 Robux**"
        ),
        color=discord.Color.blue()
    )
    prompt_msg = await channel.send(embed=prompt_embed)
    try:
        await prompt_msg.pin()
    except discord.HTTPException:
        pass

    def check(m):
        return m.author.id == user.id and m.channel.id == channel.id

    while True:
        try:
            msg = await bot.wait_for('message', timeout=300.0, check=check)
        except asyncio.TimeoutError:
            await channel.send("⏰ No response received. Send a message with the amount to try again, or ask staff for help.")
            return

        amount = parse_robux_amount(msg.content)
        if amount is None:
            await channel.send("❌ Please enter a valid number, e.g. `25000` or `50k`.")
            continue
        if amount < 1000:
            await channel.send("❌ Minimum order is 1,000 Robux — try again.")
            continue
        break

    price = calculate_robux_price(amount)
    embed = discord.Embed(
        title="📦 How would you like to receive your Robux?",
        description=f"Amount: **{amount:,} Robux**\nBase price: **${price:.2f}**",
        color=discord.Color.blue()
    )
    await channel.send(embed=embed, view=DeliveryMethodSelectView(amount, price))


class DeliveryMethodSelect(discord.ui.Select):
    def __init__(self, amount: int, price: float):
        self.amount = amount
        self.price = price
        options = [
            discord.SelectOption(
                label="Gamepass", value="gamepass", emoji="🎮",
                description=f"${price:.2f} — sent via gamepass purchase"
            ),
            discord.SelectOption(
                label="Pre-loaded account", value="preloaded_account", emoji="👤",
                description=f"${price * 2:.2f} — our pre-loaded account"
            ),
            discord.SelectOption(
                label="Roblox giftcard", value="giftcard", emoji="🎁",
                description=f"${price * 2.5:.2f} — Roblox giftcard code"
            ),
            discord.SelectOption(
                label="In-game trade", value="in_game", emoji="🕹️",
                description="Ask staff for in-game delivery"
            ),
        ]
        super().__init__(placeholder="Select how you would like to receive robux",
                          min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        method = self.values[0]

        if method == "in_game":
            await interaction.response.send_message(
                f"Got it! In-game was chosen, please wait for the owner - <@{OWNER_ID}>", ephemeral=False
            )
            owner = bot.get_user(OWNER_ID)
            if owner:
                await owner.send(f"🎮 {interaction.user.name} chose In-Game delivery for {self.amount:,} Robux! Check {interaction.channel.mention}")
            return

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


class DeliveryMethodSelectView(discord.ui.View):
    def __init__(self, amount: int, price: float):
        super().__init__(timeout=None)
        self.add_item(DeliveryMethodSelect(amount, price))


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
        ltc_amount = round(self.price / LTC_USD_RATE, 8)

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

        await interaction.response.send_message(embed=embed, view=ConfirmPaymentView(order.order_id))

        owner = bot.get_user(OWNER_ID)
        if owner:
            await owner.send(f"🆕 New Robux Order!\nOrder ID: `{order.order_id}`\nUser: {interaction.user.name}\nAmount: {self.amount:,} Robux\nPrice: ${self.price:.2f}\nCheck {interaction.channel.mention}")


# ========== ACCOUNT ORDER VIEWS ==========
class AccountOrderView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Korblox Account ($19.99)", style=discord.ButtonStyle.secondary, custom_id="korblox")
    async def korblox(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_account(interaction, "Korblox Account", ACCOUNT_PRICES["korblox"])

    @discord.ui.button(label="Headless Account ($29.99)", style=discord.ButtonStyle.secondary, custom_id="headless")
    async def headless(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_account(interaction, "Headless Account", ACCOUNT_PRICES["headless"])

    @discord.ui.button(label="Violet Valkyrie ($39.99)", style=discord.ButtonStyle.secondary, custom_id="valkyrie")
    async def valkyrie(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_account(interaction, "Violet Valkyrie Account", ACCOUNT_PRICES["valkyrie"])

    @discord.ui.button(label="Korblox + Headless ($49.99)", style=discord.ButtonStyle.secondary, custom_id="korblox_headless")
    async def korblox_headless(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_account(interaction, "Korblox + Headless Account", ACCOUNT_PRICES["korblox_headless"])

    @discord.ui.button(label="Korblox + Headless + Valkyrie ($59.99)", style=discord.ButtonStyle.secondary, custom_id="korblox_headless_valkyrie")
    async def korblox_headless_valkyrie(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_account(interaction, "Korblox + Headless + Valkyrie Account", ACCOUNT_PRICES["korblox_headless_valkyrie"])

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
        ltc_amount = round(self.price / LTC_USD_RATE, 8)

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

        await interaction.response.send_message(embed=embed, view=ConfirmPaymentView(order.order_id))

        owner = bot.get_user(OWNER_ID)
        if owner:
            await owner.send(f"🆕 New Account Order!\nOrder ID: `{order.order_id}`\nUser: {interaction.user.name}\nAccount Type: {self.account_type}\nPrice: ${self.price:.2f}\nCheck {interaction.channel.mention}")


# ========== SETUP COMMANDS ==========
@bot.command(name='setup_robux')
@commands.has_permissions(administrator=True)
async def setup_robux(ctx):
    embed = discord.Embed(title="Buy Robux™ - Robux", color=discord.Color.blue())
    embed.add_field(
        name="Information",
        value="This bot streamlines purchasing and distributing Robux. Please read the info below.",
        inline=False
    )
    embed.add_field(name="Fully Automated Payments", value="Seamless, automated transactions.", inline=False)
    embed.add_field(name="Transaction Security", value="Safe and secure payment process.", inline=False)
    embed.add_field(name="Delivery Method", value="Robux is delivered via Gamepass, Pre-loaded Account or Roblox Giftcard.", inline=False)
    embed.add_field(name="Payment Methods", value="Cryptocurrency (Litecoin)", inline=False)
    embed.add_field(
        name="Products",
        value="• **Gamepass**: Standard Price\n• **Pre-loaded Account**: 2× Price\n• **Roblox Giftcard**: 2.5× Price",
        inline=False
    )
    embed.add_field(
        name="Example",
        value="10,000 Robux → $10.00 (Gamepass)\n10,000 Robux → $20.00 (Pre-loaded Account)\n10,000 Robux → $25.00 (Roblox Giftcard)",
        inline=False
    )

    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="🛒 BUY ROBUX", style=discord.ButtonStyle.green, custom_id="buy_robux"))
    await ctx.send(embed=embed, view=view)
    await ctx.send("✅ Buy Robux panel setup complete!")


@bot.command(name='setup_accounts')
@commands.has_permissions(administrator=True)
async def setup_accounts(ctx):
    embed = discord.Embed(title="Buy Robux™ - Roblox Accounts", color=discord.Color.purple())
    embed.add_field(name="Information", value="Purchase and delivery of Roblox accounts.", inline=False)
    embed.add_field(name="Delivery Method", value="Accounts delivered via login credentials with original creation e-mail.", inline=False)
    embed.add_field(name="Payment Methods", value="Cryptocurrency (Litecoin)", inline=False)
    embed.add_field(
        name="Products",
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
    embed = discord.Embed(title="Buy Robux™ - Sell Your Items", color=discord.Color.gold())
    embed.add_field(
        name="Information",
        value="We buy Roblox Limiteds, Robux, in-game items, and active Roblox groups. Open a ticket to discuss.",
        inline=False
    )
    embed.add_field(name="Payment Methods", value="Litecoin, PayPal, other by arrangement", inline=False)

    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="💎 Sell Your Items", style=discord.ButtonStyle.secondary, custom_id="sell_items"))
    await ctx.send(embed=embed, view=view)
    await ctx.send("✅ Sell Items panel setup complete!")


# ========== ADMIN COMMANDS ==========
@bot.command(name='orders')
@commands.has_permissions(administrator=True)
async def list_orders(ctx):
    pending_orders = [o for o in order_manager.orders.values() if o.status == "pending"]

    if not pending_orders:
        await ctx.send("✅ No pending orders!")
        return

    embed = discord.Embed(title=f"📋 Pending Orders ({len(pending_orders)})", color=discord.Color.blue())

    for order in pending_orders[:10]:
        display_amount = f"{order.amount:,}" if order.order_type == "robux" else str(order.amount)
        embed.add_field(
            name=order.order_id,
            value=f"User: <@{order.user_id}>\nType: {order.order_type.title()}\nAmount: {display_amount}\nPrice: ${order.price:.2f}",
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

    embed = discord.Embed(title=f"📋 Order Details - {order_id}", color=discord.Color.blue())
    embed.add_field(name="User", value=f"<@{order.user_id}>", inline=True)
    embed.add_field(name="Type", value=order.order_type.title(), inline=True)
    embed.add_field(name="Status", value=ORDER_STATUSES.get(order.status, order.status), inline=True)

    if order.order_type == "robux":
        embed.add_field(name="Amount", value=f"{order.amount:,} Robux", inline=True)
        embed.add_field(name="Delivery Method", value=order.delivery_method.replace('_', ' ').title(), inline=True)
    else:
        embed.add_field(name="Account Type", value=str(order.amount), inline=True)

    embed.add_field(name="Price", value=f"${order.price:.2f}", inline=True)
    if order.payment_amount:
        embed.add_field(name="LTC Amount", value=f"{order.payment_amount} LTC", inline=True)
    embed.add_field(name="Created", value=order.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)

    view = discord.ui.View()
    for status in ("processing", "completed", "cancelled"):
        async def make_callback(interaction: discord.Interaction, order_id=order_id, status=status):
            order_manager.update_order_status(order_id, status)
            await interaction.response.send_message(f"✅ Order `{order_id}` marked **{status}**.", ephemeral=True)

        button = discord.ui.Button(label=status.title(), style=discord.ButtonStyle.secondary, custom_id=f"set_status_{status}")
        button.callback = make_callback
        view.add_item(button)

    await ctx.send(embed=embed, view=view)


# ========== BOT EVENTS ==========
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    # Register persistent views so buttons keep working after a restart
    bot.add_view(TicketView())
    bot.add_view(TicketCloseView())
    bot.add_view(AccountOrderView())

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Slash command sync failed: {e}")


if __name__ == "__main__":
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set.")
    bot.run(BOT_TOKEN)
