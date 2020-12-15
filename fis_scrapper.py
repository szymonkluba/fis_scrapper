from lxml import html
import requests

from jump import Jump
from participant import Participant
from race import Race

ABR_TOURNAMENTS = {
    "Olympic Winter Games": "OWG",
    "FIS Ski-Flying World Championships": "SFWC",
    "World Ski Championships": "WSC",
    "World Cup": "WC",
    "FIS Junior World Ski Championships": "WJC",
    "Viessmann FIS Ski Jumping World Cup": 'WC',
    'Viessmann FIS Ski Jumping Qualification': 'QUA',
    "Four Hill": "4H",
    "Continental Cup": "COC",
    "European Youth Olympic Festival": "EYOF",
    "Grand Prix": "GP",
    "Nordic Tournament": "NT",
    "Universiade": "UVS",
    "Youth Olympic Winter Games": "YOG",
    "FIS Cup": "FC",
    "FIS": "FIS",
    "Junior": "JUN",
    "National Championships": "NC",
    "Asian Winter Games": "AWG",
    "Alpen Cup": "OPA",
    "Children": "CHI",
    "Qualification": "QUA",
}

LINE_SCHEME = {
    'Rank': '',
    'Bib': '',
    'FIS code': '',
    'Athlete': '',
    'Year': '',
    'Nation': '',
    'Jump 1': '',
    'Round 1': '',
    'Jump 2': '',
    'Round 2': '',
    'Tot. Points': '',
    'Diff. Points': ''
}


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


# def save_to_file(filename, no):
#     try:
#         with open(filename, 'x') as file:
#             file.writelines(lines)
#             print(f"Zapisano w: {filename}")
#     except FileExistsError:
#         no += 1
#         filename = f'files/{date.strftime("%Y-%m-%d")}_{tournament}_{country}_{hill_size}_{no}.csv'
#         save_to_file(filename, no)


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


def generate_lines(dictionary, lines):
    for i in range(len(dictionary['Athlete'])):
        line = ''
        for k, v in LINE_SCHEME.items():
            if k in dictionary:
                line = f'{line}{dictionary[k][i]},'
            else:
                line = f'{line}{v},'
        line = f'{line}\n'
        lines.append(line)


def generate_participants(dictionary: dict, race: Race, disqualified=False):
    for i in range(len(dictionary['Athlete'])):
        for k, v in dictionary.items():
            if k == "Rank":
                participant = Participant(v[i])
            elif "Jump" in k:
                jump = Jump(v[i])
            elif "Round" in k:
                jump.set_points(v[i])
            else:
                participant_fields(k, v[i], participant)
        if disqualified:
            race.add_disqualified(participant)
        else:
            race.add_participant(participant)


def participant_fields(key, value, participant: Participant):
    return {
        "Bib": participant.set_bib(value),
        "FIS code": participant.set_fis_code(value),
        "Athlete": participant.set_name(value),
        "Year": participant.set_year_born(value),
        "Nation": participant.set_nation(value),
        "Tot. Points": participant.set_total_points(value),
        "Diff. Points": participant.set_points_diff(value)
    }.get(key)


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
                race = Race(
                    fis_id=i,
                    place=tree.xpath('//*[@class="event-header__name heading_off-sm-style"]/h1/text()')[0],
                    subtitle=tree.xpath('//*[@class="event-header__subtitle"]/text()')[0].strip(),
                    kind=tree.xpath('//*[@class="event-header__kind"]/text()')[0],
                    date_starts=tree.xpath('//*[@class="date__full"]/text()')[0],
                    time_starts=tree.xpath('//*[@class="time__value"]/text()')[0],
                            )
                rank = tree.xpath('//*[@id="ajx_results"]/section/div/div/div/div[2]/div[1]/div/div/div/div/div[1]/text()')
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


if __name__ == "__main__":
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
                    for i, race in enumerate(races):
                        print(f"{i+1}. {race.fis_id} {race.place} {race.date_starts.strftime('%d.%m.%Y')}")
                elif next_operation == "s":
                    pass
                elif next_operation == "x":
                    break
                else:
                    print("Unknown command")
                    continue
