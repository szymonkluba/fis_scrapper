import configparser

import requests
from lxml import html

from file import File
from interface import Interface
from jump import Jump
from participant import Participant
from race import Race

config = None
lines = []


def check_if_error(tree):
    field = tree.xpath('//*[@class="error"]/text()')
    if field:
        if 'No competition' in field[0]:
            return True
    return False


def check_if_empty(tree):
    field = tree.xpath('//*[@id="events-info-results"]/div/div/div/div/div/text()')
    if field:
        if 'No results found' in field[0]:
            return True
    return False


def check_woman(tree):
    if 'Women' in tree.xpath('//*[@class="event-header__kind"]/text()')[0]:
        return True
    return False


def check_children(tree):
    field = tree.xpath('//*[@class="event-header__subtitle"]/text()')
    if 'Children' in field[0]:
        return True
    return False


def check_team(tree):
    if "Team" in tree.xpath('//*[@class="event-header__kind"]/text()')[0]:
        return True
    return False


def disqualified_exists(tree):
    field_1 = tree.xpath('//*[@id="ajx_results"]/section/div/div/div/div[2]/div[4]/div/a/div/div/div[2]')
    field_2 = tree.xpath('//*[@id="ajx_results"]/section/div/div/div/div[2]/div[3]/div/div/div')
    if field_1 or field_2:
        return True
    return False


def value_from_empty_node(node):
    try:
        if node[0].text:
            return node[0].text
        return ""
    except AttributeError:
        return ""


def float_or_empty(value):
    if value == "":
        return None
    try:
        return float(value.replace(',', '.'))
    except ValueError:
        if config.getboolean("Ignores", "ignore_value_errors"):
            return value
        else:
            return float(input(f"Problem with value: {value}, you may input correct one: "))


def int_or_empty(value):
    if value == "":
        return None
    try:
        return int(value)
    except ValueError:
        if config.getboolean("Ignores", "ignore_value_errors"):
            return value
        else:
            return int(input(f"Problem with value: {value}, you may input correct one: "))


def generate_dictionary_of_columns(columns, tree, path_pref, path_affx, ):
    counter = 1
    while tree.xpath(f'{path_pref}{counter}{path_affx}'):
        key = tree.xpath(f'{path_pref}{counter}{path_affx}')[0]
        key = key.strip().lower().replace(".", "").replace(" ", "_")
        if key == "athlete":
            key = "name"
        columns[key] = counter
        counter += 1
    return columns


def generate_jumpers(columns: dict, tree, race_list: list, path_pref, path_mid, path_affx, disqualified=False):
    row = 0
    while True:
        row += 1
        jumper = None
        for k in columns:
            if k == 'nation':
                value = tree.xpath(path_pref
                                   + str(row)
                                   + path_mid
                                   + str(columns[k])
                                   + path_affx.replace("/.", "/div/span[2]/."))
            else:
                value = tree.xpath(path_pref
                                   + str(row)
                                   + path_mid
                                   + str(columns[k])
                                   + path_affx)
            if not value:
                break
            if k == "rank":
                jumper = Participant(int_or_empty(value_from_empty_node(value)))
            elif "jump" in k:
                jump = Jump(float_or_empty(value_from_empty_node(value)))
            elif "round" in k:
                jump.set_points(float_or_empty(value_from_empty_node(value)))
                jumper.add_jump(jump)
            else:
                value = value_from_empty_node(value).strip()
                if value.isdigit():
                    value = int_or_empty(value)
                elif value.isnumeric():
                    value = float_or_empty(value)
                jumper.__setattr__(k, value)
        if jumper and jumper.name:
            race_list.append(jumper)
        else:
            break
    return race_list


def scrap_races(lookup_range, races: list):
    for f_id in lookup_range:
        print(f'Current FIS ID: {f_id}')
        columns = dict()
        path = f'https://www.fis-ski.com/DB/general/results.html?sectorcode=JP&raceid={f_id}'
        page = requests.get(path)
        tree = html.fromstring(page.content)
        cancelled = tree.xpath('//*[@class="event-status event-status_cancelled"]/.')
        if check_if_error(tree):
            print('No data for given FIS ID')
        elif config.getboolean("Ignores", "ignore_cancelled") and cancelled:
            print("Race cancelled - passing")
        elif check_if_empty(tree):
            print('No data for given FIS ID')
        else:
            if config.getboolean("Ignores", "ignore_women") and check_woman(tree):
                print('Woman competition - passing')
            elif config.getboolean("Ignores", "ignore_children") and check_children(tree):
                print('Children competition - passing')
            elif config.getboolean("Ignores", "ignore_team") and check_team(tree):
                print('Team competition - passing')
            else:
                time_starts = tree.xpath('//*[@class="time__value"]/text()')
                if time_starts:
                    time_starts = time_starts[0]
                else:
                    time_starts = "00:00"
                race = Race(
                    fis_id=f_id,
                    place=tree.xpath('//*[@class="event-header__name heading_off-sm-style"]/h1/text()')[0],
                    subtitle=tree.xpath('//*[@class="event-header__subtitle"]/text()')[0].strip(),
                    kind=tree.xpath('//*[@class="event-header__kind"]/text()')[0],
                    date_starts=tree.xpath('//*[@class="date__full"]/text()')[0],
                    time_starts=time_starts,
                )
                if cancelled:
                    race.set_status_to_cancelled()
                    races.append(race)
                else:
                    rank = tree.xpath(
                        '//*[@id="ajx_results"]/section/div/div/div/div[2]/div[1]/div/div/div/div/div[1]/text()')
                    if rank:
                        path_pref = '//*[@id="ajx_results"]/section/div/div/div/div[2]/div[1]/div/div/div/div/div['
                        path_affx = ']/text()'
                        columns = generate_dictionary_of_columns(columns, tree, path_pref, path_affx)
                    else:
                        path_pref = '//*[@id="ajx_results"]/section/div/div/div/div/div[1]/div/div/div/div/div['
                        path_affx = ']/text()'
                        columns = generate_dictionary_of_columns(columns, tree, path_pref, path_affx)
                    path_pref = '//*[@id="events-info-results"]/div/a['
                    path_mid = ']/div/div/div['
                    path_affx = ']/.'
                    race.participants = generate_jumpers(columns,
                                                         tree,
                                                         race.participants,
                                                         path_pref,
                                                         path_mid,
                                                         path_affx)
                    if disqualified_exists(tree):
                        path_pref = '//*[@id="ajx_results"]/section/div/div/div/div[2]/div[4]/div/a['
                        path_mid = ']/div/div/div['
                        path_affx = ']/.'
                        race.disqualified = generate_jumpers(columns,
                                                             tree,
                                                             race.disqualified,
                                                             path_pref,
                                                             path_mid,
                                                             path_affx,
                                                             disqualified_exists(tree))
                        lines.append('disqualified\n')
                    races.append(race)
    return races


