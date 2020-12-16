from lxml import html
import requests
import configparser

from constants import ABR_TOURNAMENTS
from jump import Jump
from participant import Participant
from race import Race

ignore_women = True
ignore_children = True
ignore_team = True
ignore_cancelled = True
ignore_value_error = False

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


def check_if_full(tree):
    field = tree.xpath('//*[@id="events-info-results"]/div/a[1]/div/div/div[3]/text()')[0]
    if field.isnumeric():
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
        if node.text:
            return node.text
        return ""
    except AttributeError:
        return ""


def float_or_empty(value):
    if value == "":
        return None
    try:
        return float(value.replace(',', '.'))
    except ValueError:
        return float(input(f"Problem with value: {value}, you may input correct one: "))


def int_or_empty(value):
    if value == "":
        return None
    try:
        return int(value)
    except ValueError:
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


def fill_columns(columns, tree, path_pref, path_affx, disqualified):
    for k, v in columns.items():
        if k == 'Nation' and disqualified:
            full_path = ''.join([
                '//*[@id="ajx_results"]/section/div/div/div/div[2]/div[4]/div/a/div/div/div[',
                str(v),
                ']/div/span[2]/.'
            ])
            temp_list = tree.xpath(full_path)
        elif k == 'Nation':
            full_path = ''.join([
                '//*[@id="events-info-results"]/div/a/div/div/div[',
                str(v),
                ']/div/span[2]/.'])
            temp_list = tree.xpath(full_path)
        else:
            temp_list = tree.xpath(path_pref + str(columns[k]) + path_affx)
        for i in range(len(temp_list)):
            if k == "Athlete" or k == "Nation":
                temp_list[i] = value_from_empty_node(temp_list[i]).replace('\n', '').strip()
            elif k == "Rank" or k == "Bib" or k == "FIS code" or k == "Year":
                temp_list[i] = int_or_empty(value_from_empty_node(temp_list[i]))
            else:
                temp_list[i] = float_or_empty(value_from_empty_node(temp_list[i]))
        columns[k] = temp_list
    return columns


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


def generate_participants(dictionary: dict, race: Race, disqualified=False):
    for i in range(len(dictionary["Athlete"])):
        participant = None
        for k, v in dictionary.items():
            if k == "Rank":
                participant = Participant(v[i])
            elif "Jump" in k:
                jump = Jump(v[i])
            elif "Round" in k:
                jump.set_points(v[i])
                participant.add_jump(jump)
            elif k == "Bib":
                participant.set_bib(v[i])
            elif k == "FIS code":
                participant.set_fis_code(v[i])
            elif k == "Athlete":
                participant.set_name(v[i])
            elif k == "Year":
                participant.set_year_born(v[i])
            elif k == "Nation":
                participant.set_nation(v[i])
            elif k == "Tot. Points":
                participant.set_total_points(v[i])
            elif k == "Diff. Points":
                participant.set_points_diff(v[i])
        if disqualified:
            race.add_disqualified(participant)
        else:
            race.add_participant(participant)


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

        if check_if_empty(tree) or check_if_error(tree):
            print('Nothing to get:(')
        else:
            if check_woman(tree):
                print('Woman competition - passing')
            elif check_children(tree):
                print('Children competition - passing')
            elif check_team(tree):
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
                rank = tree.xpath(
                    '//*[@id="ajx_results"]/section/div/div/div/div[2]/div[1]/div/div/div/div/div[1]/text()')
                if rank:
                    path_pref = '//*[@id="ajx_results"]/section/div/div/div/div[2]/div[1]/div/div/div/div/div['
                    path_affx = ']/text()'
                    columns = generate_dictionary_of_columns(columns, tree, path_pref, path_affx)
                    disqualified = columns.copy()
                    path_pref = '//*[@id="events-info-results"]/div/a/div/div/div['
                    path_affx = ']/.'
                    columns = fill_columns(columns, tree, path_pref, path_affx, False)
                else:
                    path_pref = '//*[@id="ajx_results"]/section/div/div/div/div/div[1]/div/div/div/div/div['
                    path_affx = ']/text()'
                    columns = generate_dictionary_of_columns(columns, tree, path_pref, path_affx)
                    disqualified = columns.copy()
                    path_pref = '//*[@id="events-info-results"]/div/a/div/div/div['
                    path_affx = ']/.'
                    columns = fill_columns(columns, tree, path_pref, path_affx, False)
                generate_participants(columns, race)
                if disqualified_exists(tree):
                    path_pref = '//*[@id="ajx_results"]/section/div/div/div/div[2]/div[4]/div/a/div/div/div['
                    path_affx = ']/.'
                    fill_columns(disqualified, tree, path_pref, path_affx, disqualified_exists(tree))
                    lines.append('disqualified\n')
                    generate_participants(disqualified, race, disqualified=True)
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


def create_or_open_config(config: configparser.ConfigParser, **kwargs):
    try:
        with open("config.ini", "w") as config_file:
            config.add_section("Ignores")
            if "ignore_women" in kwargs:
                config.set("Ignores", "ignore_women", kwargs["ignore_women"])
            if "ignore_children" in kwargs:
                config.set("Ignores", "ignore_children", kwargs["ignore_children"])
            if "ignore_cancelled" in kwargs:
                config.set("Ignores", "ignore_cancelled", kwargs["ignore_cancelled"])
            if "ignore_team" in kwargs:
                config.set("Ignores", "ignore_team", kwargs["ignore_team"])
            if "ignore_value_errors" in kwargs:
                config.set("Ignores", "ignore_value_errors", kwargs["ignore_value_errors"])
            config.write(config_file)
            config_file.close()
    finally:
        config.read("config.ini")
        return config


if __name__ == "__main__":
    config = configparser.ConfigParser()
    config = create_or_open_config(
        config,
        ignore_women=True,
        ignore_cancelled=True,
        ignore_children=True,
        ignore_team=True,
        ignore_value_errors=False,
                  )
    ignore_women = config.getboolean("Ignores", "ignore")
    while True:
        races = []
        mode = input("Choose scraping for:\n 1 - single race, 2 - selected races, 3 - range of races, q - quit: ")
        if mode not in "123q":
            print("Unknown mode")
            continue
        elif mode == "q":
            break
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
