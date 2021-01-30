from participant import Participant
from race import Race


class Interface:

    @staticmethod
    def mode_prompts(mode: str):
        return {
            "1": "Enter FIS ID of race: ",
            "2": "Enter FIS IDs of races, separated by spaces (ex. 1111 2222 3333): ",
            "3": "Enter range of FIS IDs, separated by \"-\" (ex. 1111-2222: "
        }.get(mode)

    @staticmethod
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
                print(Interface.jumpers_table(p))
            print("-" * len(header))
        if race.disqualified:
            print("=" * len(header))
            print("Disqualified:")
            print("-" * len(header))
            print(header)
            print("-" * len(header))
            for p in race.disqualified:
                print(Interface.jumpers_table(p))
            print("-" * len(header))

    @staticmethod
    def jumpers_table(p: Participant):
        return (f"|{p.rank if p.rank else '-': ^4}|"
                f"{p.bib if p.bib else '-': ^4}|"
                f"{p.fis_code if p.fis_code else '-': ^8}|"
                f"{p.name if p.name else '-': ^30}|"
                f"{p.tot_points if p.tot_points else '-': ^12}|"
                f"{p.diff_points if p.diff_points else '-': ^12}|")
