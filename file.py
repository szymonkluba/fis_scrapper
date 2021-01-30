from constants import ABR_TOURNAMENTS
from race import Race


class File:
    lines = []

    def __init__(self, race: Race):
        self.race = race
        if race.is_cancelled:
            self.file_name = f"CSV/CANCELLED_{race.date_starts.strftime('%Y-%m-%d')}_" \
                        f"{ABR_TOURNAMENTS[race.subtitle]}_" \
                        f"{race.place.replace(' ', '_')}"
            self.lines = ["##### CANCELLED #####"]
        else:
            self.file_name = f"CSV/{race.date_starts.strftime('%Y-%m-%d')}_" \
                        f"{ABR_TOURNAMENTS[race.subtitle]}_" \
                        f"{race.place.replace(' ', '_')}"

    def generate_lines(self):
        if not self.race.is_cancelled:
            if self.race.participants:
                for p in self.race.participants:
                    self.lines.append(str(p))
            if self.race.disqualified:
                self.lines.append("##### DISQUALIFIED #####\n")
                for d in self.race.disqualified:
                    self.lines.append(str(d))

    def save(self, number: int = 0):
        try:
            if number:
                with open(self.file_name + f"_{number}.csv", 'x') as f:
                    f.writelines(self.lines)
                print(f"Zapisano w: {self.file_name}_{number}.csv")
            else:
                with open(self.file_name + ".csv", 'x') as f:
                    f.writelines(self.lines)
                print(f"Zapisano w: {self.file_name}.csv")
        except FileExistsError:
            number += 1
            self.save(number)
