from lxml import html
import requests
import configparser

from constants import ABR_TOURNAMENTS
from jump import Jump
from participant import Participant
from race import Race

config = None


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


def save_to_file(filename, lines, no=0):
    try:
        with open(filename, 'x') as file:
            file.writelines(lines)
            print(f"Zapisano w: {filename}")
    except FileExistsError:
        no += 1
        file_name = f"CSV/{race.date_starts.strftime('%Y-%m-%d')}_" \
                    f"{ABR_TOURNAMENTS[race.subtitle]}_" \
                    f"{race.place.replace(' ', '_')} ({no}).csv"
        save_to_file(file_name, lines, no)


def generate_dictionary_of_columns(columns, tree, path_pref, path_affx, ):
    counter = 1
    while tree.xpath(f'{path_pref}{counter}{path_affx}'):
        columns[tree.xpath(f'{path_pref}{counter}{path_affx}')[0]] = counter
        counter += 1
    return columns


def generate_jumpers(columns: dict, tree, race_list: list, path_pref, path_mid, path_affx, disqualified=False):
    row = 0
    while True:
        row += 1
        jumper = None
        for k, v in columns.items():
            if k == 'Nation' and disqualified:
                full_path = ''.join([
                    '//*[@id="ajx_results"]/section/div/div/div/div[2]/div[4]/div/a[',
                    str(row),
                    ']/div/div/div[',
                    str(v),
                    ']/div/span[2]/.'
                ])
                value = tree.xpath(full_path)
            elif k == 'Nation':
                full_path = ''.join([
                    '//*[@id="events-info-results"]/div/a[',
                    str(row),
                    ']/div/div/div[',
                    str(v),
                    ']/div/span[2]/.'])
                value = tree.xpath(full_path)
            else:
                value = tree.xpath(path_pref + str(row) + path_mid + str(columns[k]) + path_affx)
            if not value:
                break
            if k == "Rank":
                jumper = Participant(int_or_empty(value_from_empty_node(value)))
            elif "Jump" in k:
                jump = Jump(float_or_empty(value_from_empty_node(value)))
            elif "Round" in k:
                jump.set_points(float_or_empty(value_from_empty_node(value)))
                jumper.add_jump(jump)
            elif k == "Bib":
                jumper.set_bib(int_or_empty(value_from_empty_node(value)))
            elif k == "FIS code":
                jumper.set_fis_code(int_or_empty(value_from_empty_node(value)))
            elif k == "Athlete" or k == "Name":
                value = value_from_empty_node(value).replace("\n", "").strip()
                if value != "":
                    jumper.set_name(value)
                else:
                    break
            elif k == "Year":
                jumper.set_year_born(int_or_empty(value_from_empty_node(value)))
            elif k == "Nation":
                jumper.set_nation(value_from_empty_node(value))
            elif k == "Tot. Points":
                jumper.set_total_points(float_or_empty(value_from_empty_node(value)))
            elif k == "Diff. Points":
                jumper.set_points_diff(float_or_empty(value_from_empty_node(value)))
        if jumper and jumper.name:
            race_list.append(jumper)
        else:
            break
    return race_list


def generate_lines(race: Race):
    lines = []
    if race.participants:
        for p in race.participants:
            line = generate_single_line(p)
            lines.append(line)
    if race.disqualified:
        lines.append("##### DISQUALIFIED #####\n")
        for d in race.disqualified:
            line = generate_single_line(d)
            lines.append(line)
    return lines


def generate_single_line(participant: Participant):
    line = ""
    line += f"{participant.rank if participant.rank else ''};"
    line += f"{participant.bib if participant.bib else ''};"
    line += f"{participant.fis_code if participant.fis_code else ''};"
    line += f"{participant.name if participant.name else ''};"
    line += f"{participant.year_born if participant.year_born else ''};"
    line += f"{participant.nation if participant.nation else ''};"
    for j in participant.jumps:
        line += f"{j.distance if j.distance else ''};{j.points if j.points else ''};"
    line += f"{participant.total_points if participant.total_points else ''};"
    line += f"{participant.diff_points if participant.diff_points else ''}\n"
    return line


