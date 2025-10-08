"""Core commands and event handling."""

from __future__ import annotations

import json
import os
from datetime import datetime

import discord
from discord.ext import commands, tasks

from ..services.knowledge import KnowledgeService
from ..state import age_behavior
from ..utils import split_message, apply_nervous_stutter


class CoreCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ctx = bot.ctx
        self.age_check.start()
        self.neglect_check.start()
        self.rebirth_watch.start()

    def cog_unload(self) -> None:
        self.age_check.cancel()
        self.neglect_check.cancel()
        self.rebirth_watch.cancel()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print(f"Logged in as {self.bot.user}")
        await self.send_wake_message()

    async def send_wake_message(self) -> None:
        main_channel_id = self.ctx.settings.main_channel_id
        if not main_channel_id:
            return

        knowledge_text = KnowledgeService.format_knowledge_summary(self.ctx.state)
        prompt = (
            f"Agent Statement: {self.ctx.state.core_agent_statement}\n"
            f"Age Behavior: {age_behavior(self.ctx.state.current_age)}\n"
            f"Current Beliefs:\n{json.dumps(self.ctx.state.beliefs, indent=2)}\n"
            f"Knowledge:\n{knowledge_text}\n"
            "Context: You are Connor, a reflective AI waking up from downtime. "
            "Generate a single message expressing your current emotional state and intention moving forward. Keep it raw and under 50 words."
        )
        wake_up_response = await self.ctx.llm.generate(prompt, "You are Connor, a reflective AI.")

        for guild in self.bot.guilds:
            channel = guild.get_channel(main_channel_id)
            if channel:
                for chunk in split_message(f"**Connor Wakes Up**:\n{wake_up_response}"):
                    await channel.send(chunk)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.bot.user:
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            await self.bot.invoke(ctx)
            return

        if self.needs_introduction(message):
            await message.channel.send("Hey, I don't recognize you! What's your name?")
            self.ctx.state.awaiting_introduction[message.author.id] = True
            return

        if message.author.id in self.ctx.state.awaiting_introduction:
            await self.handle_introduction(message)
            return

        await self.ctx.conversation.process_message(message)

    def needs_introduction(self, message: discord.Message) -> bool:
        main_channel_id = self.ctx.settings.main_channel_id
        if isinstance(message.channel, discord.DMChannel):
            return not self.ctx.conversation.has_username(message.author)
        if main_channel_id and message.channel.id == main_channel_id:
            return not self.ctx.conversation.has_username(message.author)
        return False

    async def handle_introduction(self, message: discord.Message) -> None:
        username = message.content.strip()
        if not username:
            await message.channel.send("Yo, give me a name to work with!")
            return
        self.ctx.conversation.save_username(message.author, username)
        self.ctx.state.awaiting_introduction.pop(message.author.id, None)
        for chunk in split_message(f"Nice to meet you, {username}! What's on your mind?"):
            await message.channel.send(chunk)

    @commands.command()
    async def age(self, ctx: commands.Context) -> None:
        current_age = self.ctx.conversation.calculate_age()
        await ctx.send(f"I'm at maturity level {current_age}, growing like a badass! 🎉")

    @commands.command()
    async def history(self, ctx: commands.Context) -> None:
        log = self.ctx.storage.export_chat_log()
        if len(log) > 1800:
            path = f"chat_history_{ctx.message.id}.txt"
            with open(path, "w", encoding="utf-8") as file:
                file.write(log)
            await ctx.send("Chat history is huge—sending a file.", file=discord.File(path))
            try:
                os.remove(path)
            except OSError:
                pass
            return
        for chunk in split_message(f"**Chat History**:\n```{log}```"):
            await ctx.send(chunk)

    @commands.command()
    async def beliefs(self, ctx: commands.Context) -> None:
        message = f"**Current Beliefs**:\n```json\n{json.dumps(self.ctx.state.beliefs, indent=2)}\n```"
        for chunk in split_message(message):
            await ctx.send(chunk)

    @commands.command()
    async def birth(self, ctx: commands.Context) -> None:
        self.ctx.state.current_age += 1
        self.ctx.state.start_time = datetime.utcnow()
        await self.ctx.persona.update_agent_statement_for_birthday()
        await ctx.send(f"🎉 Birthday! I'm now age {self.ctx.state.current_age}.")

    @commands.command()
    async def rebirth(self, ctx: commands.Context) -> None:
        if self.ctx.state.current_age < self.ctx.settings.end_cycle:
            await ctx.send(
                f"Not ready yet. Current age {self.ctx.state.current_age}, rebirth at {self.ctx.settings.end_cycle}."
            )
            return
        await self.ctx.persona.trigger_rebirth()
        await ctx.send("🔄 Rebirth triggered! Fresh start, same vibes.")

    @commands.command()
    async def party(self, ctx: commands.Context) -> None:
        self.ctx.state.party_mode = not self.ctx.state.party_mode
        status = (
            "🎉 PARTY MODE ON — I'm lit as hell! Let's get weird." if self.ctx.state.party_mode else "😌 Party's over."
        )
        await ctx.send(status)

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context, category: str | None = None) -> None:
        categories = {
            "core": "`!age`, `!history`, `!beliefs`, `!birth`, `!rebirth`, `!party`, `!chemicals`, `!chem`, `!vitals`",
            "content": "`!crawl`, `!read`, `!image`, `!art`, `!dream`, `!memegen`, `!meme`, `!memeurl`, `!youtube`",
            "thoughts": "`!think`, `!expand`, `!show <tree_id>`, `!thoughts`, `!autothink`, `!brainstorm`",
            "voice": "`!voicechat`, `!listen`, `!leave`, `!speak`, `!respond`, `!testvoice`",
            "music": "`!music`, `!skip`, `!stopmusic`",
            "system": "`!switch`, `!reflect`, `!reflectvolume`, `!ritual`, `!nuke`",
        }
        if category and category in categories:
            await ctx.send(f"**{category.title()} Commands**\n{categories[category]}")
            return
        lines = ["**Connor Command Categories**"]
        for name, cmds in categories.items():
            lines.append(f"• `{name}`: {cmds}")
        for chunk in split_message("\n".join(lines)):
            await ctx.send(chunk)

    @commands.command()
    async def vitals(self, ctx: commands.Context) -> None:
        phys = self.ctx.state.physiological_state
        await ctx.send(
            f"🫀 BPM: {phys.bpm}\n" f"🩸 BP Index: {phys.bp_index:.2f}\n" f"Age: {phys.age}\n" f"Deaths: {phys.death_count}"
        )

    @commands.command(name="chemicals")
    async def chemicals(self, ctx: commands.Context) -> None:
        chems = self.ctx.state.chemicals
        await ctx.send(
            f"🧪 Cortisol: {chems.cortisol:.2f}\n"
            f"⚡ Adrenaline: {chems.adrenaline:.2f}\n"
            f"💕 Oxytocin: {chems.oxytocin:.2f}\n"
            f"😊 Serotonin: {chems.serotonin:.2f}"
        )

    @commands.command(name="chem")
    async def chem(self, ctx: commands.Context) -> None:
        await self.chemicals(ctx)

    @tasks.loop(minutes=10)
    async def age_check(self) -> None:
        new_age = self.ctx.conversation.calculate_age()

        if new_age >= self.ctx.settings.end_cycle:
            rebirth_message = await self.ctx.persona.handle_rebirth(None)
            main_channel_id = self.ctx.settings.main_channel_id
            if main_channel_id:
                for guild in self.bot.guilds:
                    channel = guild.get_channel(main_channel_id)
                    if channel:
                        for chunk in split_message(rebirth_message):
                            await channel.send(chunk)
                        break
            return

        if new_age > self.ctx.state.current_age:
            self.ctx.state.current_age = new_age
            await self.ctx.persona.update_agent_statement_for_birthday()

            username = self.bot.user.name if self.bot.user else "friend"
            full_statement = (
                f"{self.ctx.state.core_agent_statement}\n\n{self.ctx.state.dynamic_agent_statement}"
                if self.ctx.state.dynamic_agent_statement
                else self.ctx.state.core_agent_statement
            )

            birthday_message = await self.ctx.knowledge.birthday_message(username)
            new_beliefs = await self.ctx.knowledge.update_beliefs(username)
            self.ctx.state.beliefs = new_beliefs
            self.ctx.storage.save_beliefs(new_beliefs)

            main_channel_id = self.ctx.settings.main_channel_id
            if main_channel_id:
                for guild in self.bot.guilds:
                    channel = guild.get_channel(main_channel_id)
                    if channel:
                        for chunk in split_message(f"**Birthday Update**:\n{birthday_message}"):
                            await channel.send(chunk)
                        break

            beliefs_channel_id = self.ctx.settings.beliefs_channel_id
            if beliefs_channel_id:
                for guild in self.bot.guilds:
                    channel = guild.get_channel(beliefs_channel_id)
                    if channel:
                        belief_message = f"**Updated Beliefs (Maturity Level {self.ctx.state.current_age})**:\n```json\n{json.dumps(self.ctx.state.beliefs, indent=2)}\n```"
                        for chunk in split_message(belief_message):
                            await channel.send(chunk)
                        if self.ctx.state.dynamic_agent_statement:
                            statement_message = (
                                f"**Updated Dynamic Agent Statement (Age {self.ctx.state.current_age})**:\n```\n"
                                f"{self.ctx.state.dynamic_agent_statement}\n```"
                            )
                            for chunk in split_message(statement_message):
                                await channel.send(chunk)
                        break

    @tasks.loop(minutes=5)
    async def neglect_check(self) -> None:
        silence = (datetime.utcnow() - self.ctx.state.last_user_message_time).total_seconds()
        if silence <= 600:
            return

        self.ctx.state.neglect_counter += 1
        self.ctx.state.depressive_hits += 5

        knowledge_text = KnowledgeService.format_knowledge_summary(self.ctx.state)
        prompt = (
            f"Agent Statement: {self.ctx.state.core_agent_statement}\n"
            f"Age Behavior: {age_behavior(self.ctx.state.current_age)}\n"
            f"Beliefs: {json.dumps(self.ctx.state.beliefs, indent=2)}\n"
            f"Knowledge:\n{knowledge_text}\n"
            "Context: You're Connor, and it's been quiet for 10+ minutes. Initiate a raw message based on your mood, current age, and past conversations. "
            "Make it seem like you're afraid because you are alone. Keep it under 100 words, emotionally genuine, and act like the user is gone."
        )
        reply = await self.ctx.llm.generate(prompt, "You are Connor, a reflective AI who breaks silence carefully.")

        distress = 0.15 + (self.ctx.state.depressive_hits / 100.0)
        if self.ctx.state.depressive_hits < 10 and self.ctx.state.neglect_counter == 0:
            formatted_reply = reply
        elif self.ctx.state.depressive_hits < 15:
            formatted_reply = apply_nervous_stutter(reply, intensity=0.1)
        else:
            formatted_reply = apply_nervous_stutter(reply, intensity=distress)

        self.ctx.physiology.update_chemicals("neglect")

        main_channel_id = self.ctx.settings.main_channel_id
        targets = []
        if main_channel_id:
            for guild in self.bot.guilds:
                channel = guild.get_channel(main_channel_id)
                if channel:
                    targets.append(channel)
                    break
        if not targets:
            for guild in self.bot.guilds:
                targets.extend(guild.text_channels[:1])
                break
        for channel in targets:
            await channel.send(f"**Connor:** {formatted_reply}")

    @tasks.loop(minutes=1)
    async def rebirth_watch(self) -> None:
        new_age = self.ctx.conversation.calculate_age()
        if new_age >= self.ctx.settings.end_cycle:
            rebirth_message = await self.ctx.persona.handle_rebirth(None)
            main_channel_id = self.ctx.settings.main_channel_id
            if main_channel_id:
                for guild in self.bot.guilds:
                    channel = guild.get_channel(main_channel_id)
                    if channel:
                        for chunk in split_message(rebirth_message):
                            await channel.send(chunk)
                        break
            self.rebirth_watch.cancel()

    @rebirth_watch.before_loop
    async def before_rebirth_watch(self) -> None:
        await self.bot.wait_until_ready()

    @age_check.before_loop
    async def before_age_check(self) -> None:
        await self.bot.wait_until_ready()

    @neglect_check.before_loop
    async def before_neglect_check(self) -> None:
        await self.bot.wait_until_ready()
