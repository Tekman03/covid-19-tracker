import asyncio
import datetime as dt
import os
import time
import uuid

import discord
from discord.ext import commands
from pymysql.err import IntegrityError

import src.utils as utils
from src.plotting import PlotEmpty, plot_csv, plot_graph

class Datacmds(commands.Cog):
    """Help commands"""
    __slots__ = ("bot", "continent_code")
    def __init__(self, bot):
        self.bot = bot
        self.continent_code = [
            "af",
            "as",
            "eu",
            "na",
            "oc",
            "sa"
        ]
    @commands.command(name="list")
    @commands.cooldown(3, 30, commands.BucketType.user)
    async def list_countries(self, ctx):
        text = ""
        i = 1
        data = await utils.get(self.bot.http_session, "/all")
        text = ""
        overflow_text = ""
        embeds = []
        for c in data:
            overflow_text += c["country"] + ", "
            if len(overflow_text) >= utils.DISCORD_LIMIT:

                embed = discord.Embed(
                    description=text.rstrip(", "),
                    color=utils.COLOR,
                    timestamp=utils.discord_timestamp()
                )
                text = overflow_text
                overflow_text = ""
                embeds.append(embed)
            text = overflow_text

        if text:
            embed = discord.Embed(
                    description=text.rstrip(", "),
                    color=utils.COLOR,
                    timestamp=utils.discord_timestamp()
                )

            embeds.append(embed)

        for i, _embed in enumerate(embeds):
            _embed.set_author(
                    name=f"All countries affected by Coronavirus COVID-19 - Page {i+1}",
                    icon_url=self.bot.author_thumb
                )
            _embed.set_footer(text=utils.last_update(data[0]["lastUpdate"]),
                            icon_url=ctx.me.avatar_url)
            _embed.set_thumbnail(url=self.bot.thumb + str(time.time()))
            await ctx.send(embed=_embed)

    @commands.command(name="info")
    @commands.cooldown(3, 30, commands.BucketType.user)
    async def info(self, ctx):
        data = await utils.get(self.bot.http_session, "/all")

        text = utils.string_formatting(data)
        embed = discord.Embed(
            description=text,
            color=utils.COLOR,
            timestamp=utils.discord_timestamp()
        )

        embed.set_author(
            name=f"All countries affected by Coronavirus COVID-19",
            url="https://www.who.int/home",
            icon_url=self.bot.author_thumb
            )
        embed.set_thumbnail(url=self.bot.thumb + str(time.time()))
        embed.set_footer(text="coronavirus.jessicoh.com/api | " + utils.last_update(data[0]["lastUpdate"]),
                        icon_url=ctx.me.avatar_url)

        if not os.path.exists(utils.STATS_PATH):
            history_confirmed = await utils.get(self.bot.http_session, f"/history/confirmed/total")
            history_recovered = await utils.get(self.bot.http_session, f"/history/recovered/total")
            history_deaths = await utils.get(self.bot.http_session, f"/history/deaths/total")
            await plot_csv(
                utils.STATS_PATH,
                history_confirmed,
                history_recovered,
                history_deaths)
        with open(utils.STATS_PATH, "rb") as p:
            img = discord.File(p, filename=utils.STATS_PATH)
        embed.set_image(url=f'attachment://{utils.STATS_PATH}')
        await ctx.send(file=img, embed=embed)


    # @commands.command()
    # async def daily(self, ctx, *args):
    #     if len(args) > 1:
    #         data_type = args[-1]
    #         country = ' '.join(args[:-1])
    #         print(data_type, country)
    #         history = await utils.get(self.bot.http_session, f"/{data_type}/{country}")
    #         data = await utils.get(self.bot.http_session, f"/{data_type}/{country}")


    @commands.command(name="country", aliases=["c"])
    @commands.cooldown(5, 30, commands.BucketType.user)
    async def country(self, ctx, *countries):
        if len(countries):
            data = await utils.get(self.bot.http_session, "/all")
            embeds = []
            text = overflow_text = ""
            i = 0
            stack = []
            countries = list(map(lambda x: x.lower(), countries))
            for d in data:
                for country in countries:
                    bold = "**" if i % 2 == 0 else ""
                    data_country = d['country'].lower()
                    if (data_country.startswith(country) or \
                        d['iso2'].lower() == country or \
                        d['iso3'].lower() == country) \
                        and data_country not in stack:
                        overflow_text += f"{bold}{d['country']} : {d['totalCases']:,} confirmed [+{d['newCases']:,}] - {d['totalRecovered']:,} recovered - {d['totalDeaths']:,} deaths [+{d['newDeaths']:,}]{bold}\n"
                        stack.append(data_country)
                        i += 1
                    if len(overflow_text) >= utils.DISCORD_LIMIT:
                        embed = discord.Embed(
                            title="Countries affected",
                            description=text,
                            timestamp=utils.discord_timestamp(),
                            color=utils.COLOR
                        )
                        overflow_text = ""
                    text = overflow_text
            if text:
                embed = discord.Embed(
                    description=text,
                    timestamp=utils.discord_timestamp(),
                    color=utils.COLOR
                )
                embeds.append(embed)
            for i, _embed in enumerate(embeds):
                _embed.set_author(
                        name=f"Countries affected",
                        icon_url=self.bot.author_thumb
                    )
                _embed.set_footer(text=f"coronavirus.jessicoh.com/api/ | {utils.last_update(data[0]['lastUpdate'])} | Page {i+1}",
                                icon_url=ctx.me.avatar_url)
                _embed.set_thumbnail(url=self.bot.thumb + str(time.time()))
                await ctx.send(embed=_embed)
        else:
            await ctx.send("No country provided")

    @commands.command(name="stats", aliases=["stat", "statistic", "s"])
    @commands.cooldown(5, 30, commands.BucketType.user)
    async def stats(self, ctx, *country):
        is_log = False
        graph_type = "Linear"
        embed = discord.Embed(
                description=utils.mkheader(),
                timestamp=dt.datetime.utcnow(),
                color=utils.COLOR
            )
        if len(country) == 1 and country[0].lower() == "log" or not len(country):
            data = await utils.get(self.bot.http_session, f"/all/world")
        splited = country

        if len(splited) == 1 and splited[0].lower() == "log":
            embed.set_author(
                name="Coronavirus COVID-19 logarithmic stats",
                icon_url=self.bot.author_thumb
            )
            is_log = True
            path = utils.STATS_LOG_PATH
            graph_type = "Logarithmic"
        elif not len(country):
            path = utils.STATS_PATH
        else:
            try:
                if splited[0].lower() == "log":
                    is_log = True

                    joined = ' '.join(country[1:]).lower()
                    data = await utils.get(self.bot.http_session, f"/all/{joined}")
                    path = data["iso2"].lower() + utils.STATS_LOG_PATH

                else:
                    joined = ' '.join(country).lower()
                    data = await utils.get(self.bot.http_session, f"/all/{joined}")
                    path = data["iso2"].lower() + utils.STATS_PATH
                if not os.path.exists(path):
                    history_confirmed = await utils.get(self.bot.http_session, f"/history/confirmed/{joined}")
                    history_recovered = await utils.get(self.bot.http_session, f"/history/recovered/{joined}")
                    history_deaths = await utils.get(self.bot.http_session, f"/history/deaths/{joined}")
                    await plot_csv(
                        path,
                        history_confirmed,
                        history_recovered,
                        history_deaths,
                        logarithmic=is_log)

            except Exception as e:
                path = utils.STATS_PATH

        confirmed = data["totalCases"]
        recovered = data["totalRecovered"]
        deaths = data["totalDeaths"]
        active = data["activeCases"]
        embed.set_author(
            name=f"Coronavirus COVID-19 {graph_type} graph - {data['country']}",
            icon_url=f"https://raw.githubusercontent.com/hjnilsson/country-flags/master/png250px/{data['iso2'].lower()}.png"
        )
        embed.add_field(
            name="<:confirmed:688686089548202004> Confirmed",
            value=f"{confirmed:,}"
        )
        embed.add_field(
            name="<:recov:688686059567185940> Recovered",
            value=f"{recovered:,} (**{utils.percentage(confirmed, recovered)}**)"
        )
        embed.add_field(
            name="<:_death:688686194917244928> Deaths",
            value=f"{deaths:,} (**{utils.percentage(confirmed, deaths)}**)"
        )

        embed.add_field(
            name="<:_calendar:692860616930623698> Today confirmed",
            value=f"+{data['newCases']:,} (**{utils.percentage(confirmed, data['newCases'])}**)"
        )
        embed.add_field(
            name="<:_calendar:692860616930623698> Today deaths",
            value=f"+{data['newDeaths']:,} (**{utils.percentage(confirmed, data['newDeaths'])}**)"
        )
        embed.add_field(
            name="<:bed_hospital:692857285499682878> Active",
            value=f"{active:,} (**{utils.percentage(confirmed, active)}**)"
        )
        embed.add_field(
            name="<:critical:752228850091556914> Serious critical",
            value=f"{data['seriousCritical']:,} (**{utils.percentage(confirmed, data['seriousCritical'])}**)"
        )
        if data["totalTests"]:
            percent_pop = ""
            if data["population"]:
                percent_pop = f"(**{utils.percentage(data['population'], data['totalTests'])}**)"

            embed.add_field(
                name="<:test:752252962532884520> Total test",
                value=f"{data['totalTests']:,} {percent_pop}"
            )

        if not os.path.exists(path):
            history_confirmed = await utils.get(self.bot.http_session, f"/history/confirmed/total")
            history_recovered = await utils.get(self.bot.http_session, f"/history/recovered/total")
            history_deaths = await utils.get(self.bot.http_session, f"/history/deaths/total")
            await plot_csv(
                path,
                history_confirmed,
                history_recovered,
                history_deaths,
                logarithmic=is_log)

        with open(path, "rb") as p:
            img = discord.File(p, filename=path)

        embed.set_footer(
            text="coronavirus.jessicoh.com/api/ | " + utils.last_update(data["lastUpdate"]),
            icon_url=ctx.me.avatar_url
        )
        embed.set_thumbnail(
            url=self.bot.thumb + str(time.time())
        )
        embed.set_image(url=f'attachment://{path}')
        await ctx.send(file=img, embed=embed)

    @commands.command(name="graph", aliases=["g"])
    @commands.cooldown(3, 30, commands.BucketType.user)
    async def graph(self, ctx, *args):
        #c!graph <proportion | daily | total> <confirmed | recovered | deaths> <top | country[] | world>

        # graph is going to be stored in files with names:
        # es_it_gb_us-proportion-deaths.png
        # most-proportion-confirmed.png

        types = ['proportion', 'daily', 'total']

        description = {
            'proportion': "This shows the **percentage of the population** who have confirmed/recovered/died.",
            'daily': "This shows the number of confirmed/recovered/deaths each day.",
            'total': "This shows the cumulative number of confirmed/recovered/deaths."
        }
        img = None

        ## START WITH INPUT VALIDATION
        if len(args) < 3:
            print("not enough args")
            embed = discord.Embed(
                description=f"Not enough args provided, I can't tell you which country/region/graph type if you won't tell me everything!\n\n__Examples:__\n `{ctx.prefix}g proportion deaths gb us it de fr`\n`{ctx.prefix}g proportion confirmed top`",
                timestamp=dt.datetime.utcnow(),
                color=utils.COLOR
            )
            embed.set_author(name=f"Coronavirus COVID-19 Graphs")
        else:
            # at least 2 arguments have been provided
            if args[0] not in types:
                # 1st argument is not an available graph type
                embed = discord.Embed(
                    description="Your first argument should tell me which kind of graph you would like to see. (proportion/daily_change/total)",
                    color=utils.COLOR,
                    timestamp=utils.discord_timestamp()
                )
            elif args[1] not in ['confirmed', 'recovered', 'deaths']:
                # 2nd argument is not an available measure
                embed = discord.Embed(
                    description="Your second argument should tell me which type of measure you would like to graph. (confirmed/recovered/deaths)",
                    color=utils.COLOR,
                    timestamp=utils.discord_timestamp()
                )
            else:
                # 1st and 2nd arguments are all good
                if args[0] == "total":
                    api_graph_type = "history"
                else:
                    api_graph_type = args[0]


                if args[2] == "top":
                    await ctx.send("Not yet implemented: cogs/Datacmds.py:332")
                elif args[2] == "world":
                    await ctx.send("Not yet implemented: cogs/Datacmds.py:334")
                else:
                    # presumably the user has entered one or more countries
                    stats = []
                    for c in args[2:]:
                        data = await utils.get(self.bot.http_session, f"/{api_graph_type}/{args[1]}/{c.lower()}")
                        dates = list(data[api_graph_type])
                        values = list(data[api_graph_type].values())
                        s = {
                            "dates": dates,
                            "values": values,
                            "iso2": data["iso2"],
                            "iso3": data["iso3"]
                        }
                        stats.append(s)

                    if args[0] == "proportion":
                        ylabel = f"Proportion of {args[1].capitalize()} (%)"
                    elif args[0] == "daily":
                        ylabel = f"Daily increase in {args[1].capitalize()}"
                    elif args[0] == "total":
                        ylabel = f"Total {args[1].capitalize()}"

                    embed = discord.Embed(
                        description=f"Here is a graph of the **{ylabel}** of COVID-19. " + description[args[0]],
                        timestamp=dt.datetime.utcnow(),
                        color=utils.COLOR
                    )   

                    path = ""
                    for c in stats:
                        embed.add_field(
                            name=c['iso3'],
                            value=str(c['values'][-1])
                        )

                        path += f"{c['iso2'].lower()}_"

            path += f"{args[0]}-{args[1]}-{utils.STATS_PATH}"

            if not os.path.exists(path):
                await plot_graph(path, stats, args[0], ylabel)

            with open(path, "rb") as p:
                img = discord.File(p, filename=path)

            embed.set_image(url=f'attachment://{path}')

            embed.set_author(name=f"Coronavirus COVID-19 Graphs - {args[0].capitalize()} of {args[1].capitalize()}",
                        url="https://www.who.int/home",
                        icon_url=self.bot.author_thumb)

        embed.set_footer(
            text="coronavirus.jessicoh.com/api/ | ",# + utils.last_update(data["lastUpdate"]),
            icon_url=ctx.me.avatar_url
        )
        embed.set_thumbnail(
            url=self.bot.thumb + str(time.time())
        )
        if img != None:
            await ctx.send(file=img, embed=embed)
        else:
            await ctx.send(embed=embed)

    @staticmethod
    def _get_idx(args, val):
        try:
            return args.index(val)
        except ValueError:
            return -1

    def _unpack_notif(self, args, val):
        try:
            idx = int(self._get_idx(args, val))
            interval_type = args[len(args)-1].lower()
            interval = int(args[idx+1])
            if idx != -1 and interval >= 1 and interval <= 24:
                country = " ".join(args[0:idx])
            else:
                interval = 1
                country = " ".join(args)
        except:
            interval = 1
            country = " ".join(args)

        return country.lower(), interval * self._convert_interval_type(interval_type), interval_type

    def _convert_interval_type(self, _type):
        try:
            return {
                "hours": 1,
                "days": 24,
                "weeks": 168,
                "hour": 1,
                "day": 24,
                "week": 168
            }[_type]
        except KeyError:
            return 1

    @commands.command(name="notification", aliases=["notif", "notifications"])
    @commands.has_permissions(administrator=True)
    @commands.cooldown(5, 30, commands.BucketType.user)
    async def notification(self, ctx, *state):
        if len(state):
            all_data = await utils.get(self.bot.http_session, "/all/")
            country, interval, interval_type = self._unpack_notif(state, "every")
            try:
                data = utils.get_country(all_data, country)
                try:
                    await self.bot.insert_notif(str(ctx.guild.id), str(ctx.channel.id), country, interval)

                except IntegrityError:
                    await self.bot.update_notif(str(ctx.guild.id), str(ctx.channel.id), country, interval)
                finally:
                    if country != "all":
                        embed = discord.Embed(
                            description=f"You will receive a notification in this channel on data update. `{ctx.prefix}notififcation disable` to disable the notifications"
                        )
                        embed.set_author(
                            name="Notifications successfully enabled",
                            icon_url=self.bot.author_thumb
                        )
                        embed.add_field(
                            name="Country",
                            value=f"**{data['country']}**"
                        )
                        embed.add_field(
                            name="Next update",
                            value=f"**{interval//self._convert_interval_type(interval_type)} {interval_type}**"
                        )
                    elif country == "all":
                        embed = discord.Embed(
                            description=f"You will receive a notification in this channel on data update. `{ctx.prefix}notififcation disable` to disable the notifications"
                        )
                        embed.set_author(
                            name="Notifications successfully enabled",
                            icon_url=self.bot.author_thumb
                        )
                        embed.add_field(
                            name="Country",
                            value=f"**World stats**"
                        )
                        embed.add_field(
                            name="Next update",
                            value=f"**{interval//self._convert_interval_type(interval_type)} {interval_type}**"
                        )
            except Exception as e:
                embed = discord.Embed(
                    title=f"{ctx.prefix}notification",
                    description=f"Make sure that you didn't have made any mistake, please retry\n`{ctx.prefix}notification <country | disable> [every NUMBER] [hours | days | weeks]`\n__Examples__ : `{ctx.prefix}notification usa every 3 hours` (send a message to the current channel every 3 hours about United States), `{ctx.prefix}notification united states every 1 day`, `{ctx.prefix}notification disable`"
                )
                print(e)

            if country == "disable":
                await self.bot.delete_notif(str(ctx.guild.id))
                embed = discord.Embed(
                    title="Notifications successfully disabled",
                    description="Notifications are now interrupted in this channel."
                )
        else:
            embed = discord.Embed(
                title=f"{ctx.prefix}notification",
                description=f"Make sure that you didn't have made any mistake, please retry\n`{ctx.prefix}notification <country | disable> [every NUMBER] [hours | days | weeks]`\n__Examples__ : `{ctx.prefix}notification usa every 3 hours` (send a message to the current channel every 3 hours about United States), `{ctx.prefix}notification united states every 1 day`, `{ctx.prefix}notification disable`"
            )

        embed.color = utils.COLOR
        embed.timestamp = utils.discord_timestamp()
        embed.set_thumbnail(url=self.bot.thumb + str(time.time()))
        embed.set_footer(
            text="coronavirus.jessicoh.com/api/ | " + utils.last_update(all_data[0]["lastUpdate"]),
            icon_url=ctx.me.avatar_url
        )
        await ctx.send(embed=embed)

    @commands.command(name="track", aliases=["tracker"])
    @commands.cooldown(3, 30, commands.BucketType.user)
    async def track(self, ctx, *country):
        if not len(country):
            embed = discord.Embed(
                description=f"No country provided. **`{ctx.prefix}track <COUNTRY>`** work like **`{ctx.prefix}country <COUNTRY>`** see `{ctx.prefix}help`",
                color=utils.COLOR,
                timestamp=utils.discord_timestamp()
            )
            embed.set_author(
                name=f"{ctx.prefix}track",
                icon_url=self.bot.author_thumb
            )
        elif ''.join(country) == "disable":
            embed = discord.Embed(
                description=f"If you want to reactivate the tracker : **`{ctx.prefix}track <COUNTRY>`**",
                color=utils.COLOR,
                timestamp=utils.discord_timestamp()
            )
            embed.set_author(
                name="Tracker has been disabled!",
                icon_url=self.bot.author_thumb
            )
            try:
                await self.bot.delete_tracker(str(ctx.author.id))
            except:
                pass
        else:

            all_data = await utils.get(self.bot.http_session, "/all/")
            country = ' '.join(country)
            data = utils.get_country(all_data, country)
            if data is not None:
                try:
                    await self.bot.insert_tracker(str(ctx.author.id), str(ctx.guild.id),country)
                except IntegrityError:
                    await self.bot.update_tracker(str(ctx.author.id), country)
                embed = discord.Embed(
                    description=f"{utils.mkheader()}You will receive stats about {data['country']} in DM",
                    color=utils.COLOR,
                    timestamp=utils.discord_timestamp()
                )
                embed.set_author(
                    name="Tracker has been set up!",
                    icon_url=f"https://raw.githubusercontent.com/hjnilsson/country-flags/master/png250px/{data['iso2'].lower()}.png"
                )
            else:
                embed = discord.Embed(
                    description="Wrong country selected.",
                    color=utils.COLOR,
                    timestamp=utils.discord_timestamp()
                )
                embed.set_author(
                    name=f"{ctx.prefix}track",
                    icon_url=self.bot.author_thumb
                )
        embed.set_thumbnail(url=self.bot.thumb + str(time.time()))
        embed.set_footer(
            text="coronavirus.jessicoh.com/api/",
            icon_url=ctx.me.avatar_url
        )
        await ctx.send(embed=embed)

    @commands.command(name="region", aliases=["r"])
    @commands.cooldown(5, 30, commands.BucketType.user)
    async def region(self, ctx, *params):
        if len(params):
            country, state = utils.parse_state_input(*params)
            try:
                if state == "all":
                    history_confirmed = await utils.get(self.bot.http_session, f"/history/confirmed/{country}/regions")
                    history_recovered = await utils.get(self.bot.http_session, f"/history/recovered/{country}/regions")
                    history_deaths = await utils.get(self.bot.http_session, f"/history/deaths/{country}/regions")
                    embeds = utils.region_format(history_confirmed, history_recovered, history_deaths)
                    for i, _embed in enumerate(embeds):
                        _embed.set_author(
                                name=f"All regions in {country}",
                                icon_url=self.bot.author_thumb
                            )
                        _embed.set_footer(
                            text=f"coronavirus.jessicoh.com/api/ | Page {i+1}",
                            icon_url=ctx.me.avatar_url)
                        _embed.set_thumbnail(url=self.bot.thumb + str(time.time()))
                        await ctx.send(embed=_embed)
                    return
                else:
                    path = state.lower().replace(" ", "_") + utils.STATS_PATH
                    history_confirmed = await utils.get(self.bot.http_session, f"/history/confirmed/{country}/{state}")
                    history_recovered = await utils.get(self.bot.http_session, f"/history/recovered/{country}/{state}")
                    history_deaths = await utils.get(self.bot.http_session, f"/history/deaths/{country}/{state}")
                    confirmed = list(history_confirmed["history"].values())[-1]
                    deaths = list(history_deaths["history"].values())[-1]

                    if country in ("us", "united states", "usa"):
                        is_us = True
                        recovered = 0
                        active = 0
                    else:
                        is_us = False
                        recovered = list(history_recovered["history"].values())[-1]
                        active = confirmed - (recovered + deaths)
                    if not os.path.exists(path):
                        await plot_csv(
                            path,
                            history_confirmed,
                            history_recovered,
                            history_deaths,
                            is_us=is_us)


                    embed = discord.Embed(
                        description=utils.mkheader(),
                        timestamp=dt.datetime.utcnow(),
                        color=utils.COLOR
                    )
                    embed.set_author(
                        name=f"Coronavirus COVID-19 - {state.capitalize()}",
                        icon_url=self.bot.author_thumb
                    )
                    embed.add_field(
                        name="<:confirmed:688686089548202004> Confirmed",
                        value=f"{confirmed:,}"
                    )
                    embed.add_field(
                        name="<:_death:688686194917244928> Deaths",
                        value=f"{deaths:,} (**{utils.percentage(confirmed, deaths)}**)"
                    )
                    if recovered:
                        embed.add_field(
                            name="<:recov:688686059567185940> Recovered",
                            value=f"{recovered:,} (**{utils.percentage(confirmed, recovered)}**)"
                        )
                        embed.add_field(
                            name="<:bed_hospital:692857285499682878> Active",
                            value=f"{active:,} (**{utils.percentage(confirmed, active)}**)"
                        )



            except:
                raise utils.RegionNotFound("Region not found, it might be possible that the region isn't yet available in the data.")
        else:
            return await ctx.send("No arguments provided.")

        with open(path, "rb") as p:
            img = discord.File(p, filename=path)

        embed.set_footer(
            text=f"coronavirus.jessicoh.com/api/ | {list(history_confirmed['history'].keys())[-1]}",
            icon_url=ctx.me.avatar_url
        )
        embed.set_thumbnail(
            url=self.bot.thumb + str(time.time())
        )
        embed.set_image(url=f'attachment://{path}')
        await ctx.send(file=img, embed=embed)

    @commands.command(name="continent")
    # @commands.cooldown(3, 30, commands.BucketType.user)
    async def continent(self, ctx, continent="", graph_type=""):
        embed = discord.Embed(
            title="API REWORK",
            description="This command is down for now, sorry (all the command left in c!help are still available)",
            color=utils.COLOR,
            timestamp=utils.discord_timestamp()
        )
        embed.set_thumbnail(url=self.bot.thumb + str(time.time()))
        embed.set_footer(
            text="coronavirus.jessicoh.com/api/",
            icon_url=ctx.me.avatar_url
        )
        await ctx.send(embed=embed)
    #     embed = discord.Embed(
    #         description="You can support me on <:kofi:693473314433138718>[Kofi](https://ko-fi.com/takitsu) and vote on [top.gg](https://top.gg/bot/682946560417333283/vote) for the bot. <:github:693519776022003742> [Source code](https://github.com/takitsu21/covid-19-tracker)",
    #         timestamp=dt.datetime.utcnow(),
    #         color=utils.COLOR
    #     )
    #     if len(continent) and continent in self.continent_code:
    #         continent = continent.lower()
    #         data = utils.filter_continent(self.bot._data, continent)

    #         if graph_type == "log":
    #             graph_type = "logarihmic"
    #             is_log = True
    #             path = continent + utils.STATS_LOG_PATH
    #         else:
    #             graph_type = "linear"
    #             path = continent + utils.STATS_PATH
    #             is_log = False
    #         if not os.path.exists(path):
    #             history_confirmed = await utils.get(self.bot.http_session, f"/history/confirmed/{joined}")
    #             history_recovered = await utils.get(self.bot.http_session, f"/history/recovered/{joined}")
    #             history_deaths = await utils.get(self.bot.http_session, f"/history/deaths/{joined}")
    #             await plot_csv(
    #                 path,
    #                 history_confirmed,
    #                 history_recovered,
    #                 history_deaths,
    #                 logarithmic=is_log)


    #         embed.set_author(
    #             name=f"Coronavirus COVID-19 {graph_type} stats | {continent.upper()}",
    #             icon_url=self.bot.author_thumb
    #         )
    #         embed.set_thumbnail(
    #             url=self.bot.thumb + str(time.time())
    #             )
    #         embed.add_field(
    #             name="<:confirmed:688686089548202004> Confirmed",
    #             value=f"{data['total']['confirmed']}",
    #             )
    #         embed.add_field(
    #                 name="<:recov:688686059567185940> Recovered",
    #                 value=f"{data['total']['recovered']} (**{utils.percentage(data['total']['confirmed'], data['total']['recovered'])}**)",
    #             )
    #         embed.add_field(
    #             name="<:_death:688686194917244928> Deaths",
    #             value=f"{data['total']['deaths']} (**{utils.percentage(data['total']['confirmed'], data['total']['deaths'])}**)",
    #         )

    #         embed.add_field(
    #             name="<:_calendar:692860616930623698> Today confirmed",
    #             value=f"+{data['today']['confirmed']} (**{utils.percentage(data['total']['confirmed'], data['today']['confirmed'])}**)"
    #         )
    #         embed.add_field(
    #             name="<:_calendar:692860616930623698> Today recovered",
    #             value=f"+{data['today']['recovered']} (**{utils.percentage(data['total']['confirmed'], data['today']['recovered'])}**)"
    #         )
    #         embed.add_field(
    #             name="<:_calendar:692860616930623698> Today deaths",
    #             value=f"+{data['today']['deaths']} (**{utils.percentage(data['total']['confirmed'], data['today']['deaths'])}**)"
    #         )
    #         embed.add_field(
    #                 name="<:bed_hospital:692857285499682878> Active",
    #                 value=f"{data['total']['active']} (**{utils.percentage(data['total']['confirmed'], data['total']['active'])}**)"
    #             )
    #         with open(path, "rb") as p:
    #             img = discord.File(p, filename=path)


    #     else:
    #         embed.set_author(
    #             name=f"Coronavirus COVID-19 available continent",
    #             icon_url=self.bot.author_thumb
    #         )
    #         text = '**' + ', '.join(self.continent_code).upper() + '**'
    #         embed.description = "\n\n" + text

    #     embed.set_footer(
    #         text=utils.last_update(utils.DATA_PATH),
    #         icon_url=ctx.me.avatar_url
    #     )
    #     try:
    #         embed.set_image(url=f'attachment://{path}')
    #         await ctx.send(embed=embed, file=img)
    #     except:
    #         embed.set_image(url=self.bot.thumb + str(time.time()))
    #         await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Datacmds(bot))