def mode_prompts(mode):
    return {
        "1": "Enter FIS ID of race: ",
        "2": "Enter FIS IDs of races, separated by spaces (ex. 1111 2222 3333): ",
        "3": "Enter range of FIS IDs, separated by \"-\" (ex. 1111-2222: "
    }.get(mode)


def scrap_races(lookup_range, races: list):
    for i in lookup_range:
        print(f'Current FIS ID: {i}')
        lines = []
        columns = dict()
        raceid = str(i)
        path = 'https://www.fis-ski.com/DB/general/results.html?sectorcode=JP&raceid=' + raceid
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
                    fis_id=i,
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


def race_details(race: Race):
    header = f"|{'Rank': ^4}|{'Bib': ^4}|{'FIS code': ^8}|{'Athlete': ^30}|{'Total points': ^12}|{'Points diff': ^12}|"
    print("RACE DETAILS")
    print("_" * len(header))
    print(f"Place: {race.place}")
    print(f"Subtitle: {race.subtitle}")
    print(f"Kind: {race.kind}")
    print(f"Date: {race.date_starts.strftime('%d.%m.%Y')}")
    print(f"Time: {race.time_starts.strftime('%H:%M')} CET")
    print("_" * len(header))
    if race.is_cancelled:
        print("##### CANCELLED #####")
    if race.participants:
        print("=" * len(header))
        print("Participants:")
        print("-" * len(header))
        print(header)
        print("-" * len(header))
        for p in race.participants:
            print(jumpers_table(p))
        print("-" * len(header))
    if race.disqualified:
        print("=" * len(header))
        print("Disqualified:")
        print("-" * len(header))
        print(header)
        print("-" * len(header))
        for p in race.disqualified:
            print(jumpers_table(p))
        print("-" * len(header))


def jumpers_table(p: Participant):
    return (f"|{p.rank if p.rank else '-': ^4}|"
            f"{p.bib if p.bib else '-': ^4}|"
            f"{p.fis_code if p.fis_code else '-': ^8}|"
            f"{p.name if p.name else '-': ^30}|"
            f"{p.total_points if p.total_points else '-': ^12}|"
            f"{p.diff_points if p.diff_points else '-': ^12}|")


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
            lookup_range = input(mode_prompts(mode))
            if "-" in lookup_range:
                lookup_range = list(map(int, lookup_range.split("-")))
                lookup_range = range(lookup_range[0], lookup_range[1] + 1)
                races = scrap_races(lookup_range, races)
            else:
                lookup_range = lookup_range.split()
                races = scrap_races(lookup_range, races)
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
                                race_details(races[next_operation])
                            except IndexError:
                                print("No such race")
                                continue
                        elif next_operation == "b":
                            break
                        else:
                            print("Unknown command")
                elif next_operation == "s":
                    for race in races:
                        if race.is_cancelled:
                            file_name = f"CSV/CANCELLED_{race.date_starts.strftime('%Y-%m-%d')}_" \
                                        f"{ABR_TOURNAMENTS[race.subtitle]}_" \
                                        f"{race.place.replace(' ', '_')}.csv"
                            lines = ["##### CANCELLED #####"]
                        else:
                            file_name = f"CSV/{race.date_starts.strftime('%Y-%m-%d')}_" \
                                        f"{ABR_TOURNAMENTS[race.subtitle]}_" \
                                        f"{race.place.replace(' ', '_')}.csv"
                            lines = generate_lines(race)
                        save_to_file(file_name, lines)
                elif next_operation == "x":
                    next_operation = input("Are you sure? Data not saved to file will be gone. y/n: ")
                    if next_operation == 'y':
                        break
                    else:
                        continue
                else:
                    print("Unknown command")
                    continue
