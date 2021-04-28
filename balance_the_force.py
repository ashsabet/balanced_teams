import asyncio
import discord
from dotenv import load_dotenv
import logging
import os
from pathlib import Path
import json
import argparse
from balance.team_balancer import get_player_members, get_player_names_rank, create_balance, create_bros_balance
from balance.application import Application
from balance.message_parser import MessageParser

# https://github.com/Rapptz/discord.py
# https://discordpy.readthedocs.io/en/latest/index.html

#TODO Make use of discord.ext.commmands: https://discordpy.readthedocs.io/en/latest/ext/commands/commands.html 
#TODO Add "bros" mode so that Balazs and Greg can play on the same team while making the teams as fair as possible
#TODO Move rankings to a Google Sheet and allow users to dynamically upload or apply their own rankings
#TODO When asking the bot to create teams, tell it who to include or who to exclude

load_dotenv()
# process parser
parser = argparse.ArgumentParser()
parser.add_argument("--botkey", help="The discord bot key")
parser.add_argument("--rankings", help="The directory that holds rankings")
parser.add_argument("--verbose", action='store_true', help="Shows logging from Discord")
args = parser.parse_args()

# Show debug messages
logging.basicConfig(encoding='utf-8', level=logging.DEBUG)
if not args.verbose:
    logging.getLogger("asyncio").setLevel(logging.CRITICAL + 1)
    logging.getLogger("discord").setLevel(logging.CRITICAL + 1)


rankings_directory = ""
rankings = {} #example rankings file would be {"Khellendros": 3000, "ArrrrMatey": 2000, "Ashkon": 500}
botkey = ""
cwd = Path(__file__).parent # can't trust Path.cwd() if we are calling from another directory

if args.botkey:
    botkey = args.botkey
else:
    botkey = os.environ.get('BALANCE_THE_FORCE_API_KEY')

if not botkey:
    exit(f"Discord Api Key Not Set\nPlease check {cwd / '.env'}")

if args.rankings:
    rankings_directory = Path(args.rankings)
else:
    env = os.environ.get('BALANCE_THE_FORCE_RANKINGS_DIRECTORY')
    if env:
        rankings_directory = Path(env)

if not rankings_directory:
    rankings_directory = cwd

rankings_file_path = rankings_directory / "rankings.json"

logging.info(f"Rankings file set to: '{rankings_file_path}'")
if rankings_file_path.exists():
    with open(rankings_file_path) as json_file:
        rankings = json.load(json_file)
else:
    exit(f"No such ranking file '{rankings_file_path}'")

intents = discord.Intents.all()
client = discord.Client(intents=intents)
messageParser = MessageParser()
application = Application(rankings)

def list_known_players():
    return rankings

def formated_teams(team_blue, players):
    team_orange = []
    for player in players:
        if player not in team_blue[0]:
            team_orange.append(player)

    string_to_return = "🟦BLUE: " + str(team_blue[0]) + "\n"
    string_to_return += "🟧ORANGE: " + str(team_orange)

    return string_to_return

def get_channel(channel_name, channels):
    return discord.utils.get(channels, name=channel_name)


@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('!list known players'):
        # neuter this with a return so that we don't accidentally expose player rankings.
        return

        known_players = list_known_players()
        for player in known_players.items():
            await message.channel.send(player)
    
    if message.content.startswith('!balance'):
        balanced_teams = create_balance(message.channel.members, rankings, 3)
        option_counter = 1
        for team in balanced_teams:
            response_message = "OPTION " + str(option_counter) + "\n" + formated_teams(team, get_player_names_rank(message.channel.members, rankings)) + "\n"
            option_counter += 1
            await message.channel.send(response_message)
        return

    if message.content.startswith('!v'):
        balanced_teams = create_balance(message.channel.members, rankings, 3)
        option_counter = 1
        for team in balanced_teams:
            response_message = "OPTION " + str(option_counter) + "\n" + formated_teams(team, get_player_names_rank(message.channel.members, rankings)) + "\n"
            option_counter += 1
            await message.channel.send(response_message)

            def check(reaction, user):
                return user == message.author and str(reaction.emoji) == '👍'

            try:
                reaction, user = await client.wait_for('reaction_add', timeout=10.0, check=check)
            except asyncio.TimeoutError:
                await message.channel.send('👎')
            else:
                await message.channel.send('Moving players.')
                for player in get_player_members(message.channel.members, rankings):
                    if player.name in team[0]:
                        await player.move_to(get_channel('Blue Team', message.channel.guild.voice_channels))
                    else:
                        await player.move_to(get_channel('Orange Team', message.channel.guild.voice_channels))
                break
        return


    if message.content.startswith('!list members'):
        members = message.channel.members
        
        for member in members:
            await message.channel.send(member.name + ' ' + member.raw_status)
        return

    if message.content.startswith('!debug'):
        await message.channel.send('Get out of my head!')
        return

    if message.content.startswith('!'):
        command = messageParser.parse(message.content)
        if command.command == '!players':
            player_names = application.get_players(command, message.channel.members)
            await message.channel.send(', '.join(player_names))
        if command.command == '!balance':
            members = message.channel.members
            if command.skip != None:
                members = filter(lambda member: member.name in command.skip, members)

            balanced_teams = create_balance(members, rankings, 3)
            option_counter = 1
            for team in balanced_teams:
                response_message = "OPTION " + str(option_counter) + "\n" + formated_teams(team, get_player_names_rank(members, rankings)) + "\n"
                option_counter += 1
                await message.channel.send(response_message)

                if command.verify:
                    def check_reaction(reaction, user):
                        return user == message.author and str(reaction.emoji) == '👍'

                    try:
                        reaction, user = await client.wait_for('reaction_add', timeout=10.0, check=check_reaction)
                    except asyncio.TimeoutError:
                        await message.channel.send('👎')
                    else:
                        await message.channel.send('Moving players.')
                        for player in get_player_members(members, rankings):
                            if player.name in team[0]:
                                await player.move_to(get_channel('Blue Team', message.channel.guild.voice_channels))
                            else:
                                await player.move_to(get_channel('Orange Team', message.channel.guild.voice_channels))
                        break
        return

client.run(botkey)