def open_config(config: configparser.ConfigParser, **kwargs):
    try:
        with open("config.ini", "x") as config_file:
            config["Ignores"] = {}
            if "ignore_women" in kwargs:
                config["Ignores"]["ignore_women"] = "yes" if kwargs["ignore_women"] else "no"
            if "ignore_children" in kwargs:
                config["Ignores"]["ignore_children"] = "yes" if kwargs["ignore_children"] else "no"
            if "ignore_cancelled" in kwargs:
                config["Ignores"]["ignore_cancelled"] = "yes" if kwargs["ignore_cancelled"] else "no"
            if "ignore_team" in kwargs:
                config["Ignores"]["ignore_team"] = "yes" if kwargs["ignore_team"] else "no"
            if "ignore_value_errors" in kwargs:
                config["Ignores"]["ignore_value_errors"] = "yes" if kwargs["ignore_value_errors"] else "no"
            config.write(config_file)
    finally:
        config.read("config.ini")
        return config


def settings(config: configparser.ConfigParser):
    while True:
        for i, v in enumerate(config["Ignores"].items()):
            print(f"{i + 1}. {v[0].capitalize().replace('_', ' ')}: {v[1]}")
        operation = input("Enter setting number to switch, s - save and exit,  x - exit: ")
        if operation.isnumeric():
            options = {}
            for i, k in enumerate(config["Ignores"].keys()):
                options[str(i + 1)] = k
            for num in operation:
                config["Ignores"][options[num]] = "no" if config["Ignores"].getboolean(options[num]) else "yes"
        elif operation == "s":
            with open("config.ini", "w") as config_file:
                config.write(config_file)
            break
        elif operation == "x":
            break
        else:
            print("Unknown operation")
            continue


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config = open_config(
        config,
        ignore_women=True,
        ignore_cancelled=True,
        ignore_children=True,
        ignore_team=True,
        ignore_value_errors=False,
    )
    while True:
        races = []
        files = []
        mode = input("Choose scraping for:\n "
                     "1 - single race, "
                     "2 - selected races, "
                     "3 - range of races, "
                     "s - settings, "
                     "q - quit: ")
        if mode not in "123qs":
            print("Unknown mode")
            continue
        elif mode == "q":
            break
        elif mode == "s":
            settings(config)
        else:
            lookup_range = input(Interface.mode_prompts(mode))
            if "-" in lookup_range:
                lookup_range = list(map(int, lookup_range.split("-")))
                lookup_range = range(lookup_range[0], lookup_range[1] + 1)
                races = scrap_races(lookup_range, races)
            else:
                lookup_range = lookup_range.split()
                races = scrap_races(lookup_range, races)
            for race in races:
                file = File(race)
                files.append(file)
            while True:
                print("What next?")
                next_operation = input("l - list races, s - save to file, x - exit: ")
                if next_operation == "l":
                    while True:
                        print("\nList of races:")
                        for i, race in enumerate(races):
                            print(f"{i + 1}. {race.fis_id} {race.place} {race.date_starts.strftime('%d.%m.%Y')}")
                        next_operation = input("Enter race number for details, b - go back: ")
                        if next_operation.isnumeric():
                            next_operation = int(next_operation) - 1
                            try:
                                Interface.race_details(races[next_operation])
                            except IndexError:
                                print("No such race")
                                continue
                        elif next_operation == "b":
                            break
                        else:
                            print("Unknown command")
                elif next_operation == "s":
                    if files:
                        while files:
                            file = files.pop()
                            file.generate_lines()
                            file.save()
                    else:
                        print("Nothing to save!")
                        break
                elif next_operation == "x":
                    if races and files:
                        next_operation = input("Are you sure? Data not saved to file will be gone. y/n: ")
                        if next_operation == 'y':
                            break
                        else:
                            continue
                    else:
                        break
                else:
                    print("Unknown command")
                    continue
