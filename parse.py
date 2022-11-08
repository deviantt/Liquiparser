from bs4 import BeautifulSoup as bs
import re
import asyncio
from aiohttp import ClientSession
from datetime import datetime, timedelta

TIMEZONE_OFFSET = 3
URL_GROUPSTAGE_GAMES_1 = "https://liquipedia.net/dota2/The_International/2022/Group_Stage_Day_1-2"
URL_GROUPSTAGE_GAMES_2 = "https://liquipedia.net/dota2/The_International/2022/Group_Stage_Day_3-4"
URL_OVERVIEW = "https://liquipedia.net/dota2/The_International/2022"
URL_PLAYOFF = "https://liquipedia.net/dota2/The_International/2022/Main_Event"

events_dict = {
                'The International 2022':
                    ['https://liquipedia.net/dota2/The_International/2022',
                    ['https://liquipedia.net/dota2/The_International/2022/Group_Stage_Day_1-2', 
                    'https://liquipedia.net/dota2/The_International/2022/Group_Stage_Day_3-4'],
                    'https://liquipedia.net/dota2/The_International/2022/Main_Event']
}

session = {}

class DotaEvent:
    def __init__(self, event_name):
        self.__overview_url = events_dict[event_name][0]
        self.__groupstage_urls = events_dict[event_name][1]
        self.__playoff_url = events_dict[event_name][2]
        self.__event_name = None
        self.__participants = None
        self.__playoff_matches = None
        self.__groupstage_matches = None
        asyncio.run(self.__async_init())
        
    #public
    def get_event_name(self):
        return self.__event_name

    def get_participants(self):
        return self.__participants

    def get_playoff_matches(self):
        return self.__playoff_matches

    def get_groupstage_matches(self):
        return self.__groupstage_matches

    def get_filtered_matches(self, team_names):
        return self.__filter_matches(team_names)

    #private
    async def __async_init(self):
        session['session'] = ClientSession()
        async with session['session']:
            overview_task = asyncio.create_task(self.__parse_overview())
            groupstage_task = asyncio.create_task(self.__parse_groupstage_matches())
            playoff_task = asyncio.create_task(self.__parse_playoff_matches())
            await overview_task
            await groupstage_task
            await playoff_task

    def __filter_matches(self, team_names):
        group_list = 'Group Stage Matches:\n'
        playoff_list = 'Main Stage Matches:\n'
        for team in team_names:
            my_regex = r"(?<!\S)" + re.escape(team) + r"(?!\S)"
            for groupstage_matches in self.__groupstage_matches:
                for match in self.__groupstage_matches[groupstage_matches]:
                    if re.search(my_regex, match) and match not in group_list:
                        group_list += f'{match}\n'
            for match in self.__playoff_matches:
                if re.search(my_regex, match) and match not in group_list:
                    playoff_list += f'{match}\n'
        return group_list, playoff_list

    async def __parse_overview(self):
        async with session['session'].get(self.__overview_url) as resp:
            r = await resp.text()
        soup = bs(r, "html.parser")
        out_list = list()
        participants = soup.find_all('div', class_='teamcard toggle-area toggle-area-1')
        for team in participants:
            out_list.append(team.a['title'])
        self.__participants = out_list
        event_name = soup.find('h1', class_='firstHeading')
        self.__event_name = event_name.text
    
    async def __parse_playoff_matches(self):
        async with session['session'].get(self.__playoff_url) as resp:
            r = await resp.text()
        soup = bs(r, "html.parser")
        matches_raw = soup.find_all('tr', class_='Match')
        out_list = list()
        for i in range(len(matches_raw)):
            temp_str: str
            if matches_raw[i].find('span', class_='team-template-team2-short') is not None:
                temp_str = str(matches_raw[i].find('span', class_='team-template-team2-short').a['title'] + " vs ")
            else:
                temp_str = "TBD vs "
            if matches_raw[i].find('span', class_='team-template-team-short') is not None:
                temp_str += str(matches_raw[i].find('span', class_='team-template-team-short').a['title'] + ".")
            else:
                temp_str += "TBD. "
            temp_str += str("Round: " + matches_raw[i].find('td', class_='Round').text + ". ")
            temp_str += str("Start time: " + self.__timezoneHandler(matches_raw[i].find('span', class_='timer-object timer-object-datetime-only').text, 5))
            out_list.append(temp_str)
        self.__playoff_matches = out_list

    async def __parse_groupstage_matches(self):
        group_matches = dict()
        tasks = []
        for i in self.__groupstage_urls:
            tasks.append(asyncio.create_task(self.__parse_groupstage_day(i)))
        results = await asyncio.gather(*tasks)
        for result in results:
            group_matches = group_matches | result
        self.__groupstage_matches = group_matches

    async def __parse_groupstage_day(self, url):
        async with session['session'].get(url) as resp:
            r = await resp.text()
        soup = bs(r, "html.parser")
        game_days = list()
        days_tables = soup.find_all('div', class_='brkts-matchlist brkts-matchlist-collapsible')
        for i in range(len(days_tables)):
            game_days.append(days_tables[i].find('div', class_='brkts-matchlist-title').text)
        out_dict = dict()
        for i in range(len(game_days)):
            out_dict[game_days[i]] = self.__parse_groupstage_gamesperday(days_tables[i])
        return out_dict

    def __parse_groupstage_gamesperday(self, days_tables):
        team_names = days_tables.find_all('span', class_='name')
        start_times = days_tables.find_all('span', class_='timer-object')
        out_list = list()
        for i in range(len(team_names)):
            if team_names[i].a is not None:
                temp_str: str
                if i % 2 == 0:
                    temp_str = team_names[i].a['title'] + ' vs '
                else:
                    temp_str += f"{team_names[i].a['title']} | Start time: {self.__timezoneHandler(start_times[i//4].text, -3)}"
                    out_list.append(temp_str)
        return out_list

    def __timezoneHandler(self, start_time, timezone_offset):
        new_time = int(re.search('[0-9]{2}:', start_time).group(0)[:-1]) + timezone_offset
        time_index = start_time.find(re.search('[0-9]{2}:', start_time).group(0))
        if new_time < 10:
            new_time = "0" + str(new_time)
        else:
            new_time = str(new_time)
        start_time = (start_time[:time_index] + new_time + start_time[time_index + 2:])[:-4]
        date_time = datetime.strptime(start_time, '%B %d, %Y - %H:%M')
        if date_time < datetime.now():
            start_time = start_time + ' \U00002714'
        else:
            start_time = start_time + ' \U0000274C'
        return start_time
    

def print_dict(dictionary): #console app testing
    for key in dictionary:
        print(key + ':')
        for i in range(len(dictionary[key])):
            print(str(i + 1) + ". " + dictionary[key][i])

def print_list(list): #console app testing
    for i in range(len(list)):
        print(f"{i+1}. {list[i]}")

    
if __name__=="__main__":
    pass